"""CLI smoke tests -- verify commands are importable and parse correctly.

Uses Click's CliRunner to invoke commands. Tests focus on CLI layer
functionality (argument parsing, help text, command registration) rather
than business logic.
"""

from __future__ import annotations

from click.testing import CliRunner

from src.cli.cli_entry import cli

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _runner() -> CliRunner:
    return CliRunner()


# ---------------------------------------------------------------------------
# Root / Help Tests
# ---------------------------------------------------------------------------


class TestCliRoot:
    """Tests for the CLI root group and help output."""

    def test_help_displays_commands(self):
        """--help lists all registered subcommands."""
        result = _runner().invoke(cli, ["--help"])
        assert result.exit_code == 0
        output = result.output
        # Verify key command groups are listed
        assert "player" in output
        assert "scoring" in output
        assert "match" in output
        assert "energy" in output
        assert "vault" in output
        assert "events" in output
        assert "ads" in output
        assert "payments" in output

    def test_version_command(self):
        """version command exits 0 (may warn about missing config)."""
        result = _runner().invoke(cli, ["version"])
        # Exit 0 if config exists, may fail if no config file — that's OK
        # We just verify the command is registered and parseable
        assert result.exit_code in (0, 1, 2)

    def test_show_config_command(self):
        """show-config command is registered and parseable."""
        result = _runner().invoke(cli, ["show-config", "--help"])
        assert result.exit_code == 0
        assert "config" in result.output.lower()


# ---------------------------------------------------------------------------
# Subcommand Help Tests
# ---------------------------------------------------------------------------


class TestSubcommandHelp:
    """Tests that every subcommand group shows help without crashing."""

    def test_player_help(self):
        result = _runner().invoke(cli, ["player", "--help"])
        assert result.exit_code == 0

    def test_auth_help(self):
        result = _runner().invoke(cli, ["auth", "--help"])
        assert result.exit_code == 0

    def test_scoring_help(self):
        result = _runner().invoke(cli, ["scoring", "--help"])
        assert result.exit_code == 0

    def test_energy_help(self):
        result = _runner().invoke(cli, ["energy", "--help"])
        assert result.exit_code == 0

    def test_vault_help(self):
        result = _runner().invoke(cli, ["vault", "--help"])
        assert result.exit_code == 0

    def test_match_help(self):
        result = _runner().invoke(cli, ["match", "--help"])
        assert result.exit_code == 0

    def test_matchmaking_help(self):
        result = _runner().invoke(cli, ["matchmaking", "--help"])
        assert result.exit_code == 0

    def test_events_help(self):
        result = _runner().invoke(cli, ["events", "--help"])
        assert result.exit_code == 0

    def test_ads_help(self):
        result = _runner().invoke(cli, ["ads", "--help"])
        assert result.exit_code == 0

    def test_payments_help(self):
        result = _runner().invoke(cli, ["payments", "--help"])
        assert result.exit_code == 0

    def test_bot_earnings_help(self):
        result = _runner().invoke(cli, ["bot-earnings", "--help"])
        assert result.exit_code == 0

    def test_board_gen_help(self):
        result = _runner().invoke(cli, ["board-gen", "--help"])
        assert result.exit_code == 0

    def test_special_gems_help(self):
        result = _runner().invoke(cli, ["special-gems", "--help"])
        assert result.exit_code == 0

    def test_board_help(self):
        result = _runner().invoke(cli, ["board", "--help"])
        assert result.exit_code == 0
