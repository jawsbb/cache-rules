from __future__ import annotations

import typer
from rich.console import Console

from cache_rules import __version__

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
) -> None:
    """Report real cache hit rate from local Claude Code transcripts. (stub)"""
    console.print(
        "[yellow]cache: not implemented yet.[/yellow] "
        f"Will scan the last {days} day(s)"
        + (f", project filter={project!r}" if project else "")
        + (", JSON output" if json_output else "")
        + "."
    )
    raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
