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

# What the report still needs from `session`. It used to include the token
# columns and time_created; those moved to `message`, which knows when the
# tokens were spent rather than when the session began. Requiring them here
# would reject a database that is perfectly readable.
_SESSION_COLUMNS = {"agent", "cost", "parent_id", "time_updated"}

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

    @property
    def tokens(self) -> int:
        """Everything this bucket spent.

        Written out by hand in three places, one of which forgot the
        reasoning tokens, and the per-model line stopped adding up to the
        total. One definition instead.
        """
        return (
            self.input_tokens + self.output_tokens + self.reasoning
            + self.cache_read + self.cache_write
        )

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
    prompts: int = 0
    # Every model this agent has used, heaviest first. An agent is not pinned
    # to one model: the orchestrator runs on whatever the user picked, and a
    # subagent can be switched mid-session. Reporting a single "model" for an
    # agent is how a wrong answer becomes invisible.
    models: dict = field(default_factory=dict)


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


# Token accounting lives on `message`, not on `session`. The session table only
# carries a running total stamped with the session's *creation* time, which
# makes a session that starts at 23:31 and runs past midnight report nothing at
# all for the new day. Every message has its own timestamp and its own token
# split, so attributing per message is both exact and cheap. The two agree
# exactly in total: summing the message rows reproduces the session totals.
_MESSAGE_TOKEN_SUM = (
    "COALESCE(json_extract(m.data,'$.tokens.input'),0)"
    " + COALESCE(json_extract(m.data,'$.tokens.output'),0)"
    " + COALESCE(json_extract(m.data,'$.tokens.reasoning'),0)"
    " + COALESCE(json_extract(m.data,'$.tokens.cache.read'),0)"
    " + COALESCE(json_extract(m.data,'$.tokens.cache.write'),0)"
)
# Only assistant turns consume tokens; user rows carry zeroes.
_ASSISTANT = "json_extract(m.data,'$.role') = 'assistant'"


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
        """What this opencode build lacks for us to read it at all.

        `message` is not optional any more: token accounting, the per-day
        chart and the per-agent model split all come from it, because a
        session row only carries a total stamped with the session's start.
        A build without it gets the plain "schema changed" report instead of
        a raw "no such table" from whichever query happened to run first.
        """
        tables = {row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )}
        if "message" not in tables:
            return {"message table"}
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
        # Session-level facts still come from `session`: it is the only place
        # that knows how many sessions ran and which were subagent runs.
        # Everything measured in *tokens* comes from `message` instead, because
        # only a message knows when its tokens were spent and which model spent
        # them. Reading tokens off `session` attributes a whole session to the
        # day it started, so a session that crosses midnight reports nothing for
        # the new day and a multi-day session dumps its whole total on day one.
        # Cost is the one number still read off `session`, because opencode
        # keeps it as a session-level rollup and the per-agent cost is summed
        # from the same place. Tokens are the opposite case: the session only
        # holds a total, so they come per message.
        today = _epoch_ms()
        week_ago = _epoch_ms(6)
        active_cutoff = int((time.time() - ACTIVE_WINDOW_SECONDS) * 1000)

        row = conn.execute(
            "SELECT COUNT(*),"
            " COALESCE(SUM(CASE WHEN parent_id IS NOT NULL THEN 1 ELSE 0 END), 0),"
            " COALESCE(SUM(cost), 0)"
            " FROM session"
        ).fetchone()
        out.total_sessions, out.subagent_sessions, out.total_cost = row
        out.total_prompts = self._count_prompts(conn)

        # All-time tokens, summed per message.
        out.total_tokens = conn.execute(
            f"SELECT COALESCE(SUM({_MESSAGE_TOKEN_SUM}), 0)"
            f" FROM message m WHERE {_ASSISTANT}"
        ).fetchone()[0]

        # Today, by the same measure. This is the number that used to read zero
        # for anyone working past midnight.
        row = conn.execute(
            f"SELECT COALESCE(SUM({_MESSAGE_TOKEN_SUM}), 0) FROM message m"
            f" WHERE {_ASSISTANT} AND m.time_created >= ?",
            (today,),
        ).fetchone()
        out.today_tokens = row[0]
        out.today_prompts = self._count_prompts(conn, since=today)
        out.today_sessions = int(conn.execute(
            "SELECT COUNT(DISTINCT session_id) FROM message"
            " WHERE time_created >= ?",
            (today,),
        ).fetchone()[0])

        # Tokens per day, keyed by local date, for the panel's 7-day chart.
        days: dict[str, int] = {}
        for day, tokens in conn.execute(
            f"SELECT date(m.time_created / 1000, 'unixepoch', 'localtime'),"
            f" COALESCE(SUM({_MESSAGE_TOKEN_SUM}), 0)"
            f" FROM message m WHERE {_ASSISTANT} AND m.time_created >= ?"
            f" GROUP BY 1",
            (week_ago,),
        ):
            if day:
                days[day] = days.get(day, 0) + tokens
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
                f"SELECT DISTINCT date(m.time_created / 1000, 'unixepoch', 'localtime')"
                f" FROM message m WHERE {_ASSISTANT} ORDER BY 1"
            )
            if day
        ]

        # Per model, all time. The panel's own manifest calls this section the
        # "all-time model breakdown", so a date filter here would hide most of
        # the history from the one view built to show it. The 7-day window
        # already has its own section ("tokens by day").
        for model, i, o, r, cr, cw in conn.execute(
            f"SELECT json_extract(m.data,'$.providerID') || '/' || json_extract(m.data,'$.modelID'),"
            f" COALESCE(SUM(json_extract(m.data,'$.tokens.input')),0),"
            f" COALESCE(SUM(json_extract(m.data,'$.tokens.output')),0),"
            f" COALESCE(SUM(json_extract(m.data,'$.tokens.reasoning')),0),"
            f" COALESCE(SUM(json_extract(m.data,'$.tokens.cache.read')),0),"
            f" COALESCE(SUM(json_extract(m.data,'$.tokens.cache.write')),0)"
            f" FROM message m WHERE {_ASSISTANT} GROUP BY 1"
        ):
            if not model or "/" not in model:
                continue
            bucket = out.by_model.setdefault(model, ModelBucket())
            bucket.input_tokens += i
            bucket.output_tokens += o
            bucket.reasoning += r
            bucket.cache_read += cr
            bucket.cache_write += cw
        # Drop models that never actually spent anything: they are rows the
        # panel would draw as an empty bar.
        out.by_model = {
            model: bucket
            for model, bucket in out.by_model.items()
            if bucket.input_tokens or bucket.output_tokens
            or bucket.reasoning or bucket.cache_read or bucket.cache_write
        }

        # Today's split per model, same measure as the all-time one.
        for model, tokens in conn.execute(
            f"SELECT json_extract(m.data,'$.providerID') || '/' || json_extract(m.data,'$.modelID'),"
            f" COALESCE(SUM({_MESSAGE_TOKEN_SUM}), 0)"
            f" FROM message m WHERE {_ASSISTANT} AND m.time_created >= ? GROUP BY 1",
            (today,),
        ):
            if model and "/" in model:
                out.today_by_model[model] = tokens

        # Per agent. Both halves come from different tables on purpose:
        # `session` knows which runs were subagent runs and which are still
        # live, `message` knows what each agent actually spent and on what.
        for agent, sub, live, sessions, cost in conn.execute(
            "SELECT COALESCE(agent,'(none)'),"
            " COALESCE(SUM(CASE WHEN parent_id IS NOT NULL THEN 1 ELSE 0 END),0),"
            f" COALESCE(SUM(CASE WHEN time_updated >= {active_cutoff} THEN 1 ELSE 0 END),0),"
            " COUNT(*), COALESCE(SUM(cost),0)"
            " FROM session GROUP BY agent"
        ):
            entry = out.by_agent.get(agent) or AgentUsage(name=agent)
            entry.subagent_sessions += sub
            entry.active_sessions += live
            entry.sessions += sessions
            entry.cost += cost or 0.0
            out.by_agent[agent] = entry

        # Prompts per agent, as its own query. A correlated subquery reading
        # session.agent would be the obvious way to write this, but that is not
        # legal next to a GROUP BY: the column is neither grouped nor
        # aggregated. Two queries merged here cost less than the workaround.
        for agent, prompts in conn.execute(
            f"SELECT COALESCE(json_extract(m.data,'$.agent'),'(none)'), COUNT(*)"
            f" FROM message m WHERE {_ASSISTANT} GROUP BY 1"
        ):
            entry = out.by_agent.get(agent) or AgentUsage(name=agent)
            entry.prompts += prompts or 0
            out.by_agent[agent] = entry

        # The model an agent is actually running, per agent and per model.
        # Not MAX(model) over a JSON blob: that compares strings and will
        # happily name a model the agent never used.
        for agent, model, tokens in conn.execute(
            f"SELECT COALESCE(json_extract(m.data,'$.agent'),'(none)'),"
            f" json_extract(m.data,'$.providerID') || '/' || json_extract(m.data,'$.modelID'),"
            f" COALESCE(SUM({_MESSAGE_TOKEN_SUM}), 0)"
            f" FROM message m WHERE {_ASSISTANT} GROUP BY 1, 2"
        ):
            if not model or "/" not in model:
                continue
            entry = out.by_agent.setdefault(agent, AgentUsage(name=agent))
            entry.models[model] = entry.models.get(model, 0) + tokens
            entry.tokens += tokens

        for entry in out.by_agent.values():
            if entry.models:
                # Heaviest first, so the headline model is the one that matters.
                ordered = sorted(entry.models.items(), key=lambda kv: -kv[1])
                entry.model = ordered[0][0]
                entry.models = dict(ordered)
            entry.variant = _model_variant(entry.model)

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
