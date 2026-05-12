# Enterprise Security Guardrail Auditor

**Wolters Kluwer Graduate Vibe Coding Challenge — Project 2**
**Engineer:** Adrian Sebuliba | **Tagle:** Navigator with Catalyst edge — Confident Operator

Upload a Terraform (`.tf`) or CloudFormation (`.json` / `.yaml`) file.
Get a risk score, colour-coded severity breakdown, and actionable remediation for every violation — in seconds.

---

## Quick Start

```bash
# Install (Python 3.12+)
pip install -e ".[dev]"

# Run
uvicorn app.main:app --reload

# Open
http://localhost:8000/dashboard
```

---

## Features

| Feature | Detail |
|---------|--------|
| **12 Security Rules** | CRITICAL × 4, HIGH × 4, MEDIUM × 4 |
| **Risk Score 0–100** | `min(CRITICAL×40 + HIGH×20 + MEDIUM×5, 100)` — deterministic, auditable |
| **Actionable Findings** | Every finding includes `rule_id`, `severity`, `title`, `description`, `remediation` |
| **Pydantic v2 Governance** | All API boundaries validated — severity is `Literal`, score is `ge=0, le=100` |
| **Interactive Dashboard** | Bootstrap 5 + Chart.js — risk gauge, severity chart, top rules, recent scans |
| **API-first** | Full OpenAPI spec at `/openapi.json` |
| **Zero crashes** | Malformed, empty, binary inputs all return 202 (never 500) |

---

## Security Rules

| Rule ID | Severity | Trigger |
|---------|----------|---------|
| `S3_PUBLIC_ACL` | CRITICAL | `acl = "public-read"` / `"public-read-write"` |
| `SSH_OPEN_TO_WORLD` | CRITICAL | Port 22 ingress to `0.0.0.0/0` |
| `RDP_OPEN_TO_WORLD` | CRITICAL | Port 3389 ingress to `0.0.0.0/0` |
| `WILDCARD_IAM_ACTION` | CRITICAL | IAM action `"*"` |
| `UNENCRYPTED_EBS` | HIGH | `encrypted = false` |
| `UNENCRYPTED_RDS` | HIGH | `storage_encrypted = false` |
| `PUBLIC_RDS` | HIGH | `publicly_accessible = true` |
| `HARDCODED_SECRET` | HIGH | Config key / SSM name matches `password\|secret\|token\|api_key` |
| `S3_VERSIONING_DISABLED` | MEDIUM | Versioning block absent or `enabled = false` |
| `CLOUDTRAIL_DISABLED` | MEDIUM | `enable_logging = false` |
| `UNRESTRICTED_EGRESS` | MEDIUM | All-port egress to `0.0.0.0/0` |
| `MISSING_REQUIRED_TAGS` | MEDIUM | Resource missing `Name` or `Environment` tag |

---

## API

| Method | Path | Description | Status |
|--------|------|-------------|--------|
| `POST` | `/api/scan` | Upload IaC file | 202 / 415 / 422 / 413 |
| `GET` | `/api/scan/{id}` | Full scan result + findings | 200 / 404 |
| `GET` | `/api/scans` | History, last 50 | 200 |
| `GET` | `/api/health` | Health check | 200 |
| `GET` | `/dashboard` | HTML dashboard | 200 |

---

## Architecture

```
FileParser  →  ScannerEngine  →  RiskScorer  →  SQLite
   ↑              (12 rules)       (0-100)        ↑
bytes             Pydantic            int       async ORM
                  Finding
                  (frozen)
                     ↓
              FastAPI routes
              (Pydantic schemas)
                     ↓
              Jinja2 Dashboard
```

**Key design decisions:**

- **SQLite** — zero infrastructure, file-based, one env-var swap to Postgres
- **Pydantic v2 everywhere** — `Finding` is frozen, severity is `Literal`, risk score is range-validated; invalid data raises `ValidationError`, never silently corrupts
- **Rule engine as pure functions** — each rule is a `Callable[[dict], bool]`; adding a rule = one entry, zero other files change
- **API-first** — all state readable as JSON; dashboard is a thin template layer over the same data

---

## Test Suite

```
tests/
├── unit/          18 parser + 40 scanner + 19 scorer tests
├── integration/   19 API + 7 dashboard tests
└── smoke/         20 end-to-end edge case tests
                   ────────────────────────────────
                   120 tests  ·  86% coverage
```

Quality gates on every commit: `ruff` · `mypy --strict` · `bandit` · `pytest --cov-fail-under=85`

---

## Workflow

This project follows a strict **Spec-Driven + BDD + TDD** methodology documented in `prompts.md`:

```
ARCHITECT → SPEC → RED → GREEN → REFACTOR → SMOKE → DEMO → COMMIT
```

- Every module has a 6-element SPEC before a line of code
- Tests use `Given / When / Then` naming (BDD language layer)
- RED phase: all tests fail (ModuleNotFoundError) — no implementation exists
- GREEN phase: minimum code to pass all tests — no extra features
- REFACTOR: `ruff` + `mypy --strict` + `bandit` must all pass before commit
- Architecture Decision Records in `ADR.md` — every significant choice is documented

---

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite+aiosqlite:///./security_auditor.db` | Database connection |
| `OPENAI_API_KEY` | `""` | Optional AI summary (gracefully skipped if absent) |
| `MAX_FILE_SIZE_MB` | `20` | Upload size limit |
