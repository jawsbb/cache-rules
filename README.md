<div align="center">

# cache-rules

**Measure your real Claude Code cache hit rate from the JSONL transcripts on your disk.**
No proxy. No telemetry. No API call.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-3776AB.svg)](https://www.python.org/downloads/)
[![Status: pre-alpha](https://img.shields.io/badge/status-pre--alpha-orange.svg)](#roadmap)
[![Built with uv](https://img.shields.io/badge/built%20with-uv-blueviolet)](https://github.com/astral-sh/uv)

</div>

---

## Why this exists

Prompt caching is what makes Claude Code affordable at scale. Done right, you pay ~10% of the input-token price on every turn. Done wrong, costs explode silently — and nothing in the UI warns you.

Most existing tools "audit" your setup heuristically: an agent reads your config files and guesses whether the cache is healthy. **cache-rules is different.** It parses the JSONL transcripts that Claude Code already writes to `~/.claude/projects/` and computes the *real* hit rate from the numbers Anthropic returned: `cache_read_input_tokens`, `cache_creation_input_tokens`, `input_tokens`.

> **Measure, don't guess.**

Everything runs locally. No data leaves your machine.

---

## Status

This is **pre-alpha** — only `--version` and `--help` work today. The repository ships:

1. A **Python CLI** (this project) that will compute your cache hit rate, cost, and configuration health.
2. A **bundled Claude Code skill** in [`skills/cache-rules/`](skills/cache-rules/) — the heuristic predecessor that scores your setup against the six prompt-cache rules. Install it today, get measured numbers tomorrow.

See the [Roadmap](#roadmap) for what's coming in each phase.

---

## Quick start (skill, available now)

The bundled Claude Code skill works today. It reads your live config and scores it against the six prompt-cache rules.

```bash
# Global install (all projects)
mkdir -p ~/.claude/skills/cache-rules
curl -o ~/.claude/skills/cache-rules/SKILL.md \
  https://raw.githubusercontent.com/jawsbb/cache-rules/main/skills/cache-rules/SKILL.md

# Or per-project
mkdir -p .claude/skills/cache-rules
curl -o .claude/skills/cache-rules/SKILL.md \
  https://raw.githubusercontent.com/jawsbb/cache-rules/main/skills/cache-rules/SKILL.md
```

Restart your Claude Code session, then invoke with:

```
/cache-rules
```

or say `"audit my caching"`.

---

## Quick start (CLI, pre-alpha)

```bash
git clone https://github.com/jawsbb/cache-rules.git
cd cache-rules
uv sync
uv run cache-rules --help
```

Once Phase 1 ships, you'll be able to:

```bash
uv tool install cache-rules
cache-rules cache                 # 7-day hit rate report
cache-rules cache --days 30       # custom window
cache-rules cache --project foo   # filter by project
cache-rules cache --json          # machine-readable
```

---

## The six rules

The framework `cache-rules` is built on. Every rule will become a measured check in Phase 2.

| # | Rule | What breaks it |
|:-:|:-----|:--------------|
| **1** | **Ordering** | Dynamic data (timestamps, git status) in the system prompt prefix |
| **2** | **Message injection** | Editing the system prompt mid-session instead of using `<system-reminder>` |
| **3** | **Tool stability** | Adding or removing tools mid-conversation |
| **4** | **Model switching** | Switching models inside the same conversation thread |
| **5** | **Dynamic content size** | Injecting thousands of tokens of dynamic data each turn |
| **6** | **Fork safety** | Compaction or subagent calls that don't share the parent's prefix |

The full text and rationale for each rule live in [`skills/cache-rules/SKILL.md`](skills/cache-rules/SKILL.md).

---

## Example output (planned)

```text
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  CACHE-RULES — last 7 days
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Cache hit rate :     73.2%        (target : >90%)
Cache reads    :     4.2M tokens
Cache writes   :     890k tokens
Uncached input :     650k tokens
Estimated cost :     12.40€       (without cache: ~45€, saved 72%)

Top 3 sessions with broken cache:
  1. session-abc123 (project: foo)   hit rate  12%  —  4.20€
  2. session-def456 (project: bar)   hit rate  28%  —  2.10€
  3. session-ghi789 (project: foo)   hit rate  41%  —  1.80€

→ Run `cache-rules cache --session abc123` to drill in.
```

---

## Roadmap

| Phase | What lands | Status |
|:-----:|:-----------|:------:|
| **1.1** | Python project bootstrap (CLI scaffold, tests, lint, CI-ready) | done |
| **1.2** | JSONL transcript parser for `~/.claude/projects/` | next |
| **1.3** | Hit rate + cost metrics, rich terminal report | |
| **1.4** | JSON output for CI integration | |
| **2** | The six checks, each measured (not heuristic) with evidence + fix | |
| **3** | Sources beyond Claude Code: proxy logs, Anthropic Console exports | |
| **4** | MCP server audit (token footprint, anti-pattern detection) + Skill audit | |

Full plan in [`ROADMAP.md`](ROADMAP.md).

---

## Project layout

```text
src/cache_rules/         Python CLI (typer + rich)
├── cli.py               entry point
├── parser/              Phase 1.2 — JSONL transcript parsing
├── metrics/             Phase 1.3 — cache hit rate, cost
├── checks/              Phase 2   — the six rule checks
└── report/              Phase 1.4 — rich terminal output, JSON export

skills/cache-rules/      Bundled Claude Code skill (heuristic)
tests/                   pytest suite + .jsonl fixtures
ROADMAP.md               Phase-by-phase plan
```

---

## Anti-goals

What `cache-rules` will **never** do:

- No SaaS, no backend, no auth — everything runs locally
- No LLM analyzing your code; deterministic measurement only
- No telemetry, no analytics, no "anonymous usage data"
- No multi-provider support (OpenAI, Gemini) in Phase 1–3 — Claude first

---

## Acknowledgments

The bundled `skills/cache-rules/SKILL.md` is derived from the original [cache-audit](https://github.com/ussumant/cache-audit) Claude Code skill by Sumant. The six-rule framework that the CLI builds on comes from that work. See [NOTICE](NOTICE).

The framework itself is grounded in Thariq Shihipar's thread *["Lessons from Building Claude Code: Prompt Caching Is Everything"](https://x.com/trq212)*.

---

## License

[MIT](LICENSE) © 2026 Jules Koehler
