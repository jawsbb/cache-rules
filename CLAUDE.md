# Conventions du projet — cache-rules

## Contexte

`cache-rules` est une CLI Python qui mesure le cache hit rate Claude Code à partir
des transcripts JSONL locaux (`~/.claude/projects/`). Pas de SaaS, pas de backend,
pas de télémétrie — tout tourne en local. Voir `ROADMAP.md` pour les phases.

## Style

- Python 3.11+, types stricts partout — `from __future__ import annotations` en tête de fichier.
- Pas de `print()` direct : passer par `rich.console` (un helper centralisé dans `report/`).
- Pas de framework lourd (pas de Django, Flask, etc.) — c'est une CLI.
- Imports triés par `ruff` (`uv run ruff check --fix .`).

## Tests

- Chaque nouveau check/parser a au moins 1 test unitaire.
- Les fixtures `.jsonl` doivent être ANONYMISÉES — pas de vrais paths utilisateur, pas de contenu personnel.
- Coverage cible : 70%+.

## Commits

- Conventional commits (`feat:`, `fix:`, `chore:`, `docs:`, `test:`).
- Un commit par feature logique, pas un commit géant en fin de journée.

## Architecture

- Les `checks/` ne font JAMAIS d'I/O directement : ils consomment un `AuditContext` déjà construit.
- Les `parser/` ne font JAMAIS de logique métier : juste de la lecture/parsing.
- Tout ce qui est affichage vit dans `report/`.

## Commandes

```bash
uv sync                      # installer / mettre à jour les deps
uv run cache-rules --help    # lancer la CLI
uv run pytest                # tests
uv run ruff check .          # lint
uv run ruff check --fix .    # lint + autofix
```
