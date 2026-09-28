"""Tests for agent discovery, model pinning and opencode telemetry."""

import json
import sqlite3
import time

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
        ],
    )
    conn.executemany(
        "INSERT INTO message (id, session_id, time_created, data) VALUES (?,?,?,?)",
        [
            ("m1", "s1", now, json.dumps({"role": "assistant"})),
            ("m2", "s1", now, json.dumps({"role": "user"})),
            ("m3", "s2", now, json.dumps({"role": "assistant"})),
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
        assert telemetry.total_sessions == 4
        assert telemetry.total_tokens == 702
        assert telemetry.total_prompts == 2
        assert telemetry.total_cost == pytest.approx(0.25)

    def test_splits_root_and_subagent_sessions(self, opencode_db):
        telemetry = OpenCodeTelemetry(opencode_db).read()
        assert telemetry.by_agent["review-agent"].subagent_sessions == 2
        assert telemetry.by_agent["orchestrator"].subagent_sessions == 0

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


class TestOmarchyRecord:
    def test_record_satisfies_the_panel_contract(self, opencode_db):
        record = build_record(OpenCodeTelemetry(opencode_db).read())
        assert validate_record(record) == []
        assert record["id"] == "lemoria"
        assert record["schemaVersion"] == 1
        assert record["scope"] == "device"

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

    def test_write_is_atomic_and_leaves_no_temp_files(self, tmp_path, opencode_db):
        destination = tmp_path / "usage" / "lemoria.json"
        record = build_record(OpenCodeTelemetry(opencode_db).read())
        write_record(record, destination)
        assert json.loads(destination.read_text())["id"] == "lemoria"
        assert [p.name for p in destination.parent.iterdir()] == ["lemoria.json"]


class TestTimerUnits:
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

    def test_null_token_columns_do_not_erase_a_row(self, tmp_path):
        """One NULL used to make the whole SUM expression NULL, and SUM skips
        NULLs, so the row vanished with no error."""
        path = tmp_path / "nulls.db"
        conn = sqlite3.connect(path)
        conn.execute(
            "CREATE TABLE session (id text PRIMARY KEY, agent text, model text,"
            " cost real, parent_id text, time_created integer, time_updated integer,"
            " tokens_input integer, tokens_output integer, tokens_reasoning integer,"
            " tokens_cache_read integer, tokens_cache_write integer)"
        )
        now = int(time.time() * 1000)
        conn.executemany(
            "INSERT INTO session (id, agent, model, cost, parent_id, time_created,"
            " time_updated, tokens_input, tokens_output) VALUES (?,?,?,?,?,?,?,?,?)",
            [
                ("a", "review-agent", '{"id":"m","providerID":"opencode"}', 0.0, None, now, now, 500, 50),
                # tokens_output left NULL
                ("b", "review-agent", '{"id":"m","providerID":"opencode"}', 0.0, None, now, now, 700, None),
            ],
        )
        conn.commit()
        conn.close()
        telemetry = OpenCodeTelemetry(path).read()
        # 500+50 + 700+0: the second row must not disappear.
        assert telemetry.total_tokens == 1250

    def test_record_is_not_world_readable(self, tmp_path, opencode_db):
        """Omarchy's own collectors write 600. Usage counts are not secret,
        but the record should not be more permissive than its neighbours."""
        from lemoria.omarchy import build_record as _build
        from lemoria.omarchy import write_record as _write

        destination = tmp_path / "usage" / "lemoria.json"
        _write(_build(OpenCodeTelemetry(opencode_db).read()), destination)
        assert destination.stat().st_mode & 0o077 == 0
