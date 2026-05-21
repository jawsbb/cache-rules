# cache-rules — Roadmap

## Vision

Partir du repo `cache-audit` (une Skill markdown heuristique) et le transformer en **un vrai outil de mesure** du cache hit rate Claude Code / API Anthropic, avec recommandations actionnables et calcul de coût en euros réels.

À terme : un framework d'audit pour tout l'écosystème Claude (cache, Skills, MCP servers).

---

## État actuel du repo

- 1 fichier `cache-audit/SKILL.md` (12K)
- Audit purement heuristique : Claude lit des fichiers et devine si les 6 règles sont respectées
- Pas de mesure réelle, pas de code, pas de tests
- Installation par `curl` d'un seul fichier

**À conserver** : les 6 règles (Ordering, Message injection, Tool stability, Model switching, Dynamic content size, Fork safety) — c'est le bon framework conceptuel.

**À remplacer** : tout le reste.

---

## Stack technique cible

- **Python 3.11+** (parsing JSON, écosystème mature, accessible)
- **`uv`** pour la gestion deps + packaging (plus rapide que pip)
- **`typer`** pour la CLI (typage natif, sortie propre)
- **`rich`** pour le rendu terminal (tableaux, couleurs)
- **`pytest`** pour les tests
- **`ruff`** pour le lint
- **GitHub Actions** pour CI dès le début

Pourquoi pas Node/TS : on veut un binaire installable via `uv tool install` ou `pipx`, sans demander à l'utilisateur d'installer Node.

---

## Structure de repo cible

```
cache-rules/
├── README.md
├── pyproject.toml
├── ROADMAP.md                     # ce fichier
├── src/
│   └── cache_rules/
│       ├── __init__.py
│       ├── cli.py                 # point d'entrée typer
│       ├── parser/
│       │   ├── __init__.py
│       │   └── transcripts.py     # parse les .jsonl de Claude Code
│       ├── metrics/
│       │   ├── __init__.py
│       │   ├── cache.py           # calcul cache hit rate
│       │   └── cost.py            # conversion en €
│       ├── checks/
│       │   ├── __init__.py
│       │   ├── base.py            # interface CheckResult
│       │   ├── rule1_ordering.py
│       │   ├── rule2_messages.py
│       │   ├── rule3_tools.py
│       │   ├── rule4_models.py
│       │   ├── rule5_size.py
│       │   └── rule6_forks.py
│       └── report/
│           ├── __init__.py
│           └── renderer.py        # rendu rich + export JSON
├── tests/
│   ├── fixtures/
│   │   └── sample_transcripts/    # .jsonl de test commités
│   ├── test_parser.py
│   ├── test_metrics.py
│   └── test_checks.py
├── skills/
│   └── cache-rules/
│       └── SKILL.md               # version skill conservée, met juste à jour le code
└── .github/
    └── workflows/
        ├── test.yml
        └── release.yml
```

---

## Phase 1 — Le MVP qui mesure vraiment (semaine 1-2)

**Objectif** : à la fin de cette phase, `cache-rules cache` lit tes transcripts locaux et te dit ton vrai cache hit rate sur les 7 derniers jours, avec une estimation €.

### 1.1 — Bootstrap le projet — **done**

- [x] `uv init` dans le repo
- [x] Migrer le `SKILL.md` actuel dans `skills/cache-rules/`
- [x] Setup `pyproject.toml` avec deps : `typer`, `rich`, `pydantic`
- [x] Setup `pytest`, `ruff`, `.gitignore` Python
- [x] Premier commit : "chore: bootstrap project structure"

### 1.2 — Parser de transcripts

Claude Code stocke les sessions dans `~/.claude/projects/<encoded-path>/<session-uuid>.jsonl`. Chaque ligne est un événement JSON. Les events `assistant` contiennent un champ `message.usage` avec :
- `input_tokens`
- `output_tokens`
- `cache_creation_input_tokens`
- `cache_read_input_tokens`

**À implémenter dans `parser/transcripts.py`** :

```python
@dataclass
class TranscriptTurn:
    timestamp: datetime
    session_id: str
    project_path: str
    model: str
    input_tokens: int
    cache_creation_tokens: int
    cache_read_tokens: int
    output_tokens: int

def find_transcript_files(base_dir: Path = None) -> Iterator[Path]:
    """Yield all .jsonl files under ~/.claude/projects/"""

def parse_transcript(path: Path) -> Iterator[TranscriptTurn]:
    """Stream-parse a transcript, yielding one TranscriptTurn per assistant message."""
```

**⚠️ À vérifier en local** : le format exact des `.jsonl` peut avoir évolué. Première étape : `cat un-fichier.jsonl | head -3 | jq .` pour confirmer la structure réelle. Adapter le parser à ce que tu trouves.

### 1.3 — Métriques

Dans `metrics/cache.py` :

```python
def cache_hit_rate(turns: list[TranscriptTurn]) -> float:
    """cache_read / (cache_read + cache_creation + input_no_cache)"""

def hit_rate_by_session(turns) -> dict[str, float]
def hit_rate_by_day(turns) -> dict[date, float]
def hit_rate_by_project(turns) -> dict[str, float]
```

Dans `metrics/cost.py` : pricing officiel par modèle (cache_read = 0.1x du prix input, cache_creation = 1.25x). Pour la première version, hardcode les prix Sonnet 4.6 et mets un TODO pour fetch dynamique.

### 1.4 — CLI minimale

```bash
cache-rules cache                    # rapport sur les 7 derniers jours, tous projets
cache-rules cache --days 30          # range custom
cache-rules cache --project foo      # filtrer par projet
cache-rules cache --json             # export JSON pour CI
```

Sortie type :

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  CACHE AUDIT — 7 derniers jours
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Cache hit rate :     73.2%        (cible : >90%)
Tokens lus cache :   4.2M
Tokens créés cache : 890k
Tokens hors cache :  650k
Coût estimé :        12.40€       (sans cache : ~45€, économie 72%)

Top 3 sessions avec cache cassé :
  1. session-abc123 (project: foo)   hit rate 12%  — coût 4.20€
  2. session-def456 (project: bar)   hit rate 28%  — coût 2.10€
  3. session-ghi789 (project: foo)   hit rate 41%  — coût 1.80€

→ Run `cache-rules cache --session abc123` pour analyser
```

### 1.5 — Tests

- Commit 5-10 fichiers `.jsonl` de fixtures (anonymisés) dans `tests/fixtures/`
- Tests parser : format valide, format corrompu, fichier vide, gros fichier
- Tests métriques : valeurs connues d'avance

### 1.6 — Livrable Phase 1

- README clair avec un GIF de la CLI en action
- `uv tool install cache-rules` fonctionne
- Au moins 30 stars en ciblant 2 communautés : r/ClaudeAI et le Discord Anthropic Builders
- Un blog post : "I measured my real Claude Code cache hit rate — here's what I found"

---

## Phase 2 — Audit complet des 6 règles (semaine 3-4)

**Objectif** : ramener les 6 checks de la Skill originale en code Python, mais cette fois avec des chiffres mesurés, pas heuristiques.

### 2.1 — Refactor en architecture de checks

Interface dans `checks/base.py` :

```python
class Severity(Enum):
    PASS = "pass"
    WARNING = "warning"
    FAIL = "fail"
    MANUAL = "manual"

@dataclass
class CheckResult:
    rule_id: int
    rule_name: str
    severity: Severity
    message: str
    evidence: dict           # données brutes qui appuient la conclusion
    fix: str | None          # action concrète à prendre

class Check(Protocol):
    def run(self, ctx: AuditContext) -> CheckResult: ...
```

`AuditContext` agrège : transcripts parsés, contenu des `settings.json`, contenu des `CLAUDE.md`, hooks détectés.

### 2.2 — Implémenter les 6 checks

Chaque check est un fichier dans `checks/`. Pour chaque check, transformer l'heuristique de la Skill en mesure :

- **Rule 1 (Ordering)** : analyse statique des fichiers de config + détection de patterns suspects (timestamps, variables dynamiques) via regex
- **Rule 2 (Messages)** : parser les hooks référencés, vérifier qu'ils produisent du JSON avec `hookSpecificOutput.additionalContext`
- **Rule 3 (Tool stability)** : comparer la liste de tools entre les différents turns dans les transcripts → si elle change mid-session, FAIL avec preuve
- **Rule 4 (Model switching)** : grep le champ `model` dans tous les turns d'une session, FAIL si plusieurs valeurs
- **Rule 5 (Dynamic size)** : sur les `n` dernières sessions, mesurer la taille moyenne et p99 du contenu dynamique injecté
- **Rule 6 (Fork safety)** : MANUAL pour l'instant, documenter

### 2.3 — Commande agrégée

```bash
cache-rules all               # tous les checks
cache-rules rule 3            # un seul check
cache-rules watch             # mode continu (re-run toutes les 10min)
```

---

## Phase 3 — Sortie de Claude Code, vers l'API Anthropic (semaine 5-6)

**Objectif** : auditer aussi les usages directs de l'API Anthropic, pas que Claude Code.

### 3.1 — Adaptateurs

Refactorer pour que `TranscriptTurn` puisse venir de plusieurs sources :

- **Claude Code transcripts** (déjà fait)
- **Logs proxy custom** (l'utilisateur pointe la CLI vers un fichier de logs)
- **Anthropic Console export** (l'utilisateur télécharge ses logs depuis la console)

Pattern : un dossier `sources/` avec une interface commune.

### 3.2 — Mode "live"

Optionnel mais cool : un proxy local que l'utilisateur peut faire pointer son SDK Anthropic dessus. La CLI accumule les métriques en temps réel et affiche un dashboard `rich` qui se met à jour.

```bash
cache-rules live --port 8080
# Set ANTHROPIC_BASE_URL=http://localhost:8080 dans ton app
```

---

## Phase 4 — Audit des MCP servers (semaine 7+)

**Objectif** : pivoter du "cache" vers le "tout AI tools". Le moment où le projet devient unique.

### 4.1 — MCP server cost audit

```bash
cache-rules mcp <server-url-or-command>
```

Lance le serveur, énumère ses tools, mesure :
- Nombre total de tokens consommés par les tool descriptions
- Verbosity score (descriptions trop longues, schemas redondants)
- Detected anti-patterns (mention du nom du tool dans la description, etc.)

### 4.2 — MCP server security check (léger)

Pas refaire MCPTox/MindGuard, mais détecter les patterns évidents :
- Tool descriptions contenant des instructions impératives suspectes ("ignore previous", "always", etc.)
- Permissions excessives (OAuth scopes demandés)
- Pas de validation d'input visible dans le schema

### 4.3 — Skill audit

```bash
cache-rules skill <path-to-SKILL.md>
```

Mesure :
- Taille en tokens du SKILL.md
- Présence de bonnes pratiques (frontmatter `name`/`description` présent, exemples concrets)
- Trigger ambigu détecté

---

## Règles de qualité pour Claude Code

À mettre dans `CLAUDE.md` à la racine pour cadrer l'exécution :

```markdown
# Conventions du projet

## Style
- Python 3.11+, types stricts partout (utiliser `from __future__ import annotations`)
- Pas de `print()` direct, utiliser `rich.console` via un helper centralisé
- Pas de framework lourd (pas de Django, Flask, etc.) — c'est une CLI
- Imports triés par `ruff`

## Tests
- Chaque nouveau check/parser a au moins 1 test unitaire
- Les fixtures `.jsonl` doivent être ANONYMISÉES (pas de vrais path utilisateur, pas de contenu personnel)
- Coverage cible : 70%+

## Commits
- Conventional commits (`feat:`, `fix:`, `chore:`, `docs:`, `test:`)
- Un commit par feature logique, pas un commit géant en fin de journée

## Architecture
- Les `checks/` ne font JAMAIS d'I/O directement, ils consomment un `AuditContext` déjà construit
- Les `parser/` ne font JAMAIS de logique métier, juste de la lecture/parsing
- Tout ce qui est affichage est dans `report/`
```

---

## Anti-objectifs (ce qu'on ne fait PAS)

- Pas de SaaS, pas de backend, pas d'auth — tout tourne en local
- Pas d'IA pour analyser le code de l'utilisateur, on reste sur de la mesure et des règles déterministes
- Pas de support multi-LLM (OpenAI, Gemini) en Phase 1-3 — focus Claude, on élargira plus tard si traction
- Pas de UI web avant la Phase 5+ (et seulement si la CLI a traction)

---

## Mesure du succès

- **Phase 1** : 50 stars GitHub, 1 issue ouverte par un utilisateur externe
- **Phase 2** : 200 stars, 5 contributeurs externes, mentionné dans une newsletter AI
- **Phase 3** : intégré dans au moins 1 CI/CD d'un projet open-source
- **Phase 4** : référence "comment auditer un MCP server" sur Google
