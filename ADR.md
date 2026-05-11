# ADR.md — Architecture Decision Records

---

## ADR-001: SQLite as the database

**Date:** 2026-05-12
**Status:** Accepted

**Context:**
The challenge requires a free-tier database. The system is single-process,
single-user for the submission scope. Setup complexity must be minimised to
stay within the 4–6 hour build window.

**Decision:**
Use SQLite via SQLAlchemy 2.x async. Zero infrastructure. Ships inside the
Python standard library. No connection strings, no credentials, no server.

**Consequences:**
- No concurrent writes from multiple workers (acceptable: single-process)
- No horizontal scaling (acceptable: challenge scope)
- In production: replace with PostgreSQL — SQLAlchemy makes this a one-line
  connection string change
- Database file persists on disk; easy to inspect during development

---

## ADR-002: Rule engine as pure Python dataclasses

**Date:** 2026-05-12
**Status:** Accepted

**Context:**
Security rules are static logic known at build time, not user-generated data.
They do not need to be persisted, versioned in the database, or modified
at runtime by end users.

**Decision:**
Each rule is a Python dataclass with a `check(resource: dict) -> bool`
callable. Rules are instantiated at application startup and held in a
registry list. No ORM model, no database table, no admin UI.

**Consequences:**
- Rules are not user-configurable at runtime (acceptable: challenge scope)
- Adding a new rule requires a code change and redeploy (acceptable)
- Rules are fully testable in isolation with zero infrastructure
- Rule logic is type-checked by mypy and linted by ruff

---

## ADR-003: Risk scoring formula

**Date:** 2026-05-12
**Status:** Accepted

**Context:**
Scans must produce a single integer (0–100) that communicates overall risk
clearly to non-technical stakeholders. The formula must be auditable and
explainable.

**Decision:**
```
score = min(
    (CRITICAL_count × 40) + (HIGH_count × 20) + (MEDIUM_count × 5),
    100
)
```
Severity weights reflect real-world exploitability. One CRITICAL finding
alone produces a score of 40. Three CRITICAL findings saturate the scale.

**Consequences:**
- A single CRITICAL finding is never dismissed (score ≥ 40)
- Score is capped at 100 regardless of finding count
- Formula is transparent and reproducible — no ML, no hidden weights
- LOW severity findings excluded from score to keep signal clean

---

## ADR-004: File parsing strategy

**Date:** 2026-05-12
**Status:** Accepted

**Context:**
The tool must accept Terraform (`.tf`) and CloudFormation (`.json`, `.yaml`).
These are fundamentally different formats requiring different parsers.

**Decision:**
Three explicit parsers, unified output format:
- `.tf` → `python-hcl2` library
- `.json` → Python `json` stdlib
- `.yaml` / `.yml` → `PyYAML` library

All three produce the same normalised resource list:
`[{"type": str, "name": str, "config": dict}]`

**Consequences:**
- Parser selection is explicit, not heuristic
- Unsupported extensions return 415 immediately (no silent failures)
- Malformed files return `parse_error` status with empty findings (never crash)
- New format support requires adding one parser function and one file extension

---

## ADR-005: Optional AI analysis layer

**Date:** 2026-05-12
**Status:** Accepted

**Context:**
AI-powered finding explanation adds value but requires an external API key
that may not be present in all deployment environments.

**Decision:**
The AI analysis layer is opt-in. If `OPENAI_API_KEY` is absent or the API
call fails, the scan completes normally with rule-based findings only.
No error is surfaced to the user.

**Consequences:**
- System works fully without any API key (zero-dependency baseline)
- AI layer enriches results when available but is never on the critical path
- API failures are logged at DEBUG level and silently skipped
