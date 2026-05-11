# ARCHITECTURE.md — Enterprise Security Guardrail Auditor

## System Overview

```
User (browser)
    │
    ▼
FastAPI (Python 3.12)
    ├── POST /api/scan         ← file upload, enqueue scan
    ├── GET  /api/scan/{id}    ← retrieve results
    ├── GET  /api/scans        ← scan history
    ├── GET  /api/health       ← health check
    └── GET  /dashboard        ← Jinja2 HTML + Chart.js
    │
    ├── BackgroundTask
    │       ├── FileParser     ← python-hcl2 / PyYAML / json
    │       ├── ScannerEngine  ← 12 rules → findings list
    │       ├── RiskScorer     ← weighted sum → 0-100 score
    │       └── AIAnalyser     ← optional GPT layer (graceful skip)
    │
    └── SQLite (SQLAlchemy async)
            ├── scans
            └── findings
```

## Components

### FileParser
Accepts raw bytes + filename. Routes to:
- `python-hcl2` for `.tf` (Terraform HCL2)
- `json` stdlib for `.json` (CloudFormation JSON)
- `PyYAML` for `.yaml` / `.yml` (CloudFormation YAML)

Normalises all formats to a unified list of resource dicts:
```python
[{"type": "aws_s3_bucket", "name": "my_bucket", "config": {...}}, ...]
```
Returns `(resources, parse_error)`. Never raises.

### ScannerEngine
Holds a registry of 12 `SecurityRule` dataclasses. Each rule:
```python
@dataclass
class SecurityRule:
    id: str
    severity: Literal["CRITICAL", "HIGH", "MEDIUM"]
    title: str
    description: str
    remediation: str
    check: Callable[[dict], bool]
```

Iterates all resources against all rules. Returns list of `Finding` objects.

### RiskScorer
```
score = min(
    (CRITICAL_count × 40) + (HIGH_count × 20) + (MEDIUM_count × 5),
    100
)
```
Returns integer 0–100. 0 = clean. 100 = maximum risk.

### AIAnalyser (optional)
If `OPENAI_API_KEY` is set: calls `gpt-4o-mini` with findings list.
Returns plain-English executive summary + top-3 prioritised findings.
Gracefully skipped if key absent or API unavailable.

### Dashboard
Single Jinja2 HTML template served at `GET /dashboard`.
Chart.js (bundled inline — no external CDN).
- Risk Score gauge: doughnut, red ≥ 70 / amber 40–69 / green < 40
- Findings by severity: colour-coded bar chart
- Top rules triggered: horizontal bar chart
- Recent scans: sortable table, last 10, click to drill down

## API Surface

| Method | Path | Description | Status codes |
|--------|------|-------------|--------------|
| POST | /api/scan | Upload IaC file, enqueue scan | 202, 415, 422, 413 |
| GET | /api/scan/{scan_id} | Get scan results | 200, 404 |
| GET | /api/scans | List scan history (last 50) | 200 |
| GET | /api/health | Health check | 200 |
| GET | /dashboard | HTML dashboard | 200 |
| GET | /openapi.json | Auto-generated OpenAPI schema | 200 |

## Database Schema (SQLite)

```sql
CREATE TABLE scans (
    id          TEXT PRIMARY KEY,        -- UUID
    filename    TEXT NOT NULL,
    status      TEXT NOT NULL,           -- queued | scanning | complete | parse_error
    risk_score  INTEGER,                 -- 0-100, NULL until complete
    summary     TEXT,                    -- AI summary or NULL
    file_size   INTEGER,
    scanned_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE findings (
    id              TEXT PRIMARY KEY,    -- UUID
    scan_id         TEXT NOT NULL REFERENCES scans(id),
    rule_id         TEXT NOT NULL,
    severity        TEXT NOT NULL,       -- CRITICAL | HIGH | MEDIUM
    title           TEXT NOT NULL,
    description     TEXT NOT NULL,
    remediation     TEXT NOT NULL,
    resource_name   TEXT NOT NULL,
    resource_type   TEXT NOT NULL
);

CREATE INDEX idx_findings_scan_id ON findings(scan_id);
CREATE INDEX idx_scans_scanned_at ON scans(scanned_at DESC);
```

## Security Rules (12 total)

| Rule ID | Severity | Trigger |
|---------|----------|---------|
| S3_PUBLIC_ACL | CRITICAL | aws_s3_bucket acl = "public-read" / "public-read-write" |
| SSH_OPEN_TO_WORLD | CRITICAL | port 22, cidr 0.0.0.0/0 ingress |
| RDP_OPEN_TO_WORLD | CRITICAL | port 3389, cidr 0.0.0.0/0 ingress |
| WILDCARD_IAM_ACTION | CRITICAL | IAM policy action = "*" |
| UNENCRYPTED_EBS | HIGH | aws_ebs_volume encrypted = false |
| UNENCRYPTED_RDS | HIGH | aws_db_instance storage_encrypted = false |
| PUBLIC_RDS | HIGH | aws_db_instance publicly_accessible = true |
| HARDCODED_SECRET | HIGH | value matches secret pattern (key/password/token) |
| S3_VERSIONING_DISABLED | MEDIUM | aws_s3_bucket versioning block absent or disabled |
| CLOUDTRAIL_DISABLED | MEDIUM | aws_cloudtrail enable_logging = false |
| UNRESTRICTED_EGRESS | MEDIUM | all-port egress rule to 0.0.0.0/0 |
| MISSING_REQUIRED_TAGS | MEDIUM | resource missing Name or Environment tag |

## Project Structure

```
wk-security-guardrail-auditor/
├── app/
│   ├── main.py               ← FastAPI app, lifespan, CORS
│   ├── core/
│   │   ├── config.py         ← Pydantic Settings
│   │   └── database.py       ← SQLAlchemy async engine + session
│   ├── models/
│   │   └── scan.py           ← SQLAlchemy ORM models
│   ├── schemas/
│   │   └── scan.py           ← Pydantic request/response
│   ├── api/
│   │   └── routes/
│   │       ├── scan.py       ← POST /api/scan, GET /api/scan/{id}
│   │       ├── history.py    ← GET /api/scans
│   │       └── health.py     ← GET /api/health
│   ├── scanner/
│   │   ├── parser.py         ← FileParser
│   │   ├── rules.py          ← 12 SecurityRule dataclasses
│   │   ├── engine.py         ← ScannerEngine
│   │   ├── scorer.py         ← RiskScorer
│   │   └── ai_analyser.py    ← optional GPT layer
│   └── dashboard/
│       └── templates/
│           └── dashboard.html
├── tests/
│   ├── unit/
│   ├── integration/
│   └── smoke/
├── pyproject.toml
├── prompts.md
├── VISION.md
├── ARCHITECTURE.md
├── ADR.md
└── SPEC.md
```

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Runtime | Python 3.12 |
| API | FastAPI + Uvicorn |
| ORM | SQLAlchemy 2.x async |
| Database | SQLite |
| Validation | Pydantic v2 |
| IaC Parsing | python-hcl2, PyYAML |
| Dashboard | Jinja2 + Chart.js (inline) |
| Testing | pytest, pytest-asyncio, schemathesis |
| Quality | ruff, mypy --strict, bandit, pip-audit |
| CI | GitHub Actions |
| Optional AI | OpenAI gpt-4o-mini |
