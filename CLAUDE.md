# CLAUDE.md — Security Guardrail Auditor

This file is auto-loaded by Claude Code at session start. It contains the working conventions,
quality gates, and architectural constraints for this project.

---

## Project in One Sentence

Upload a Terraform or CloudFormation file → get a 0–100 risk score + actionable findings
for every misconfiguration, backed by 12 security rules and a full audit trail.

## Quick Start

```bash
pip install -e ".[dev]"          # install with dev dependencies
uvicorn app.main:app --reload    # start server → http://localhost:8000/dashboard
pytest tests/ -q                 # run all 120 tests
```

---

## Mandatory Workflow — Every Module, Every Time

```
SPEC → RED → GREEN → REFACTOR → SMOKE → COMMIT
```

1. **SPEC first** — read `SPEC.md` before writing any code. Every module has a 6-element spec.
2. **RED** — write all tests before the implementation. Tests must fail with `ImportError`.
3. **GREEN** — write the minimum code to pass. No extra features, no speculative abstractions.
4. **REFACTOR** — run the full quality gate. All 4 must pass before committing.
5. **SMOKE** — add edge-case tests in `tests/smoke/` that unit tests can't catch.
6. **COMMIT** — conventional commit message. Max 400 LOC per commit.

Deviations must be logged in `prompts.md` with a `DEVIATION NOTE`.

---

## Quality Gate — Must Pass Before Every Commit

```bash
ruff check app/ tests/          # linting + import order
mypy app/                        # strict type checking
bandit -r app/ -q                # security scan
pytest tests/ -q                 # 120 tests, coverage ≥ 85%
```

All four green = commit allowed. One red = fix before committing.

---

## Architecture Constraints (Do Not Violate)

- **Pydantic v2 everywhere** — all domain objects are `BaseModel`, not raw dicts.
  `Finding` is frozen. `severity` is `Literal["CRITICAL","HIGH","MEDIUM"]`. `risk_score` is `ge=0, le=100`.
- **FileParser is pure** — takes `bytes`, returns `(list[dict], bool)`. Never raises except on unsupported ext.
- **ScannerEngine is pure** — takes `list[dict]`, returns `list[Finding]`. Never raises on any input.
- **RiskScorer is pure** — takes `list[Finding]`, returns `int`. Formula: `min(CRITICAL×40 + HIGH×20 + MEDIUM×5, 100)`.
- **Rules are additive** — adding a rule = one `SecurityRule(...)` entry in `rules.py` + 2 test cases. Zero other files.
- **No business logic in routes** — routes orchestrate; scanner modules contain all logic.
- **SQLite default** — one env-var swap (`DATABASE_URL`) to Postgres. No schema changes needed.

---

## Adding a New Security Rule

1. Add fire + no-fire cases to `FIRE_CASES` / `NO_FIRE_CASES` in `tests/unit/test_scanner.py`
2. Run `pytest tests/unit/test_scanner.py -q` — 2 new parametrised cases must fail
3. Add `SecurityRule(...)` to `app/scanner/rules.py`
4. If rule targets specific resource types, add to `_RESOURCE_TYPE_FILTER` in `app/scanner/engine.py`
5. Run full quality gate — all green
6. Update the rules table in `ARCHITECTURE.md`

Use `/add-rule` slash command to automate this flow.

---

## Test Layout

```
tests/
├── unit/           # FileParser (18), ScannerEngine (40), RiskScorer (19)
├── integration/    # API routes (19), Dashboard (7)
└── smoke/          # End-to-end edge cases (20) — empty files, garbage input, all-violations
```

All tests use `Given / When / Then` naming. Integration and smoke tests use the `client` fixture
from `conftest.py` (in-memory SQLite, isolated per test).

---

## Key Files

| File | Purpose |
|------|---------|
| `prompts.md` | Full audit log — every turn, decision, bug, and learning |
| `SPEC.md` | 6-element module specs (source of truth for acceptance criteria) |
| `ARCHITECTURE.md` | System design, 12 rules table, API surface, DB schema |
| `ADR.md` | Architecture Decision Records — the *why* behind every major choice |
| `VISION.md` | 7 success criteria + 6 non-goals (check against this every 5 turns) |
| `app/scanner/rules.py` | 12 `SecurityRule` definitions — pure predicate functions |
| `app/scanner/engine.py` | `ScannerEngine` + `Finding` Pydantic model |
| `app/schemas/scan.py` | All API Pydantic schemas — the governance contract |

---

## Slash Commands (`.claude/commands/` on `feat/claude-commands` branch)

| Command | Does |
|---------|------|
| `/tdd-red` | Scaffold failing tests from SPEC AC |
| `/tdd-green` | Implement minimum code to pass tests |
| `/quality-gate` | Run all 4 gates in sequence |
| `/vision-check` | Verify all 7 success criteria, detect drift |
| `/add-rule` | Add a new security rule via full TDD cycle |

---

## What Not To Do

- Do not write implementation before tests — RED phase is mandatory
- Do not use raw `dict` for findings — use `Finding` Pydantic model
- Do not add business logic to FastAPI route handlers
- Do not skip the quality gate (`--no-verify` is never acceptable)
- Do not reference external AI tools in git commit messages or committed files
- Do not add features outside `SPEC.md` scope without updating the spec first
