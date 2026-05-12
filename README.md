# Security Guardrail Auditor

[![CI](https://github.com/Sebuliba-Adrian/wk-security-guardrail-auditor/actions/workflows/ci.yml/badge.svg)](https://github.com/Sebuliba-Adrian/wk-security-guardrail-auditor/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.12-blue?logo=python&logoColor=white)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/tests-120%20passed-brightgreen)](https://github.com/Sebuliba-Adrian/wk-security-guardrail-auditor/actions)
[![Coverage](https://img.shields.io/badge/coverage-87%25-brightgreen)](https://github.com/Sebuliba-Adrian/wk-security-guardrail-auditor/actions)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![mypy](https://img.shields.io/badge/mypy-strict-blue)](https://mypy.readthedocs.io/)
[![bandit](https://img.shields.io/badge/security-bandit-yellow)](https://bandit.readthedocs.io/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

> Upload a Terraform, CloudFormation, or Pulumi state file. Get a deterministic 0–100 risk score, colour-coded severity breakdown, and specific remediation for every misconfiguration — in under 5 seconds.

**Wolters Kluwer Graduate Vibe Coding Challenge — Project 2**
Built with: Spec-Driven Design · BDD · TDD (RED → GREEN → REFACTOR) · Pydantic v2 governance

---

## Table of Contents

- [Quick Start](#quick-start)
- [Features](#features)
- [Security Rules](#security-rules)
- [Dashboard](#dashboard)
- [API Reference](#api-reference)
- [Architecture](#architecture)
- [Test Suite](#test-suite)
- [Development Workflow](#development-workflow)
- [Configuration](#configuration)
- [Project Structure](#project-structure)

---

## Quick Start

**Requirements:** Python 3.12+

```bash
# 1. Clone and install
git clone https://github.com/Sebuliba-Adrian/wk-security-guardrail-auditor.git
cd wk-security-guardrail-auditor
pip install -e ".[dev]"

# 2. Start the server
uvicorn app.main:app --reload

# 3. Open the dashboard
open http://localhost:8000/dashboard

# 4. Or use the API directly
curl -F "file=@your-infra.tf" http://localhost:8000/api/scan
```

**Try it immediately** — paste this into the browser address bar after starting the server:
```
http://localhost:8000/docs
```
The interactive Swagger UI lets you upload files and inspect responses without writing any code.

---

## Features

| | Feature | Detail |
|-|---------|--------|
| 🔍 | **12 Security Rules** | CRITICAL × 4, HIGH × 4, MEDIUM × 4 — covering IAM, networking, encryption, and governance |
| 📊 | **Risk Score 0–100** | `min(CRITICAL×40 + HIGH×20 + MEDIUM×5, 100)` — deterministic, auditable formula |
| 🛠️ | **Actionable Remediation** | Every finding includes a specific fix, not just a warning |
| 🔒 | **Pydantic v2 Governance** | All API boundaries validated — severity is `Literal`, score is range-constrained |
| 📁 | **Multi-format Support** | Terraform (`.tf`), CloudFormation JSON/YAML (`.json`/`.yaml`/`.yml`), Pulumi state (`.json`) |
| 🌐 | **Interactive Dashboard** | Zero-CDN Jinja dashboard — risk gauge, severity breakdown, top rules, recent scans |
| 📖 | **OpenAPI / Swagger** | Full API spec auto-generated from Pydantic schemas at `/docs` |
| 🧪 | **139 Tests** | Unit + integration + smoke, 87% coverage, all gates enforced in CI |
| 🤖 | **AI Executive Summary** | Per-scan plain-English summary via OpenAI, Gemini, or DeepSeek — graceful skip if no key set |
| 💾 | **Zero Infrastructure** | SQLite by default — no database server needed |

---

## Security Rules

| Rule ID | Severity | Trigger |
|---------|:--------:|---------|
| `S3_PUBLIC_ACL` | 🔴 CRITICAL | `acl = "public-read"` or `"public-read-write"` |
| `SSH_OPEN_TO_WORLD` | 🔴 CRITICAL | Port 22 ingress open to `0.0.0.0/0` |
| `RDP_OPEN_TO_WORLD` | 🔴 CRITICAL | Port 3389 ingress open to `0.0.0.0/0` |
| `WILDCARD_IAM_ACTION` | 🔴 CRITICAL | IAM policy action `"*"` |
| `UNENCRYPTED_EBS` | 🟠 HIGH | `encrypted = false` on EBS volume |
| `UNENCRYPTED_RDS` | 🟠 HIGH | `storage_encrypted = false` on RDS instance |
| `PUBLIC_RDS` | 🟠 HIGH | `publicly_accessible = true` on RDS instance |
| `HARDCODED_SECRET` | 🟠 HIGH | Config key or SSM parameter name matches `password\|secret\|token\|api_key` |
| `S3_VERSIONING_DISABLED` | 🟡 MEDIUM | Versioning block absent or `enabled = false` |
| `CLOUDTRAIL_DISABLED` | 🟡 MEDIUM | `enable_logging = false` on CloudTrail |
| `UNRESTRICTED_EGRESS` | 🟡 MEDIUM | All-port egress rule to `0.0.0.0/0` |
| `MISSING_REQUIRED_TAGS` | 🟡 MEDIUM | Resource missing `Name` or `Environment` tag |

**Risk score bands:** 🟢 0–39 Low · 🟡 40–69 Elevated · 🔴 70–100 Critical

---

## Dashboard

Navigate to `http://localhost:8000/dashboard` after starting the server.

- **Risk Score Gauge** — doughnut chart, colour-coded green/amber/red
- **Findings by Severity** — bar chart with CRITICAL/HIGH/MEDIUM breakdown
- **Top Triggered Rules** — horizontal bar chart of most-fired rules
- **Recent Scans Table** — last 10 scans with score, finding count, and JSON drill-down link
- **Inline Upload Form** — drag-and-drop `.tf`/`.json`/`.yaml`, results appear on page reload

---

## API Reference

Full interactive docs: `http://localhost:8000/docs`

### `POST /api/scan`
Upload an IaC file for scanning.

```bash
curl -X POST http://localhost:8000/api/scan \
  -F "file=@main.tf"
```

**Response 202:**
```json
{
  "scan_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "status": "complete"
}
```

**Error codes:** `415` unsupported file type · `422` missing file · `413` file > 20 MB

**Supported formats:**

| Format | Extension | Detection |
|--------|-----------|-----------|
| Terraform HCL2 | `.tf` | By extension |
| CloudFormation JSON | `.json` | Content-sniffed — `Resources` key |
| CloudFormation YAML | `.yaml` / `.yml` | By extension |
| **Pulumi state** | `.json` | Content-sniffed — `deployment.resources` key |

> Pulumi state files are produced by `pulumi stack export > stack.json`. The parser normalises Pulumi resource types (`aws:s3/bucket:Bucket`) to their Terraform equivalents (`aws_s3_bucket`) so all 12 security rules apply without modification.

---

### `GET /api/scan/{scan_id}`
Retrieve full scan results including all findings.

```bash
curl http://localhost:8000/api/scan/3fa85f64-5717-4562-b3fc-2c963f66afa6
```

**Response 200:**
```json
{
  "scan_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "filename": "main.tf",
  "status": "complete",
  "risk_score": 60,
  "scanned_at": "2026-05-12T10:30:00Z",
  "summary": "Overall Risk Level: Critical. The S3 bucket my_bucket has a public ACL allowing unauthorised internet access. Recommended first action: Set acl to 'private' and restrict access via bucket policies immediately.",
  "findings": [
    {
      "rule_id": "S3_PUBLIC_ACL",
      "severity": "CRITICAL",
      "title": "S3 bucket has public ACL",
      "description": "The bucket ACL grants public read access to the internet.",
      "remediation": "Set the bucket acl to 'private' and use bucket policies for controlled access.",
      "resource_name": "my_bucket",
      "resource_type": "aws_s3_bucket"
    }
  ]
}
```

---

### `GET /api/scans`
List scan history (last 50).

```bash
curl http://localhost:8000/api/scans
```

---

### `GET /api/health`
Health check.

```bash
curl http://localhost:8000/api/health
# {"status": "ok"}
```

---

## Architecture

```
┌─────────────┐     bytes      ┌────────────┐   list[dict]  ┌───────────────┐
│  POST /scan │ ─────────────► │ FileParser │ ────────────► │ ScannerEngine │
└─────────────┘                └────────────┘               └───────┬───────┘
                                                                     │ list[Finding]
                                                              ┌──────▼──────┐
                                                              │  RiskScorer │
                                                              └──────┬──────┘
                                                                     │ int (0-100)
                                                              ┌──────▼──────┐
                                                              │   SQLite    │
                                                              │  (async)    │
                                                              └─────────────┘
```

**Key design decisions — see `ADR.md` for full rationale:**

| Decision | Choice | Reason |
|----------|--------|--------|
| Database | SQLite + SQLAlchemy async | Zero infrastructure; one env-var swap to Postgres |
| Rule engine | Pure `Callable[[dict], bool]` predicates | Adding a rule = one entry, zero other files change |
| Domain objects | Pydantic v2 `BaseModel` (frozen) | Invalid severity raises `ValidationError`, never silently corrupts |
| Risk formula | `min(C×40 + H×20 + M×5, 100)` | Deterministic, auditable, CRITICAL-weighted |
| AI layer | Optional (graceful skip) | Works without `OPENAI_API_KEY`; never blocks the scan |
| Frontend | Jinja2 + inline CSS/JS | No build step; zero external assets; API-first dashboard |

---

## Test Suite

```
tests/
├── unit/
│   ├── test_parser.py     # 18 tests — FileParser (6 SPEC AC + edge cases)
│   ├── test_scanner.py    # 40 tests — ScannerEngine (12 fire + 12 no-fire parametrised)
│   └── test_scorer.py     # 19 tests — RiskScorer (7 SPEC AC + formula checks)
├── integration/
│   ├── test_api.py        # 19 tests — full HTTP contract + Pydantic schema assertions
│   └── test_dashboard.py  #  7 tests — dashboard render, empty state, post-scan
└── smoke/
    └── test_smoke.py      # 20 tests — lifecycle, garbage input, all-violations, multi-upload
```

**139 tests · 87% coverage · all Given/When/Then BDD naming**

Run the full suite:
```bash
pytest tests/ -v
```

Run a specific layer:
```bash
pytest tests/unit/ -v        # fast, no DB
pytest tests/integration/ -v # HTTP + SQLite
pytest tests/smoke/ -v       # end-to-end edge cases
```

---

## Development Workflow

This project uses **Spec-Driven Design + BDD naming + TDD execution**:

```
SPEC → RED → GREEN → REFACTOR → SMOKE → COMMIT
```

Every module has a 6-element spec in `SPEC.md` written **before** any code. Tests use
`Given / When / Then` naming and must fail before the implementation exists.

The full session audit trail — every decision, bug found, and learning — is in `prompts.md`.

### Adding a new security rule

```bash
# 1. Add fire/no-fire cases to test_scanner.py FIRE_CASES / NO_FIRE_CASES
# 2. Confirm they fail:
pytest tests/unit/test_scanner.py -q  # 2 new cases fail

# 3. Add SecurityRule(...) to app/scanner/rules.py
# 4. Run quality gate:
ruff check app/ tests/ && mypy app/ && bandit -r app/ -q && pytest tests/ -q

# 5. Update ARCHITECTURE.md rules table
```

### Quality gate (all 4 must pass before every commit)

```bash
ruff check app/ tests/     # linting
mypy app/                   # strict types
bandit -r app/ -q           # security
pytest tests/ -q            # tests + 85% coverage floor
```

---

## Configuration

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `DATABASE_URL` | `sqlite+aiosqlite:///./security_auditor.db` | Database — swap to `postgresql+asyncpg://...` for production |
| `OPENAI_API_KEY` | `""` | Optional — enables AI summary via gpt-4o-mini |
| `GEMINI_API_KEY` | `""` | Optional — enables AI summary via gemini-2.0-flash-lite |
| `DEEPSEEK_API_KEY` | `""` | Optional — enables AI summary via deepseek-chat |
| `MAX_FILE_SIZE_MB` | `20` | Upload size limit in megabytes |

> **AI Summary:** Set any one key and every scan response includes a `summary` field with a plain-English executive summary, top issues identified by resource name, and a recommended first action. Provider priority: OpenAI → Gemini → DeepSeek. Gracefully returns `null` if no key is set or the API call fails — the scan always completes.

---

## AI Executive Summary

When an AI provider key is configured, the scan response includes:

```json
{
  "risk_score": 100,
  "summary": "Overall Risk Level: Critical. The infrastructure has 3 severe
               misconfigurations: the S3 bucket data_lake has a public ACL
               enabling unauthorised internet access, SSH port 22 is open to
               0.0.0.0/0 enabling brute-force attacks, and the RDS instance
               prod_db is unencrypted and publicly accessible. Recommended
               first action: Remove the public ACL from data_lake and restrict
               SSH ingress to known CIDR ranges immediately."
}
```

Start the server with any of the following:

```bash
# OpenAI
OPENAI_API_KEY=sk-...          uvicorn app.main:app --reload

# Gemini
GEMINI_API_KEY=AIza...         uvicorn app.main:app --reload

# DeepSeek
DEEPSEEK_API_KEY=sk-...        uvicorn app.main:app --reload
```

---

## Project Structure

```
wk-security-guardrail-auditor/
├── app/
│   ├── main.py                      # FastAPI app, lifespan, CORS, router registration
│   ├── core/
│   │   ├── config.py                # Pydantic Settings
│   │   └── database.py              # SQLAlchemy async engine + session
│   ├── models/scan.py               # SQLAlchemy ORM models (Scan, Finding)
│   ├── schemas/scan.py              # Pydantic v2 API schemas (governance contract)
│   ├── api/routes/
│   │   ├── health.py                # GET /api/health
│   │   ├── scan.py                  # POST /api/scan · GET /api/scan/{id}
│   │   ├── history.py               # GET /api/scans
│   │   └── dashboard.py             # GET /dashboard
│   ├── scanner/
│   │   ├── parser.py                # FileParser — .tf / .json / .yaml → list[dict]
│   │   ├── rules.py                 # 12 SecurityRule definitions
│   │   ├── engine.py                # ScannerEngine + Finding Pydantic model
│   │   └── scorer.py                # RiskScorer — deterministic 0-100 formula
│   └── dashboard/templates/
│       └── dashboard.html           # Jinja2 template — zero-CDN dashboard
├── tests/
│   ├── conftest.py                  # Async fixtures: in-memory DB, test client
│   ├── unit/                        # 77 unit tests
│   ├── integration/                 # 26 integration tests
│   └── smoke/                       # 20 smoke tests
├── .github/workflows/ci.yml         # CI: ruff · mypy · bandit · pip-audit · pytest
├── CLAUDE.md                        # Session brief — auto-loaded by Claude Code
├── VISION.md                        # 7 success criteria · 6 non-goals
├── ARCHITECTURE.md                  # Full system design
├── ADR.md                           # Architecture Decision Records
├── SPEC.md                          # 5 module specs
├── prompts.md                       # Full vibe coding audit log (13 turns)
└── pyproject.toml                   # Build config, ruff, mypy, bandit, pytest settings
```

## Submission Compliance

- Tagle summary included in [TAGLE.md](C:/projects/wk-security-guardrail-auditor/TAGLE.md) and the source profile PDF is present in the repo.
- Public GitHub repository reference is documented in this README.
- `prompts.md` is maintained as the workflow audit log.
- Presentation artifacts are included as `PRESENTATION.md`, `slides.md`, and `presentation.pdf`.
- Cloud resource decommission confirmation: this solution runs locally on SQLite and does not require a live cloud account; no cloud resources remain allocated for the submission.
