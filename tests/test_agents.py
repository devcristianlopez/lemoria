"""Tests for agent discovery, model pinning and opencode telemetry."""

import json
import sqlite3
import time
from pathlib import Path

import pytest
import yaml

from lemoria.agents import (
    AgentSync,
    parse_agent,
    set_frontmatter_field,
)
from lemoria.omarchy import build_record, validate_record, write_record
from lemoria.opencode_telemetry import OpenCodeTelemetry, _model_id, _model_variant

AGENT_MD = """---
description: >-
  Review code for correctness and style. Second folded line so the scalar
  has something to join.
mode: subagent
permission:
  bash: deny
  edit: allow
---

# Review Agent

**Role:** Technical review

Body text that must survive untouched.
"""


@pytest.fixture
def agents_dir(tmp_path):
    directory = tmp_path / "agents"
    directory.mkdir()
    (directory / "review-agent.md").write_text(AGENT_MD, encoding="utf-8")
    return directory


@pytest.fixture
def opencode_db(tmp_path):
    """A miniature opencode.db. Never point tests at the real one: it is
    hundreds of megabytes and owned by a running process."""
    path = tmp_path / "opencode.db"
    conn = sqlite3.connect(path)
    conn.execute(
        "CREATE TABLE session (id text PRIMARY KEY, agent text, model text,"
        " cost real, parent_id text, time_created integer, time_updated integer,"
        " tokens_input integer default 0, tokens_output integer default 0,"
        " tokens_reasoning integer default 0, tokens_cache_read integer default 0,"
        " tokens_cache_write integer default 0)"
    )
    conn.execute(
        "CREATE TABLE message (id text PRIMARY KEY, session_id text,"
        " time_created integer, data text)"
    )
    now = int(time.time() * 1000)
    model = json.dumps({"id": "big-pickle", "providerID": "opencode", "variant": "default"})
    conn.executemany(
        "INSERT INTO session (id, agent, model, cost, parent_id, time_created, time_updated,"
        " tokens_input, tokens_output) VALUES (?,?,?,?,?,?,?,?,?)",
        [
            ("s1", "orchestrator", model, 0.25, None, now, now, 100, 50),
            ("s2", "review-agent", model, 0.0, "s1", now, now, 200, 20),
            ("s3", "review-agent", model, 0.0, "s1", now - 86_400_000, now - 86_400_000, 300, 30),
            # Same agent, older session, model id that sorts last as a string.
            # Any implementation using MAX(model) reports this one.
            (
                "s4", "orchestrator",
                json.dumps({"id": "zzz-stale", "providerID": "opencode", "variant": "low"}),
                0.0, None, now - 1000, now - 86_400_000, 1, 1,
            ),
            # 30 days old, on a model of its own. A date filter on the
            # per-model aggregate would drop it; the panel's own manifest
            # calls that section the all-time breakdown, so it must survive.
            (
                "s5", "orchestrator",
                json.dumps({"id": "ancient", "providerID": "opencode"}),
                0.0, None, now - 2_592_000_000, now - 2_592_000_000, 7, 3,
            ),
        ],
    )
    # Messages carry the token accounting in the real database, so the fixture
    # mirrors the session split onto them. A user turn is present too: only
    # assistant rows have tokens, and the prompt count must not move when one
    # is added.
    def assistant(mid, sid, ts, provider, model_id, tokens, agent):
        return (
            mid, sid, ts, json.dumps({
                "role": "assistant", "agent": agent,
                "providerID": provider, "modelID": model_id,
                "tokens": tokens, "cost": 0.0,
            }),
        )

    conn.executemany(
        "INSERT INTO message (id, session_id, time_created, data) VALUES (?,?,?,?)",
        [
            # s1: 100 in + 50 out = 150, on big-pickle.
            assistant("a1", "s1", now, "opencode", "big-pickle",
                      {"input": 100, "output": 50, "reasoning": 7,
                       "cache": {"read": 0, "write": 0}}, "orchestrator"),
            ("u1", "s1", now, json.dumps({"role": "user", "agent": "orchestrator"})),
            # s2: 200 + 20 = 220.
            assistant("a2", "s2", now, "opencode", "big-pickle",
                      {"input": 200, "output": 20, "reasoning": 0,
                       "cache": {"read": 0, "write": 0}}, "review-agent"),
            # s3: 300 + 30 = 330, a day old.
            assistant("a3", "s3", now - 86_400_000, "opencode", "big-pickle",
                      {"input": 300, "output": 30, "reasoning": 3,
                       "cache": {"read": 0, "write": 0}}, "review-agent"),
            # s4: 1 + 1 = 2, on a model that sorts last as a string. Any
            # implementation that takes the alphabetically last model, or the
            # one from the most recently *touched* session, is wrong here: the
            # heaviest model is the honest answer.
            assistant("a4", "s4", now - 1000, "opencode", "zzz-stale",
                      {"input": 1, "output": 1, "reasoning": 0,
                       "cache": {"read": 0, "write": 0}}, "orchestrator"),
            # s5: 7 + 3 = 10, 30 days old, on a model of its own. A date filter
            # on the per-model aggregate would drop it; the panel's own manifest
            # calls that section the all-time breakdown, so it must survive.
            assistant("a5", "s5", now - 2_592_000_000, "opencode", "ancient",
                      {"input": 7, "output": 3, "reasoning": 0,
                       "cache": {"read": 0, "write": 0}}, "orchestrator"),
        ],
    )
    conn.commit()
    conn.close()
    return path


class TestParsing:
    def test_folded_description_is_joined_not_kept_as_indicator(self, agents_dir):
        parsed = parse_agent(agents_dir / "review-agent.md")
        assert not parsed.description.startswith(">")
        assert "Second folded line" in parsed.description

    def test_nested_permission_is_a_dict_not_flattened(self, agents_dir):
        parsed = parse_agent(agents_dir / "review-agent.md")
        assert parsed.permission == {"bash": "deny", "edit": "allow"}

    def test_role_comes_from_the_body_convention(self, agents_dir):
        assert parse_agent(agents_dir / "review-agent.md").role == "Technical review"

    def test_role_falls_back_to_filename(self, tmp_path):
        bare = tmp_path / "solo.md"
        bare.write_text("---\nmode: subagent\n---\n\nno role here\n", encoding="utf-8")
        assert parse_agent(bare).role == "solo"

    def test_file_without_frontmatter_is_skipped(self, tmp_path):
        loose = tmp_path / "notes.md"
        loose.write_text("just prose, no frontmatter\n", encoding="utf-8")
        assert parse_agent(loose) is None

    def test_declaration_of_model_is_read(self, tmp_path):
        pinned = tmp_path / "pinned.md"
        pinned.write_text(
            "---\ndescription: d\nmodel: opencode/big-pickle\nvariant: high\n---\n\nbody\n",
            encoding="utf-8",
        )
        parsed = parse_agent(pinned)
        assert parsed.model == "opencode/big-pickle"
        assert parsed.variant == "high"


class TestFrontmatterRoundTrip:
    def test_adding_model_keeps_the_rest_byte_for_byte(self, agents_dir):
        path = agents_dir / "review-agent.md"
        original = path.read_text(encoding="utf-8")
        updated = set_frontmatter_field(original, "model", "opencode/big-pickle")
        assert updated.split("---", 2)[2] == original.split("---", 2)[2]

    def test_added_key_lands_outside_the_nested_block(self, agents_dir):
        """Appending after the last top-level key would land inside
        `permission:` and produce invalid YAML. This is the regression that
        silently corrupted real agent files."""
        updated = set_frontmatter_field(AGENT_MD, "model", "opencode/big-pickle")
        front = updated.split("---", 2)[1]
        parsed = yaml.safe_load(front)
        assert parsed["permission"] == {"bash": "deny", "edit": "allow"}
        assert parsed["model"] == "opencode/big-pickle"

    def test_rewriting_the_same_value_is_a_no_op(self, agents_dir):
        once = set_frontmatter_field(AGENT_MD, "model", "opencode/big-pickle")
        twice = set_frontmatter_field(once, "model", "opencode/big-pickle")
        assert once == twice
        assert once.count("model:") == 1

    def test_setting_none_removes_the_key(self, agents_dir):
        with_model = set_frontmatter_field(AGENT_MD, "model", "opencode/big-pickle")
        without = set_frontmatter_field(with_model, "model", None)
        assert "model:" not in without
        assert yaml.safe_load(without.split("---", 2)[1])["permission"] == {
            "bash": "deny",
            "edit": "allow",
        }

    def test_frontmatter_absent_raises(self):
        with pytest.raises(ValueError):
            set_frontmatter_field("no frontmatter here\n", "model", "x")

    def test_body_containing_rules_is_not_mistaken_for_the_closer(self, tmp_path):
        raw = "---\ndescription: d\n---\n\nintro\n\n---\n\noutro\n"
        updated = set_frontmatter_field(raw, "model", "m")
        assert updated.split("---", 2)[2] == "\n\nintro\n\n---\n\noutro\n"


class TestAgentSync:
    def test_discovers_and_parses(self, agents_dir):
        found = AgentSync(None, agents_dir).discover()
        assert [d.name for d in found] == ["review-agent"]
        assert found[0].role == "Technical review"

    def test_missing_directory_yields_nothing(self, tmp_path):
        assert AgentSync(None, tmp_path / "nope").discover() == []

    def test_set_model_updates_the_file_and_reparses(self, agents_dir):
        syncer = AgentSync(None, agents_dir)
        definition = syncer.set_model("review-agent", "opencode/big-pickle", "high")
        assert definition.model == "opencode/big-pickle"
        assert definition.variant == "high"
        assert "model: opencode/big-pickle" in (agents_dir / "review-agent.md").read_text()

    def test_clearing_model_restores_inheritance(self, agents_dir):
        syncer = AgentSync(None, agents_dir)
        syncer.set_model("review-agent", "opencode/big-pickle", "high")
        cleared = syncer.set_model("review-agent", None, None)
        assert cleared.model is None
        assert cleared.variant is None

    def test_set_model_on_missing_agent_raises(self, agents_dir):
        with pytest.raises(FileNotFoundError):
            AgentSync(None, agents_dir).set_model("nope", "m")


class TestModelParsing:
    def test_reads_id_and_keeps_provider(self):
        raw = json.dumps({"id": "big-pickle", "providerID": "opencode", "variant": "high"})
        assert _model_id(raw) == "opencode/big-pickle"
        assert _model_variant(raw) == "high"

    def test_tolerates_a_bare_string(self):
        assert _model_id("anthropic/claude-sonnet-4-6") == "claude-sonnet-4-6"
        assert _model_variant("anthropic/claude-sonnet-4-6") is None

    def test_missing_model_is_not_an_exception(self):
        assert _model_id(None) == "unknown"
        assert _model_id("{bad json") == "{bad json"


class TestTelemetry:
    def test_reads_totals_from_the_fixture(self, opencode_db):
        telemetry = OpenCodeTelemetry(opencode_db).read()
        assert telemetry.available
        assert telemetry.total_sessions == 5
        assert telemetry.total_tokens == 722
        assert telemetry.total_prompts == 5  # one assistant turn per session
        assert telemetry.total_cost == pytest.approx(0.25)

    def test_splits_root_and_subagent_sessions(self, opencode_db):
        telemetry = OpenCodeTelemetry(opencode_db).read()
        assert telemetry.by_agent["review-agent"].subagent_sessions == 2
        assert telemetry.by_agent["orchestrator"].subagent_sessions == 0

    def test_buckets_add_up_to_the_total(self, opencode_db):
        """The per-model line stopped adding up to the total, quietly, because
        the sum was written out by hand and one copy forgot the reasoning
        tokens. Nothing crashed; the panel just showed a number that did not
        match its own parts."""
        telemetry = OpenCodeTelemetry(opencode_db).read()
        by_model = sum(bucket.tokens for bucket in telemetry.by_model.values())
        by_agent = sum(entry.tokens for entry in telemetry.by_agent.values())
        assert by_model == telemetry.total_tokens
        assert by_agent == telemetry.total_tokens

    def test_a_session_spanning_midnight_counts_today(self, tmp_path):
        """The bug this whole change exists for.

        A session started at 23:31 keeps working after 00:00. It stamped
        every token it ever spent with the date it *started*, so a long
        overnight run reported 0 for today and put the whole amount on
        yesterday. Tokens are attributed to the message that spent them, so
        the half that happened after midnight lands on today.
        """
        midnight = time.time()
        # Walk back to 23:31 of the previous day.
        started = midnight - (midnight % 86_400_000) - 29 * 60_000
        path = tmp_path / "overnight.db"
        conn = sqlite3.connect(path)
        conn.execute(
            "CREATE TABLE session (id text PRIMARY KEY, agent text, model text,"
            " cost real, parent_id text, time_created integer, time_updated integer)"
        )
        conn.execute(
            "CREATE TABLE message (id text PRIMARY KEY, session_id text,"
            " time_created integer, data text)"
        )
        now_ms = int(midnight * 1000)
        conn.execute(
            "INSERT INTO session VALUES (?,?,?,?,?,?,?)",
            ("night", "orchestrator", '{"id":"m","providerID":"opencode"}',
             0.0, None, int(started * 1000), now_ms),
        )
        conn.executemany(
            "INSERT INTO message VALUES (?,?,?,?)",
            [
                # Before midnight.
                ("before", "night", int(started * 1000) + 60_000, json.dumps({
                    "role": "assistant", "agent": "orchestrator",
                    "providerID": "opencode", "modelID": "m",
                    "tokens": {"input": 1000, "output": 500,
                               "cache": {"read": 0, "write": 0}},
                })),
                # After midnight, same session.
                ("after", "night", now_ms, json.dumps({
                    "role": "assistant", "agent": "orchestrator",
                    "providerID": "opencode", "modelID": "m",
                    "tokens": {"input": 200, "output": 100,
                               "cache": {"read": 0, "write": 0}},
                })),
            ],
        )
        conn.commit()
        conn.close()

        telemetry = OpenCodeTelemetry(path).read()
        assert telemetry.available
        # Everything is still counted all-time.
        assert telemetry.total_tokens == 1800
        # But the post-midnight part is attributed to today, not yesterday.
        assert telemetry.today_tokens == 300
        assert telemetry.total_prompts == 2

    def test_recent_days_always_has_seven_entries(self, opencode_db):
        telemetry = OpenCodeTelemetry(opencode_db).read()
        assert len(telemetry.recent_days) == 7
        assert telemetry.recent_days[-1]["date"] == time.strftime("%Y-%m-%d")

    def test_missing_database_degrades_without_raising(self, tmp_path):
        telemetry = OpenCodeTelemetry(tmp_path / "absent.db").read()
        assert not telemetry.available
        assert "no opencode database" in telemetry.reason

    def test_unknown_schema_degrades_without_raising(self, tmp_path):
        """opencode owns this schema. A future version must cost us the
        report, not crash `agent status`."""
        path = tmp_path / "thin.db"
        conn = sqlite3.connect(path)
        conn.execute("CREATE TABLE session (id text PRIMARY KEY, agent text)")
        conn.commit()
        conn.close()
        telemetry = OpenCodeTelemetry(path).read()
        assert not telemetry.available
        assert "schema changed" in telemetry.reason

    def test_reading_never_writes_to_the_database(self, opencode_db):
        before = opencode_db.stat().st_mtime_ns
        OpenCodeTelemetry(opencode_db).read()
        assert opencode_db.stat().st_mtime_ns == before


class TestUsageCommand:
    """`lemoria usage` is the whole view on a machine with no Omarchy panel."""

    def test_reports_totals_models_and_agents(self, opencode_db, monkeypatch):
        import json

        from click.testing import CliRunner

        from lemoria.cli import cli

        monkeypatch.setattr(
            "lemoria.opencode_telemetry.default_db_path", lambda: opencode_db
        )
        result = CliRunner().invoke(cli, ["usage", "--json"])
        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["available"] is True
        assert payload["total"]["tokens"] == 722
        assert payload["total"]["sessions"] == 5
        # s5 is 30 days old and must reach the all-time per-model breakdown.
        assert any(m["model"] == "opencode/ancient" for m in payload["byModel"])
        assert {a["agent"] for a in payload["byAgent"]} >= {"orchestrator", "review-agent"}

    def test_models_are_ordered_heaviest_first(self, opencode_db, monkeypatch):
        import json

        from click.testing import CliRunner

        from lemoria.cli import cli

        monkeypatch.setattr(
            "lemoria.opencode_telemetry.default_db_path", lambda: opencode_db
        )
        payload = json.loads(CliRunner().invoke(cli, ["usage", "--json"]).output)
        totals = [m["tokens"] for m in payload["byModel"]]
        assert totals == sorted(totals, reverse=True)

    def test_missing_database_fails_loudly(self, tmp_path, monkeypatch):
        from click.testing import CliRunner

        from lemoria.cli import cli

        monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "absent"))
        result = CliRunner().invoke(cli, ["usage"])
        assert result.exit_code == 1
        assert "No telemetry" in result.output

    def test_human_table_does_not_dump_raw_digit_strings(self, opencode_db, monkeypatch):
        from click.testing import CliRunner

        from lemoria.cli import cli

        monkeypatch.setattr(
            "lemoria.opencode_telemetry.default_db_path", lambda: opencode_db
        )
        result = CliRunner().invoke(cli, ["usage"])
        assert result.exit_code == 0
        assert "By model" in result.output
        assert "By agent" in result.output


class TestOmarchyRecord:
    def test_record_satisfies_the_panel_contract(self, opencode_db):
        record = build_record(OpenCodeTelemetry(opencode_db).read())
        assert validate_record(record) == []
        assert record["id"] == "lemoria"
        assert record["schemaVersion"] == 1
        assert record["scope"] == "device"

    def test_model_usage_is_all_time_not_a_seven_day_window(self, opencode_db):
        """The panel calls this section the all-time breakdown, so the per-model
        aggregate must not be clipped to the week the daily chart covers."""
        record = build_record(OpenCodeTelemetry(opencode_db).read())
        # s5 is 30 days old: absent under any 7-day filter on the aggregate.
        assert record["modelUsage"]["opencode/ancient"]["inputTokens"] == 7
        assert record["modelUsage"]["opencode/ancient"]["outputTokens"] == 3

    def test_model_buckets_use_the_names_the_panel_reads(self, opencode_db):
        record = build_record(OpenCodeTelemetry(opencode_db).read())
        bucket = record["modelUsage"]["opencode/big-pickle"]
        assert set(bucket) == {
            "inputTokens",
            "outputTokens",
            "cacheReadInputTokens",
            "cacheCreationInputTokens",
        }
        assert bucket["inputTokens"] == 600

    def test_ready_is_false_when_nothing_was_ever_recorded(self, tmp_path):
        record = build_record(OpenCodeTelemetry(tmp_path / "absent.db").read())
        assert record["ready"] is False

    def test_unavailable_telemetry_explains_itself(self, tmp_path):
        record = build_record(OpenCodeTelemetry(tmp_path / "absent.db").read())
        assert record["authHelpText"]
        assert record["usageStatusText"]

    def test_validate_catches_a_missing_key(self, opencode_db):
        record = build_record(OpenCodeTelemetry(opencode_db).read())
        del record["recentDays"]
        problems = validate_record(record)
        assert any("recentDays" in p for p in problems)

    def test_validate_catches_a_short_week(self, opencode_db):
        record = build_record(OpenCodeTelemetry(opencode_db).read())
        record["recentDays"] = record["recentDays"][:3]
        assert any("7 entries" in p for p in validate_record(record))

    def test_record_carries_budget_and_agents_for_our_panel(self, opencode_db):
        from lemoria.budget import Budget

        record = build_record(OpenCodeTelemetry(opencode_db).read(), Budget(monthly_tokens=1_000))
        assert record["budget"]["funded"] == 1_000
        assert record["budget"]["used"] == record["monthTokens"]
        assert record["balance"]["remaining"] == 1_000 - record["monthTokens"]

        agents = {agent["agent"]: agent for agent in record["agents"]}
        assert agents["orchestrator"]["tokens"] > 0
        assert agents["orchestrator"]["todayTokens"] >= 0
        assert agents["orchestrator"]["model"] == "opencode/big-pickle"
        assert "opencode/big-pickle" in agents["orchestrator"]["models"]

    def test_record_keeps_agents_that_have_activity_but_zero_tokens(self, opencode_db):
        from lemoria.opencode_telemetry import AgentUsage

        telemetry = OpenCodeTelemetry(opencode_db).read()
        telemetry.by_agent["zero-agent"] = AgentUsage(
            name="zero-agent", sessions=1, prompts=2, tokens=0
        )
        record = build_record(telemetry)
        names = [agent["agent"] for agent in record["agents"]]
        assert "zero-agent" in names

    def test_write_is_atomic_and_leaves_no_temp_files(self, tmp_path, opencode_db):
        destination = tmp_path / "usage" / "lemoria.json"
        record = build_record(OpenCodeTelemetry(opencode_db).read())
        write_record(record, destination)
        assert json.loads(destination.read_text())["id"] == "lemoria"
        assert [p.name for p in destination.parent.iterdir()] == ["lemoria.json"]


class TestTimerUnits:
    def test_default_record_is_private_not_the_native_agents_panel(self, monkeypatch, tmp_path):
        from lemoria.omarchy import default_record_path, legacy_agents_record_path

        monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
        assert default_record_path() == tmp_path / "lemoria" / "omarchy" / "usage.json"
        assert legacy_agents_record_path() == (
            tmp_path / "omarchy" / "agents" / "usage" / "lemoria.json"
        )
        assert default_record_path().parent != legacy_agents_record_path().parent

    def test_writes_both_units(self, tmp_path):
        from lemoria.omarchy import install_timer

        service, timer = install_timer(tmp_path, interval="5min")
        assert service.name == "lemoria-usage.service"
        assert timer.name == "lemoria-usage.timer"
        assert "lemoria-usage.service" in timer.read_text()

    def test_service_runs_an_absolute_path(self, tmp_path):
        """A unit has no shell, so a bare `lemoria` would not resolve."""
        from lemoria.omarchy import find_executable, install_timer

        service, _ = install_timer(tmp_path)
        exec_start = [l for l in service.read_text().splitlines() if l.startswith("ExecStart=")]
        assert len(exec_start) == 1
        assert find_executable() in exec_start[0]

    def test_interval_is_honoured(self, tmp_path):
        from lemoria.omarchy import install_timer

        _, timer = install_timer(tmp_path, interval="15min")
        assert "OnUnitActiveSec=15min" in timer.read_text()

    def test_codex_stabilizer_units_watch_the_native_codex_record(self, tmp_path, monkeypatch):
        from lemoria.omarchy import install_codex_stabilizer

        monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
        service, path = install_codex_stabilizer(tmp_path)
        assert service.name == "lemoria-codex-stabilize.service"
        assert path.name == "lemoria-codex-stabilize.path"
        assert "omarchy stabilize-codex" in service.read_text()
        assert str(tmp_path / "state" / "omarchy" / "agents" / "usage" / "codex.json") in path.read_text()

    def test_creates_the_directory(self, tmp_path):
        from lemoria.omarchy import install_timer

        target = tmp_path / "deeply" / "nested"
        install_timer(target)
        assert (target / "lemoria-usage.service").exists()

    def test_reinstall_is_idempotent(self, tmp_path):
        from lemoria.omarchy import install_timer

        install_timer(tmp_path)
        before = (tmp_path / "lemoria-usage.timer").read_text()
        install_timer(tmp_path)
        assert (tmp_path / "lemoria-usage.timer").read_text() == before

    def test_writing_units_does_not_enable_them(self, tmp_path):
        """install_timer touches the filesystem only; starting a timer is the
        caller's decision."""
        from lemoria.omarchy import install_timer

        service, timer = install_timer(tmp_path)
        assert not list(tmp_path.glob("timers.target.wants"))
        assert "WantedBy=timers.target" in timer.read_text()
        assert service.read_text()


class TestCodexStabilizer:
    def test_caches_good_limits_and_clears_stale_login_hint(self, tmp_path):
        from lemoria.omarchy import stabilize_codex_record

        record = tmp_path / "codex.json"
        cache = tmp_path / "cache.json"
        record.write_text(json.dumps({
            "id": "codex",
            "ready": True,
            "todayTotalTokens": 100,
            "totalPrompts": 2,
            "usageStatusText": "",
            "authHelpText": "Run `codex login` to authenticate.",
            "tierLabel": "plus",
            "limits": [{"label": "5h window", "percent": 0.5}],
        }), encoding="utf-8")

        changed, message = stabilize_codex_record(record, cache)
        assert changed is True
        assert "stabilized" in message
        fixed = json.loads(record.read_text())
        assert fixed["authHelpText"] == ""
        assert json.loads(cache.read_text())["limits"] == fixed["limits"]

    def test_restores_cached_limits_when_account_read_fails(self, tmp_path):
        from lemoria.omarchy import stabilize_codex_record

        record = tmp_path / "codex.json"
        cache = tmp_path / "cache.json"
        cache.write_text(json.dumps({
            "schemaVersion": 1,
            "limits": [{"label": "5h window", "percent": 0.62}],
            "tierLabel": "plus",
        }), encoding="utf-8")
        record.write_text(json.dumps({
            "id": "codex",
            "ready": True,
            "todayTotalTokens": 100,
            "totalPrompts": 2,
            "usageStatusText": "Codex limits unavailable",
            "authHelpText": "account/read",
            "tierLabel": "",
            "limits": [],
        }), encoding="utf-8")

        changed, _ = stabilize_codex_record(record, cache)
        fixed = json.loads(record.read_text())
        assert changed is True
        assert fixed["usageStatusText"] == ""
        assert fixed["authHelpText"] == ""
        assert fixed["tierLabel"] == "plus"
        assert fixed["limits"] == [{"label": "5h window", "percent": 0.62}]

    def test_missing_codex_record_is_a_noop(self, tmp_path):
        from lemoria.omarchy import stabilize_codex_record

        changed, message = stabilize_codex_record(tmp_path / "missing.json", tmp_path / "cache.json")
        assert changed is False
        assert "missing" in message

    def test_account_read_without_usage_is_not_hidden(self, tmp_path):
        from lemoria.omarchy import stabilize_codex_record

        record = tmp_path / "codex.json"
        record.write_text(json.dumps({
            "id": "codex", "ready": False, "todayTotalTokens": 0,
            "totalPrompts": 0, "usageStatusText": "Codex limits unavailable",
            "authHelpText": "account/read", "limits": [],
        }), encoding="utf-8")
        changed, _ = stabilize_codex_record(record, tmp_path / "cache.json")
        fixed = json.loads(record.read_text())
        assert changed is False
        assert fixed["authHelpText"] == "account/read"

    def test_malformed_numeric_fields_do_not_crash(self, tmp_path):
        from lemoria.omarchy import stabilize_codex_record

        record = tmp_path / "codex.json"
        record.write_text(json.dumps({
            "id": "codex", "ready": True, "todayTotalTokens": "many",
            "totalPrompts": {}, "todayPrompts": [], "usageStatusText": "",
            "authHelpText": "account/read", "limits": [],
        }), encoding="utf-8")
        changed, _ = stabilize_codex_record(record, tmp_path / "cache.json")
        assert changed is False


class TestPluginInstall:
    def test_installs_the_bundled_user_plugin(self, tmp_path):
        from lemoria.omarchy import install_plugin

        destination = install_plugin(tmp_path / "plugins" / "lemoria.usage")
        assert destination.joinpath("manifest.json").exists()
        assert destination.joinpath("Panel.qml").exists()
        assert destination.joinpath("Record.qml").exists()

    def test_panel_root_exposes_a_bar_slot_size(self):
        """Omarchy sizes third-party bar widgets from the root implicit size."""
        from lemoria.omarchy import plugin_source_dir

        panel = plugin_source_dir().joinpath("Panel.qml").read_text(encoding="utf-8")
        bar_button = panel.split("BarIconButton {", 1)[1].split("KeyboardPanel {", 1)[0]
        assert "implicitWidth: button.implicitWidth + rightGap" in panel
        assert "implicitHeight: button.implicitHeight" in panel
        assert "readonly property int rightGap: Style.space(6)" in panel
        assert "anchors.fill: parent" not in bar_button
        assert "width: implicitWidth" in bar_button
        assert 'text: usage.hasUsage ? root.compact(root.record.totalTokens) : "0"' in panel

    def test_reinstall_removes_stale_files(self, tmp_path):
        from lemoria.omarchy import install_plugin

        destination = install_plugin(tmp_path / "plugins" / "lemoria.usage")
        destination.joinpath("old.qml").write_text("stale", encoding="utf-8")
        install_plugin(destination)
        assert not destination.joinpath("old.qml").exists()

    def test_uninstall_removes_only_the_plugin(self, tmp_path):
        from lemoria.omarchy import install_plugin, uninstall_plugin

        root = tmp_path / "plugins"
        destination = install_plugin(root / "lemoria.usage")
        other = root / "other.plugin"
        other.mkdir()
        assert uninstall_plugin(destination) is True
        assert not destination.exists()
        assert other.exists()
        assert uninstall_plugin(destination) is False


class TestUninstall:
    """Uninstall has to remove exactly what install wrote, and nothing else."""

    @pytest.fixture(autouse=True)
    def sandbox(self, tmp_path, monkeypatch):
        """Keep `uninstall` away from the developer's real install.

        The command has two ways out of the tmp_path the test hands it: it
        shells out to `systemctl --user disable --now` (which acts on the live
        session regardless of redirects) and it deletes the record file. Both
        must be neutralised, or running the suite disables the real timer and
        removes the real record.

        Redirecting *both* directories by default, rather than per test, is the
        point: a test that forgets to patch one of them then still cannot reach
        the developer's machine.
        """
        import subprocess

        calls = []
        monkeypatch.setattr(subprocess, "run", lambda *a, **kw: calls.append(a))
        monkeypatch.setattr("lemoria.omarchy.default_unit_dir", lambda: tmp_path / "systemd")
        monkeypatch.setattr("lemoria.omarchy.default_record_dir", lambda: tmp_path / "usage")
        monkeypatch.setattr("lemoria.omarchy.default_plugin_dir", lambda: tmp_path / "plugins")
        self.systemd_calls = calls

    def test_touches_neither_the_real_units_nor_the_real_record(self, tmp_path):
        """The guard above is what keeps the suite non-destructive.

        If this fails, the fixture stopped covering a path and the suite is
        again one `pytest` away from deleting the panel's record.
        """
        from lemoria import omarchy as omarchy_module

        real_record = Path.home() / ".local/state/omarchy/agents/usage/lemoria.json"
        real_units = Path.home() / ".config/systemd/user"
        real_plugins = Path.home() / ".config/omarchy/plugins"

        assert omarchy_module.default_record_dir() != real_record.parent
        assert omarchy_module.default_unit_dir() != real_units
        assert omarchy_module.default_plugin_dir() != real_plugins

    def test_removes_the_units_it_installed(self, tmp_path, monkeypatch):
        from click.testing import CliRunner

        from lemoria.cli import cli
        from lemoria.omarchy import install_timer

        units = tmp_path / "systemd"
        install_timer(units)
        assert units.joinpath("lemoria-usage.timer").exists()

        monkeypatch.setattr("lemoria.omarchy.default_unit_dir", lambda: units)
        result = CliRunner().invoke(cli, ["omarchy", "uninstall"])
        assert result.exit_code == 0
        assert not units.joinpath("lemoria-usage.timer").exists()
        assert self.systemd_calls, "uninstall should have asked systemd to stop the timer"
        assert not units.joinpath("lemoria-usage.service").exists()

    def test_is_idempotent_on_a_machine_that_never_installed(self, tmp_path, monkeypatch):
        from click.testing import CliRunner

        from lemoria.cli import cli

        result = CliRunner().invoke(cli, ["omarchy", "uninstall"])
        assert result.exit_code == 0
        assert "Not present" in result.output

    def test_keep_record_leaves_the_panel_file(self, tmp_path, monkeypatch):
        from click.testing import CliRunner

        from lemoria.cli import cli
        from lemoria.omarchy import build_record, write_record
        from lemoria.opencode_telemetry import OpenCodeTelemetry

        records = tmp_path / "usage"
        write_record(build_record(OpenCodeTelemetry(tmp_path / "absent.db").read()),
                     records / "lemoria.json")

        monkeypatch.setattr("lemoria.omarchy.default_unit_dir", lambda: tmp_path / "units")
        monkeypatch.setattr("lemoria.omarchy.default_record_dir", lambda: records)
        result = CliRunner().invoke(cli, ["omarchy", "uninstall", "--keep-record"])
        assert result.exit_code == 0
        assert records.joinpath("lemoria.json").exists()


class TestTimerArmed:
    """`_timer_armed` has to separate armed from the state that never fires.

    Both `list-timers` and the TimersMonotonic dump keep reporting a pending
    elapse for a stopped or broken timer, so they cannot be used here. These
    tests pin the one signal that does discriminate.
    """

    @pytest.mark.parametrize("substate, expected", [
        ("waiting", True),   # armed, fires on the next elapse
        ("dead", False),     # not started
        ("elapsed", False),  # active but nothing queued: the bug
    ])
    def test_reads_substate(self, monkeypatch, substate, expected):
        import subprocess

        class Result:
            stdout = substate + "\n"

        monkeypatch.setattr(subprocess, "run", lambda *a, **kw: Result())
        from lemoria.cli import _timer_armed
        assert _timer_armed() is expected

    def test_absent_systemctl_is_not_armed(self, monkeypatch):
        import lemoria.cli
        monkeypatch.setattr("shutil.which", lambda name: None)
        assert lemoria.cli._timer_armed() is False


class FakeAgent:
    def __init__(self, name, model=None, variant=None):
        self.name, self.model, self.variant = name, model, variant
        self.role, self.config_dict = "role", {"mode": "subagent"}


class TestStatusSurvivesOpencodeBuiltins:
    """opencode registers its own agents (build, plan, explore, general). They
    land in telemetry but have no row in the DB and no .md to configure. The
    status view unions both sets, so it must never index the DB dict with a
    name that only telemetry knows about."""

    def _run(self, monkeypatch, agent_names, telemetry_agents):
        import json as _json

        from click.testing import CliRunner

        from lemoria import cli
        from lemoria.opencode_telemetry import AgentUsage, Telemetry

        class FakeQuery:
            def order_by(self_inner, *_a):
                return self_inner

            def all(self_inner):
                return [FakeAgent(n) for n in agent_names]

        class FakeSession:
            def query(self_inner, _model):
                return FakeQuery()

        class FakeApp:
            session = FakeSession()

            def close(self_inner):
                pass

        telemetry = Telemetry(available=True, reason=None)
        for name in telemetry_agents:
            telemetry.by_agent[name] = AgentUsage(
                name=name, model="opencode/big-pickle", variant="default",
                sessions=3, subagent_sessions=1, active_sessions=0,
                tokens=1000, cost=0.0,
            )
        monkeypatch.setattr(cli, "Lemoria", lambda *a, **k: FakeApp())
        monkeypatch.setattr(
            "lemoria.opencode_telemetry.OpenCodeTelemetry",
            lambda *a, **k: type("T", (), {"read": lambda self: telemetry})(),
        )
        result = CliRunner().invoke(cli.cli, ["agent", "status", "--json"])
        return result, _json

    def test_json_survives_a_builtin_with_no_db_row(self, monkeypatch):
        result, _json = self._run(
            monkeypatch, ["review-agent"], ["review-agent", "build"]
        )
        assert result.exit_code == 0, result.output
        rows = {a["name"]: a for a in _json.loads(result.output)["agents"]}
        assert rows["review-agent"]["managed"] is True
        assert rows["build"]["managed"] is False

    def test_builtin_never_claims_to_inherit(self, monkeypatch):
        """A builtin has no frontmatter to inherit through, so reporting
        inheritsFrom for it would be a lie."""
        result, _json = self._run(monkeypatch, [], ["build"])
        assert result.exit_code == 0, result.output
        assert _json.loads(result.output)["agents"][0]["inheritsFrom"] is None

    def test_text_table_survives_a_builtin_with_no_db_row(self, monkeypatch):
        from click.testing import CliRunner

        from lemoria import cli
        from lemoria.opencode_telemetry import AgentUsage, Telemetry

        class FakeQuery:
            def order_by(self_inner, *_a):
                return self_inner

            def all(self_inner):
                return [FakeAgent("review-agent")]

        class FakeApp:
            session = type("S", (), {"query": lambda s, m: FakeQuery()})()

            def close(self_inner):
                pass

        telemetry = Telemetry(available=True, reason=None)
        telemetry.by_agent["build"] = AgentUsage(
            name="build", model="opencode/big-pickle", variant="default",
            sessions=3, subagent_sessions=1, active_sessions=0, tokens=1000, cost=0.0,
        )
        monkeypatch.setattr(cli, "Lemoria", lambda *a, **k: FakeApp())
        monkeypatch.setattr(
            "lemoria.opencode_telemetry.OpenCodeTelemetry",
            lambda *a, **k: type("T", (), {"read": lambda self: telemetry})(),
        )
        result = CliRunner().invoke(cli.cli, ["agent", "status"])
        assert result.exit_code == 0, result.output
        assert "review-agent" in result.output
        assert "build" in result.output


class TestReportedModelAndActivity:
    """Two things the status view must not get wrong: which model an agent is
    actually on, and whether a subagent is currently working."""

    def test_reported_model_is_the_most_recent_session(self, opencode_db):
        """MAX() over a JSON blob compares strings, so the lexicographically
        largest model id wins -- which is not the model in use."""
        telemetry = OpenCodeTelemetry(opencode_db).read()
        assert telemetry.by_agent["orchestrator"].model == "opencode/big-pickle"

    def test_a_stale_model_does_not_win(self, opencode_db):
        telemetry = OpenCodeTelemetry(opencode_db).read()
        assert "zzz-stale" not in telemetry.by_agent["orchestrator"].model

    def test_live_subagent_sessions_are_counted(self, opencode_db):
        """A subagent session always has a parent_id. Filtering to roots made
        this structurally always zero, which is the number the user asked for."""
        telemetry = OpenCodeTelemetry(opencode_db).read()
        assert telemetry.by_agent["review-agent"].subagent_sessions == 2
        assert telemetry.by_agent["review-agent"].active_sessions == 1

    def test_root_sessions_are_still_counted_as_live(self, opencode_db):
        telemetry = OpenCodeTelemetry(opencode_db).read()
        assert telemetry.by_agent["orchestrator"].active_sessions == 1

    def test_null_token_fields_do_not_erase_a_message(self, tmp_path):
        """One NULL used to make the whole SUM expression NULL, and SUM skips
        NULLs, so the row vanished with no error.

        The risk moved with the data: a message whose JSON omits `output` (or
        the whole `cache` object) makes `json_extract` return NULL, and an
        un-guarded SUM would drop that turn's tokens silently."""
        path = tmp_path / "nulls.db"
        conn = sqlite3.connect(path)
        conn.execute(
            "CREATE TABLE session (id text PRIMARY KEY, agent text, model text,"
            " cost real, parent_id text, time_created integer, time_updated integer)"
        )
        conn.execute(
            "CREATE TABLE message (id text PRIMARY KEY, session_id text,"
            " time_created integer, data text)"
        )
        now = int(time.time() * 1000)
        conn.execute(
            "INSERT INTO session (id, agent, model, cost, parent_id, time_created,"
            " time_updated) VALUES (?,?,?,?,?,?,?)",
            ("a", "review-agent", '{"id":"m","providerID":"opencode"}', 0.0, None, now, now),
        )
        conn.executemany(
            "INSERT INTO message (id, session_id, time_created, data) VALUES (?,?,?,?)",
            [
                ("m1", "a", now, json.dumps({
                    "role": "assistant", "agent": "review-agent",
                    "providerID": "opencode", "modelID": "m",
                    "tokens": {"input": 500, "output": 50, "reasoning": 0,
                               "cache": {"read": 0, "write": 0}},
                })),
                # `output` missing and no `cache` object at all: both paths must
                # read as 0 instead of poisoning the sum.
                ("m2", "a", now, json.dumps({
                    "role": "assistant", "agent": "review-agent",
                    "providerID": "opencode", "modelID": "m",
                    "tokens": {"input": 700},
                })),
            ],
        )
        conn.commit()
        conn.close()
        telemetry = OpenCodeTelemetry(path).read()
        # 500+50 + 700+0: the second message must not disappear.
        assert telemetry.total_tokens == 1250
        assert telemetry.by_model["opencode/m"].input_tokens == 1200

    def test_a_database_without_messages_degrades_instead_of_raising(self, tmp_path):
        """opencode owns this schema. A build that drops `message` should cost
        us the report, not crash the timer that writes the panel record."""
        path = tmp_path / "no-messages.db"
        conn = sqlite3.connect(path)
        conn.execute("CREATE TABLE session (id text PRIMARY KEY, agent text)")
        conn.execute("INSERT INTO session (id, agent) VALUES ('a', 'build')")
        conn.commit()
        conn.close()
        telemetry = OpenCodeTelemetry(path).read()
        assert telemetry.available is False
        assert "message table" in telemetry.reason

    def test_record_is_not_world_readable(self, tmp_path, opencode_db):
        """Omarchy's own collectors write 600. Usage counts are not secret,
        but the record should not be more permissive than its neighbours."""
        from lemoria.omarchy import build_record as _build
        from lemoria.omarchy import write_record as _write

        destination = tmp_path / "usage" / "lemoria.json"
        _write(_build(OpenCodeTelemetry(opencode_db).read()), destination)
        assert destination.stat().st_mode & 0o077 == 0
