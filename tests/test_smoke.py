from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

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


def _write_transcript(directory: Path) -> None:
    directory.mkdir(parents=True)
    event = {
        "type": "assistant",
        "sessionId": "cli-test-session",
        "cwd": "/code/demo",
        "isSidechain": False,
        "timestamp": datetime.now(UTC).isoformat(),
        "message": {
            "role": "assistant",
            "model": "claude-opus-4-7",
            "usage": {
                "input_tokens": 100,
                "cache_creation_input_tokens": 200,
                "cache_read_input_tokens": 700,
                "output_tokens": 50,
            },
        },
    }
    (directory / "s.jsonl").write_text(json.dumps(event) + "\n")


def test_cache_command_renders_a_report(tmp_path: Path) -> None:
    projects = tmp_path / "projects"
    _write_transcript(projects / "demo")

    result = CliRunner().invoke(app, ["cache", "--projects-dir", str(projects)])

    assert result.exit_code == 0
    assert "Cache hit rate" in result.stdout


def test_cache_command_json_output_is_parseable(tmp_path: Path) -> None:
    projects = tmp_path / "projects"
    _write_transcript(projects / "demo")

    result = CliRunner().invoke(
        app, ["cache", "--projects-dir", str(projects), "--json"]
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["turn_count"] == 1
    assert payload["tokens"]["cache_read"] == 700


def test_all_command_runs_the_rule_checks(tmp_path: Path) -> None:
    projects = tmp_path / "projects"
    _write_transcript(projects / "demo")

    result = CliRunner().invoke(app, ["all", "--projects-dir", str(projects)])

    assert result.exit_code == 0
    assert "Model switching" in result.stdout
    assert "Fork safety" in result.stdout
