"""Read-only telemetry from opencode's own database.

opencode records every session in ``$XDG_DATA_HOME/opencode/opencode.db``:
which agent ran it, which model, the token split and the cost. That is the
same data the orchestrator is asked about ("what is running, on what model,
how much has it spent"), so there is no reason to make the agents re-report it
over the SDD ledger.

The file is large (hundreds of MB on an active machine) and opencode writes to
it while we read, so every connection is read-only and every aggregate is
pushed into SQL. opencode owns this schema and may change it between
versions, so the columns are feature-detected and a missing one degrades the
report instead of raising.
"""

from __future__ import annotations

import json
import os
import sqlite3
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

_SESSION_COLUMNS = {
    "id", "agent", "model", "cost", "time_created", "time_updated",
    "parent_id", "tokens_input", "tokens_output", "tokens_reasoning",
    "tokens_cache_read", "tokens_cache_write",
}

# A session touched within this window counts as in flight. opencode has no
# explicit "running" flag, so recency is the honest signal.
ACTIVE_WINDOW_SECONDS = 300


@dataclass
class ModelBucket:
    """One model's totals, in the four buckets the panel's contract names.

    ``reasoning`` is tracked because the total reported to the CLI counts it,
    but the panel has no field for it: its contract is four buckets, so the
    panel's own sum is lower than `total_tokens` by exactly the reasoning
    tokens. Widening the contract is Omarchy's call, not ours.
    """

    input_tokens: int = 0
    output_tokens: int = 0
    cache_read: int = 0
    cache_write: int = 0
    reasoning: int = 0

    def as_contract(self) -> dict:
        """Shape the Omarchy panel expects for `modelUsage`."""
        return {
            "inputTokens": self.input_tokens,
            "outputTokens": self.output_tokens,
            "cacheReadInputTokens": self.cache_read,
            "cacheCreationInputTokens": self.cache_write,
        }


@dataclass
class AgentUsage:
    name: str
    sessions: int = 0
    subagent_sessions: int = 0
    active_sessions: int = 0
    tokens: int = 0
    cost: float = 0.0
    model: str | None = None
    variant: str | None = None


@dataclass
class Telemetry:
    """Everything the CLI and the panel record need."""

    available: bool = False
    reason: str = ""
    total_sessions: int = 0
    subagent_sessions: int = 0
    total_prompts: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    today_sessions: int = 0
    today_prompts: int = 0
    today_tokens: int = 0
    today_by_model: dict = field(default_factory=dict)
    recent_days: list = field(default_factory=list)
    by_model: dict = field(default_factory=dict)
    by_agent: dict = field(default_factory=dict)
    active_dates: list = field(default_factory=list)


def default_db_path() -> Path:
    data_home = os.environ.get("XDG_DATA_HOME") or (Path.home() / ".local" / "share")
    return Path(data_home) / "opencode" / "opencode.db"


def _epoch_ms(days_ago: int = 0) -> int:
    """Start of the day boundary, in *local* time.

    The panel buckets by the user's calendar day, and so does Omarchy's own
    collector (datetime.now().date()). Using UTC here would file a morning
    session under the previous day for anyone west of Greenwich, which is
    exactly where this is being read.
    """
    # Naive local time on purpose: see the docstring. noqa: DTZ005
    when = datetime.now() - timedelta(days=days_ago)  # noqa: DTZ005
    start_of_day = when.replace(hour=0, minute=0, second=0, microsecond=0)
    return int(start_of_day.timestamp() * 1000)


def _model_id(raw: str | None) -> str:
    """`model` is a JSON blob like {"id":"big-pickle","providerID":"opencode"}.

    Fall back to a tolerant read for a schema that stores a bare string.
    """
    if not raw:
        return "unknown"
    try:
        parsed = json.loads(raw)
    except (ValueError, TypeError):
        parsed = None
    if isinstance(parsed, dict):
        model_id = str(parsed.get("id") or "unknown")
        provider = str(parsed.get("providerID") or "")
        return f"{provider}/{model_id}" if provider else model_id
    return str(raw).rstrip("/").split("/")[-1] or "unknown"


def _model_variant(raw: str | None) -> str | None:
    try:
        parsed = json.loads(raw or "")
    except (ValueError, TypeError):
        return None
    return parsed.get("variant") if isinstance(parsed, dict) else None


class OpenCodeTelemetry:
    def __init__(self, db_path: Path | str | None = None):
        self.db_path = Path(db_path) if db_path else default_db_path()

    def _connect(self) -> sqlite3.Connection:
        # mode=ro plus query_only guarantees a read can never block opencode's
        # writer or leave a WAL/journal file behind.
        uri = f"{self.db_path.resolve().as_uri()}?mode=ro"
        conn = sqlite3.connect(uri, uri=True, timeout=2)
        conn.execute("PRAGMA query_only = ON")
        return conn

    def _missing_columns(self, conn: sqlite3.Connection) -> set[str]:
        have = {row[1] for row in conn.execute("PRAGMA table_info(session)")}
        return _SESSION_COLUMNS - have

    def read(self) -> Telemetry:
        telemetry = Telemetry()
        if not self.db_path.is_file():
            telemetry.reason = f"no opencode database at {self.db_path}"
            return telemetry

        try:
            conn = self._connect()
        except sqlite3.Error as error:
            telemetry.reason = f"cannot open opencode database: {error}"
            return telemetry

        try:
            missing = self._missing_columns(conn)
            if missing:
                # Degrade rather than raise: a future opencode schema should
                # cost us the report, not crash the command.
                telemetry.reason = f"opencode schema changed, missing: {', '.join(sorted(missing))}"
                return telemetry
            self._read_into(conn, telemetry)
            telemetry.available = True
        except sqlite3.Error as error:
            telemetry.reason = f"opencode database error: {error}"
        finally:
            conn.close()
        return telemetry

    def _read_into(self, conn: sqlite3.Connection, out: Telemetry) -> None:
        # COALESCE every column, not just the outer SUM: one NULL would make
        # the whole expression NULL for that row and SUM would skip it, losing
        # that row's tokens with no visible error.
        token_sum = (
            "COALESCE(tokens_input,0) + COALESCE(tokens_output,0) "
            "+ COALESCE(tokens_reasoning,0) + COALESCE(tokens_cache_read,0) "
            "+ COALESCE(tokens_cache_write,0)"
        )
        today = _epoch_ms()
        week_ago = _epoch_ms(6)
        active_cutoff = int((time.time() - ACTIVE_WINDOW_SECONDS) * 1000)

        row = conn.execute(
            f"SELECT COUNT(*), COALESCE(SUM({token_sum}), 0), COALESCE(SUM(cost), 0),"
            f" COALESCE(SUM(CASE WHEN parent_id IS NOT NULL THEN 1 ELSE 0 END), 0)"
            " FROM session"
        ).fetchone()
        out.total_sessions, out.total_tokens, out.total_cost, out.subagent_sessions = row
        out.total_prompts = self._count_prompts(conn)

        row = conn.execute(
            f"SELECT COUNT(*), COALESCE(SUM({token_sum}), 0) FROM session"
            " WHERE time_created >= ?",
            (today,),
        ).fetchone()
        out.today_sessions, out.today_tokens = row
        out.today_prompts = self._count_prompts(conn, since=today)

        # Tokens per day, keyed by local date, for the panel's 7-day chart.
        days: dict[str, int] = {}
        for created, tokens in conn.execute(
            f"SELECT time_created, COALESCE({token_sum}, 0) FROM session"
            " WHERE time_created IS NOT NULL AND time_created >= ?",
            (week_ago,),
        ):
            # Local calendar day, to match the panel. noqa: DTZ006
            key = datetime.fromtimestamp(created / 1000).strftime("%Y-%m-%d")  # noqa: DTZ006
            days[key] = days.get(key, 0) + tokens
        out.recent_days = [
            {
                "date": (datetime.now() - timedelta(days=offset)).strftime("%Y-%m-%d"),  # noqa: DTZ005
                "messageCount": days.get(
                    (datetime.now() - timedelta(days=offset)).strftime("%Y-%m-%d"), 0  # noqa: DTZ005
                ),
            }
            for offset in range(6, -1, -1)
        ]

        # Every date with any recorded usage, for the all-time "N days" line.
        # The panel unions these across synced machines, so they travel as
        # dates rather than a count.
        out.active_dates = [
            day
            for (day,) in conn.execute(
                "SELECT DISTINCT date(time_created / 1000, 'unixepoch', 'localtime')"
                " FROM session ORDER BY 1"
            )
            if day
        ]

        # Per model, all-time, and per agent. The panel's own manifest calls
        # this section the "all-time model breakdown", so a date filter here
        # would hide most of the history from the one view built to show it.
        # The 7-day window already has its own section ("tokens by day").
        # Grouping in SQL keeps this a single pass rather than walking every
        # session row in Python.
        for model, i, o, r, cr, cw in conn.execute(
            "SELECT model,"
            " COALESCE(SUM(tokens_input),0), COALESCE(SUM(tokens_output),0),"
            " COALESCE(SUM(tokens_reasoning),0), COALESCE(SUM(tokens_cache_read),0),"
            " COALESCE(SUM(tokens_cache_write),0)"
            " FROM session GROUP BY model",
        ):
            key = _model_id(model)
            bucket = out.by_model.setdefault(key, ModelBucket())
            bucket.input_tokens += i
            bucket.output_tokens += o
            bucket.reasoning += r
            bucket.cache_read += cr
            bucket.cache_write += cw

        # Today's split is a separate aggregate. Testing MIN(time_created)
        # against the day boundary looks like it would work, but a model used
        # all week has its minimum before midnight and would be dropped.
        for model, tokens in conn.execute(
            f"SELECT model, COALESCE(SUM({token_sum}), 0) FROM session"
            " WHERE time_created >= ? GROUP BY model",
            (today,),
        ):
            out.today_by_model[_model_id(model)] = tokens

        for agent, model, i, o, r, cr, cw, cost, sessions, sub in conn.execute(
            # The model of the most recently touched session, not MAX(model):
            # MAX() over a JSON blob compares strings, so it will happily
            # report a model the agent is not actually using.
            "SELECT COALESCE(agent,'(none)'),"
            " COALESCE((SELECT s2.model FROM session s2"
            "   WHERE COALESCE(s2.agent,'(none)') = COALESCE(session.agent,'(none)')"
            "   ORDER BY s2.time_updated DESC LIMIT 1),''),"
            " COALESCE(SUM(tokens_input),0), COALESCE(SUM(tokens_output),0),"
            " COALESCE(SUM(tokens_reasoning),0), COALESCE(SUM(tokens_cache_read),0),"
            " COALESCE(SUM(tokens_cache_write),0), COALESCE(SUM(cost),0), COUNT(*),"
            " COALESCE(SUM(CASE WHEN parent_id IS NOT NULL THEN 1 ELSE 0 END),0)"
            " FROM session GROUP BY agent ORDER BY COUNT(*) DESC"
        ):
            entry = out.by_agent.get(agent) or AgentUsage(name=agent)
            entry.sessions += sessions
            entry.subagent_sessions += sub
            entry.tokens += i + o + r + cr + cw
            entry.cost += cost
            entry.model = _model_id(model) if model else None
            entry.variant = _model_variant(model) if model else None
            out.by_agent[agent] = entry

        for agent, count, tokens in conn.execute(
            f"SELECT COALESCE(agent,'(none)'), COUNT(*), COALESCE(SUM({token_sum}),0)"
            # No parent_id filter on purpose: a subagent session always has a
            # parent, so filtering to roots reported exactly zero live
            # subagents -- the one number the user actually asked for.
            " FROM session WHERE time_updated >= ? GROUP BY agent",
            (active_cutoff,),
        ):
            entry = out.by_agent.get(agent) or AgentUsage(name=agent)
            entry.active_sessions += count
            out.by_agent[agent] = entry

    @staticmethod
    def _count_prompts(conn: sqlite3.Connection, since: int | None = None) -> int:
        """Assistant messages are opencode's unit of work. json_extract walks
        the message payload, so this is the one query that scales with history;
        the caller caches its result by database mtime."""
        sql = "SELECT COUNT(*) FROM message WHERE json_extract(data,'$.role') = 'assistant'"
        params: tuple = ()
        if since is not None:
            sql += " AND time_created >= ?"
            params = (since,)
        try:
            return int(conn.execute(sql, params).fetchone()[0])
        except sqlite3.Error:
            return 0
