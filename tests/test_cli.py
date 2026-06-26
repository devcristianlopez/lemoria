"""Tests for CLI commands."""

from lemoria.cli import cli
from click.testing import CliRunner


class TestCLI:
    """Test CLI command existence and help output."""

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
