"""Tests for CLI commands."""

from click.testing import CliRunner

from lemoria.cli import cli


class TestCLI:
    """Test CLI command existence and help output."""

    def test_version_comes_from_the_installed_metadata(self):
        """`__version__` is read from the package metadata, not a literal.

        A hardcoded copy is exactly how the two drifted apart (0.1.0 here
        against 0.2.0 in pyproject) — nothing read the literal, so nothing
        caught the disagreement.
        """
        import tomllib
        from pathlib import Path as _Path

        from lemoria import __version__

        pyproject = tomllib.loads(
            _Path(__file__).resolve().parents[1].joinpath("pyproject.toml").read_text()
        )
        assert __version__ == pyproject["project"]["version"]

    def test_version_flag_prints_it(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "lemoria" in result.output

    def test_flow_help(self):
        """Should show flow subcommands."""
        runner = CliRunner()
        result = runner.invoke(cli, ["flow", "--help"])
        assert result.exit_code == 0
        assert "step" in result.output
        assert "status" in result.output

    def test_vault_help(self):
        """Should show vault subcommands."""
        runner = CliRunner()
        result = runner.invoke(cli, ["vault", "--help"])
        assert result.exit_code == 0
        assert "sync" in result.output
        assert "restore" in result.output

    def test_spec_help(self):
        """Should show spec subcommands."""
        runner = CliRunner()
        result = runner.invoke(cli, ["spec", "--help"])
        assert result.exit_code == 0
        assert "create" in result.output
        assert "list" in result.output

    def test_error_help(self):
        """Should show error subcommands."""
        runner = CliRunner()
        result = runner.invoke(cli, ["error", "--help"])
        assert result.exit_code == 0
        assert "log" in result.output
        assert "list" in result.output
        assert "resolve" in result.output

    def test_context_help(self):
        """Should show context subcommands."""
        runner = CliRunner()
        result = runner.invoke(cli, ["context", "--help"])
        assert result.exit_code == 0
        assert "set" in result.output
        assert "get" in result.output

    def test_project_help(self):
        """Should show project subcommands."""
        runner = CliRunner()
        result = runner.invoke(cli, ["project", "--help"])
        assert result.exit_code == 0
        assert "create" in result.output
        assert "list" in result.output

    def test_conv_help(self):
        """Should show conversation subcommands."""
        runner = CliRunner()
        result = runner.invoke(cli, ["conv", "--help"])
        assert result.exit_code == 0
        assert "create" in result.output
        assert "add" in result.output

    def test_configure_prints_model_effort_workflow(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["configure"])
        assert result.exit_code == 0
        assert "lemoria agent model <agent> <provider/model> --effort <effort>" in result.output

    def test_agent_model_accepts_effort_alias(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["agent", "model", "--help"])
        assert result.exit_code == 0
        assert "--effort" in result.output

    def test_agent_effort_command_exists(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["agent", "effort", "--help"])
        assert result.exit_code == 0
        assert "EFFORT" in result.output

    def test_omarchy_install_fails_clearly_when_omarchy_cli_missing(self, monkeypatch):
        import shutil

        _stub_omarchy_install_side_effects(monkeypatch)
        monkeypatch.setattr(shutil, "which", lambda name: None if name == "omarchy" else "/usr/bin/systemctl")

        runner = CliRunner()
        result = runner.invoke(cli, ["omarchy", "install"])

        assert result.exit_code != 0
        assert "omarchy CLI not found in PATH" in result.output
        assert "omarchy plugin enable lemoria.usage --after omarchy.agents" in result.output

    def test_omarchy_install_surfaces_plugin_enable_failure(self, monkeypatch):
        import shutil
        import subprocess

        _stub_omarchy_install_side_effects(monkeypatch)
        monkeypatch.setattr(shutil, "which", lambda name: f"/usr/bin/{name}")
        monkeypatch.setattr(
            subprocess,
            "run",
            lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 1, stdout="", stderr="disabled by policy"),
        )

        runner = CliRunner()
        result = runner.invoke(cli, ["omarchy", "install"])

        assert result.exit_code != 0
        assert "Could not enable lemoria.usage automatically" in result.output
        assert "disabled by policy" in result.output


def _stub_omarchy_install_side_effects(monkeypatch):
    from lemoria import budget, omarchy
    from lemoria import opencode_telemetry as telemetry

    monkeypatch.setattr(omarchy, "remove_legacy_agents_record", lambda: False)
    monkeypatch.setattr(omarchy, "install_plugin", lambda: "/tmp/plugin")
    monkeypatch.setattr(omarchy, "install_codex_stabilizer", lambda: ("/tmp/service", "/tmp/codex"))
    monkeypatch.setattr(omarchy, "install_timer", lambda interval: ("/tmp/lemoria.service", "/tmp/lemoria.timer"))
    monkeypatch.setattr(omarchy, "build_record", lambda *args, **kwargs: {"ok": True})
    monkeypatch.setattr(omarchy, "write_record", lambda record: "/tmp/record.json")
    monkeypatch.setattr(omarchy, "stabilize_codex_record", lambda: (False, "unchanged"))
    monkeypatch.setattr(omarchy, "known_agents", list)
    monkeypatch.setattr(omarchy, "current_default_model", lambda: None)
    monkeypatch.setattr(budget.Budget, "load", staticmethod(dict))

    class FakeTelemetry:
        def read(self):
            return {}

    monkeypatch.setattr(telemetry, "OpenCodeTelemetry", FakeTelemetry)


class TestCLICommands:
    """Test CLI command behavior with test data."""

    def test_init_help(self):
        """Should show init command."""
        runner = CliRunner()
        result = runner.invoke(cli, ["init", "--help"])
        assert result.exit_code == 0

    def test_flow_step_help(self):
        """Should show flow step options."""
        runner = CliRunner()
        result = runner.invoke(cli, ["flow", "step", "--help"])
        assert result.exit_code == 0
        assert "FLOW_ID" in result.output
        assert "STEP_NAME" in result.output
        assert "--status" in result.output

    def test_flow_status_help(self):
        """Should show flow status options."""
        runner = CliRunner()
        result = runner.invoke(cli, ["flow", "status", "--help"])
        assert result.exit_code == 0
        assert "FLOW_ID" in result.output
