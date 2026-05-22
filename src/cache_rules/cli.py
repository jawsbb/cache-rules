from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import typer
from rich.console import Console

from cache_rules import __version__
from cache_rules.checks.base import AuditContext
from cache_rules.checks.registry import ALL_CHECKS
from cache_rules.parser.transcripts import find_transcript_files, parse_transcript
from cache_rules.report.renderer import (
    build_cache_report,
    render_check_results,
    render_text,
    report_to_dict,
)

app = typer.Typer(
    name="cache-rules",
    help="Audit your Claude Code prompt-cache health from local JSONL transcripts.",
    no_args_is_help=True,
)

console = Console()


def _version_callback(value: bool) -> None:
    if value:
        console.print(f"cache-rules {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        "-V",
        callback=_version_callback,
        is_eager=True,
        help="Show version and exit.",
    ),
) -> None:
    """cache-rules CLI entry point."""


@app.command()
def cache(
    days: int = typer.Option(7, "--days", "-d", help="Time window in days."),
    project: str | None = typer.Option(
        None, "--project", "-p", help="Filter by project path substring."
    ),
    json_output: bool = typer.Option(False, "--json", help="Emit machine-readable JSON."),
    projects_dir: Path | None = typer.Option(
        None,
        "--projects-dir",
        help="Transcript directory to scan (default: ~/.claude/projects).",
    ),
) -> None:
    """Report real cache hit rate from local Claude Code transcripts."""
    turns = [
        turn
        for path in find_transcript_files(projects_dir)
        for turn in parse_transcript(path)
    ]
    report = build_cache_report(
        turns,
        window_days=days,
        project_filter=project,
        now=datetime.now(UTC),
    )
    if json_output:
        console.print_json(data=report_to_dict(report))
    else:
        render_text(report, console)


@app.command(name="all")
def audit(
    projects_dir: Path | None = typer.Option(
        None,
        "--projects-dir",
        help="Transcript directory to scan (default: ~/.claude/projects).",
    ),
) -> None:
    """Run every cache rule check against your transcripts."""
    turns = [
        turn
        for path in find_transcript_files(projects_dir)
        for turn in parse_transcript(path)
    ]
    context = AuditContext(turns=turns)
    results = [check.run(context) for check in ALL_CHECKS]
    render_check_results(results, console)


if __name__ == "__main__":
    app()
