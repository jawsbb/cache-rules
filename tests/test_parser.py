from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from cache_rules.parser.transcripts import (
    TranscriptTurn,
    find_transcript_files,
    parse_transcript,
)

FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_transcript_maps_assistant_events_to_turns() -> None:
    turns = list(parse_transcript(FIXTURES / "valid_session.jsonl"))

    assert len(turns) == 2

    first = turns[0]
    assert first == TranscriptTurn(
        timestamp=datetime(2026, 5, 21, 10, 0, 5, tzinfo=UTC),
        session_id="11111111-aaaa-bbbb-cccc-000000000001",
        project_path="/Users/dev/projects/demo",
        model="claude-opus-4-7",
        input_tokens=10,
        cache_creation_tokens=2000,
        cache_read_tokens=0,
        output_tokens=150,
        is_sidechain=False,
    )

    second = turns[1]
    assert second.model == "claude-sonnet-4-6"
    assert second.cache_read_tokens == 2010
    assert second.is_sidechain is True


def test_parse_transcript_skips_malformed_blank_and_usageless_lines() -> None:
    turns = list(parse_transcript(FIXTURES / "corrupt_lines.jsonl"))

    assert len(turns) == 2
    assert [t.output_tokens for t in turns] == [7, 9]


def test_parse_transcript_handles_empty_file(tmp_path: Path) -> None:
    empty = tmp_path / "empty.jsonl"
    empty.write_text("")

    assert list(parse_transcript(empty)) == []


def test_parse_transcript_streams_a_large_file(tmp_path: Path) -> None:
    big = tmp_path / "big.jsonl"
    event = (
        '{"type":"assistant","sessionId":"s","cwd":"/p","isSidechain":false,'
        '"timestamp":"2026-05-21T10:00:00.000Z","message":{"role":"assistant",'
        '"model":"claude-opus-4-7","usage":{"input_tokens":1,'
        '"cache_creation_input_tokens":2,"cache_read_input_tokens":3,'
        '"output_tokens":4}}}\n'
    )
    big.write_text(event * 10_000)

    turns = list(parse_transcript(big))

    assert len(turns) == 10_000
    assert turns[-1].cache_read_tokens == 3


def test_find_transcript_files_discovers_jsonl_recursively(tmp_path: Path) -> None:
    (tmp_path / "proj-a").mkdir()
    (tmp_path / "proj-b").mkdir()
    (tmp_path / "proj-a" / "s1.jsonl").write_text("")
    (tmp_path / "proj-a" / "s2.jsonl").write_text("")
    (tmp_path / "proj-b" / "s3.jsonl").write_text("")
    (tmp_path / "proj-a" / "notes.txt").write_text("ignore me")

    found = list(find_transcript_files(tmp_path))

    assert found == [
        tmp_path / "proj-a" / "s1.jsonl",
        tmp_path / "proj-a" / "s2.jsonl",
        tmp_path / "proj-b" / "s3.jsonl",
    ]


def test_find_transcript_files_returns_nothing_for_missing_dir(tmp_path: Path) -> None:
    assert list(find_transcript_files(tmp_path / "does-not-exist")) == []
