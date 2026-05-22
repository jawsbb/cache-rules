from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

DEFAULT_PROJECTS_DIR = Path.home() / ".claude" / "projects"


@dataclass(frozen=True, slots=True)
class TranscriptTurn:
    """One assistant message from a Claude Code transcript, with its token usage."""

    timestamp: datetime
    session_id: str
    project_path: str
    model: str
    input_tokens: int
    cache_creation_tokens: int
    cache_read_tokens: int
    output_tokens: int
    is_sidechain: bool


def find_transcript_files(base_dir: Path | None = None) -> Iterator[Path]:
    """Yield every .jsonl transcript under the Claude Code projects directory."""
    base = base_dir if base_dir is not None else DEFAULT_PROJECTS_DIR
    if not base.is_dir():
        return
    yield from sorted(base.rglob("*.jsonl"))


def parse_transcript(path: Path) -> Iterator[TranscriptTurn]:
    """Stream-parse a transcript, yielding one TranscriptTurn per assistant message."""
    with path.open(encoding="utf-8") as handle:
        for raw_line in handle:
            raw_line = raw_line.strip()
            if not raw_line:
                continue
            try:
                event = json.loads(raw_line)
            except json.JSONDecodeError:
                continue
            if not isinstance(event, dict) or event.get("type") != "assistant":
                continue
            message = event.get("message")
            if not isinstance(message, dict):
                continue
            usage = message.get("usage")
            if not isinstance(usage, dict):
                continue
            yield TranscriptTurn(
                timestamp=datetime.fromisoformat(event["timestamp"]),
                session_id=event["sessionId"],
                project_path=event["cwd"],
                model=message["model"],
                input_tokens=usage["input_tokens"],
                cache_creation_tokens=usage["cache_creation_input_tokens"],
                cache_read_tokens=usage["cache_read_input_tokens"],
                output_tokens=usage["output_tokens"],
                is_sidechain=event["isSidechain"],
            )
