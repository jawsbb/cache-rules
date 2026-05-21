from __future__ import annotations

from typer.testing import CliRunner

from cache_rules import __version__
from cache_rules.cli import app


def test_version_matches_package() -> None:
    assert __version__ == "0.1.0"


def test_cli_version_flag() -> None:
    result = CliRunner().invoke(app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.stdout


def test_cli_help_lists_cache_command() -> None:
    result = CliRunner().invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "cache" in result.stdout
