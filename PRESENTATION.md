# Enterprise Security Guardrail Auditor
## Wolters Kluwer Graduate Vibe Coding Challenge — Project 2
### Adrian Sebuliba · The Navigator · AI Operator · AI Ready · Composite Readiness 73/100 · 2026-05-12

---

## Slide 1 — The Problem

> Every week, a misconfigured S3 bucket, an open SSH port, or an unencrypted RDS instance
> goes undetected in a Terraform commit. By the time it reaches production, the blast radius
> is a compliance incident, a breach, or a $200K fine.

**The gap:** Infrastructure engineers write IaC. Security engineers audit it. The handoff
is manual, slow, and happens too late.

**The ask from WK:** Build a scanner that catches misconfigurations before they ship —
with a visual risk score and actionable remediation, not just a warning.

---

## Slide 2 — The Solution in 30 Seconds

```
Upload main.tf  →  Risk Score: 100  →  "Your RDS instance is publicly accessible.
                                         Set publicly_accessible = false."
```

- Upload any `.tf`, `.json`, or `.yaml` IaC file
- Get a **0–100 risk score** in under 5 seconds
- Every finding includes the **exact fix** — not just the flag
- Visual dashboard with gauge, charts, and scan history
- Optional **AI executive summary** (OpenAI / Gemini / DeepSeek)

---

## Slide 3 — Architecture

```
┌──────────────┐   bytes   ┌────────────┐  list[dict]  ┌────────────────┐
│  Upload .tf  │ ────────► │ FileParser │ ───────────► │ ScannerEngine  │
└──────────────┘           └────────────┘              │  (12 rules)    │
                                                        └───────┬────────┘
                                                                │ list[Finding]
                                                         ┌──────▼──────┐
                                                         │  RiskScorer │  0-100
                                                         └──────┬──────┘
                                                                │
                                                         ┌──────▼──────┐
                                                         │  AIAnalyser │  summary
                                                         └──────┬──────┘
                                                                │
                                                         ┌──────▼──────┐
                                                         │   SQLite    │
                                                         │  FastAPI    │
                                                         │  Dashboard  │
                                                         └─────────────┘
```

**Three architectural principles:**
1. **Separation of concerns** — each module has one job, one interface
2. **Pydantic v2 everywhere** — invalid data raises `ValidationError` at the boundary, never corrupts silently
3. **Rules are additive** — adding a new security rule is one entry in one file

---

## Slide 4 — The 12 Security Rules

| Severity | Rules |
|:--------:|-------|
| 🔴 CRITICAL | S3 Public ACL · SSH Open to World · RDP Open to World · Wildcard IAM Action |
| 🟠 HIGH | Unencrypted EBS · Unencrypted RDS · Public RDS · Hardcoded Secret |
| 🟡 MEDIUM | S3 Versioning Disabled · CloudTrail Disabled · Unrestricted Egress · Missing Required Tags |

**Risk formula:** `min(CRITICAL×40 + HIGH×20 + MEDIUM×5, 100)`

Deterministic. Auditable. CRITICAL-weighted to match real-world blast radius.

---

## Slide 5 — The Vibe Coding Workflow

> *"You are the architect; the AI is the engineer."* — WK Challenge Brief

This is exactly how this project was built.

```
SPEC → RED → GREEN → REFACTOR → SMOKE → COMMIT  (×5 modules)
```

**What that looks like in practice:**

| Turn | Role | Action | Gate |
|------|------|--------|------|
| 01 | Architect | VISION + ARCHITECTURE + ADR + SPEC | Approved before any code |
| 02 | Scaffold | pyproject.toml + health endpoint only | ruff ✓ mypy ✓ bandit ✓ |
| 03–05 | FileParser | RED (18 fail) → GREEN (18 pass) → REFACTOR | hcl2 list-vs-dict bug caught |
| 06–07 | ScannerEngine | RED (40 fail) → GREEN (40 pass) | Pydantic Finding model |
| 08–09 | RiskScorer | RED (19 fail) → GREEN (19 pass) | 5-line implementation |
| 10–11 | API Routes | RED (17 fail) → GREEN (19 pass) | Full Pydantic schema layer |
| 12 | Dashboard | DEMO | Bootstrap 5 + Chart.js |
| 13 | Smoke Tests | 20 edge cases | Caught versioning block bug |

**Every turn documented in `prompts.md` — including the deviation note when discipline slipped.**

---

## Slide 6 — Pydantic v2 as Governance

The challenge asked for compliance tooling. The code itself demonstrates compliance discipline.

```python
class Finding(BaseModel):
    rule_id: str
    severity: Literal["CRITICAL", "HIGH", "MEDIUM"]  # enum-validated
    remediation: str                                   # required, never empty
    resource_name: str                                 # full provenance
    resource_type: str
    model_config = {"frozen": True}                    # immutable after creation

class ScanResponse(BaseModel):
    risk_score: int | None = Field(None, ge=0, le=100) # range-constrained
    findings: list[FindingResponse]                    # typed list, no raw dicts
```

**A finding with severity `"BANANA"` raises `ValidationError`. It never reaches the database.**

This is what governance looks like in code — not a comment, not a convention, a hard constraint.

---

## Slide 7 — Quality Gates (Run on Every Commit)

```
ruff check app/ tests/     →  import order, style, unused code
mypy app/ --strict         →  full type safety, no Any leakage
bandit -r app/             →  security scan (no eval, no shell injection)
pip-audit                  →  dependency vulnerability check
pytest --cov-fail-under=85 →  132 tests, 87% coverage floor enforced
```

**All 5 gates run automatically on every push via GitHub Actions CI.**

The badge at the top of the README is live. If CI is green, the code is clean.

---

## Slide 8 — Test Pyramid

```
                    ┌─────────────┐
                    │  Smoke (20) │  End-to-end: empty files, garbage input,
                    │             │  all-violations, multiple uploads
                 ┌──┴─────────────┴──┐
                 │ Integration (26)  │  HTTP contract + Pydantic schema assertions
              ┌──┴───────────────────┴──┐
              │     Unit (86)           │  Parser · Engine · Scorer · AI Analyser
              └─────────────────────────┘
```

**What the smoke tests caught that unit tests missed:**
- `hcl2` on Linux returns type names with literal quote characters — all 12 type-filtered rules silently failed on CI
- `versioning { enabled = true }` (HCL block syntax) parsed as a `list`, not `dict` — clean buckets scored 5 instead of 0

These are production-grade bugs. The smoke suite caught them before submission.

---

## Slide 9 — AI Executive Summary (Live Demo)

With `DEEPSEEK_API_KEY` set, every scan response includes:

```json
{
  "risk_score": 100,
  "summary": "Overall Risk Level: Critical. The S3 bucket data_lake poses a
               critical risk due to a public ACL. SSH port 22 is exposed to all
               IPs, enabling brute-force attacks. The RDS prod_db is unencrypted
               and publicly accessible, risking compliance violations.
               Recommended first action: Remove the public ACL from data_lake
               and restrict SSH access to a specific IP range immediately.",
  "findings": [...]
}
```

**Provider priority:** OpenAI → Gemini → DeepSeek — all via the OpenAI SDK, zero vendor lock-in.

---

## Slide 10 — Extensibility Demonstration

**Adding a new IaC format (Pulumi):** One parser method, one type-normaliser, zero other files changed.

```python
# Before: .json always routed to CloudFormation parser
# After:  content-sniffed — Pulumi state detected by deployment.resources key

def _dispatch_json(content):
    if "deployment" in data and "resources" in data["deployment"]:
        return FileParser._pulumi_state(data)   # new
    if "Resources" in data:
        return FileParser._cfn_resources(data)  # unchanged
    return [], False                             # unknown JSON — no error
```

**Adding a new security rule:** One `SecurityRule(...)` entry + two test cases. The scanner, API, dashboard, and CI all pick it up automatically.

---

## Slide 11 — What This Means for Wolters Kluwer

WK's platform teams ship IaC daily. Every Terraform PR is a potential compliance incident.

This tool integrates directly into that workflow:

```bash
# In a CI pipeline:
curl -F "file=@main.tf" https://guardrail.internal/api/scan | jq '.risk_score'
# Returns: 0  ← merge allowed
# Returns: 100 ← block + notify security team
```

**Extensible to WK's compliance needs:**
- Add a `MISSING_COST_CENTER_TAG` rule → FinOps enforcement
- Add a `NON_APPROVED_REGION` rule → Data residency compliance
- Add a `CIS_BENCHMARK_*` rule set → CIS AWS Foundations alignment

Zero code changes outside `rules.py`.

---

## Slide 12 — Submission Checklist

| Item | Status |
|------|--------|
| ✅ Tagle.ai Tag | The Navigator · AI Operator · AI Ready — `TAGLE.md` + `tagle-profile.pdf` |
| ✅ Public GitHub Repo | github.com/Sebuliba-Adrian/wk-security-guardrail-auditor |
| ✅ `prompts.md` audit log | 13 turns, deviation note, learnings per turn |
| ✅ Presentation Deck | This document |
| ✅ Cloud decommissioned | SQLite only — no cloud resources provisioned |
| ✅ CI passing | GitHub Actions: ruff · mypy · bandit · pip-audit · pytest |
| ✅ 132 tests | Unit + Integration + Smoke · 87% coverage |
| ✅ AI summary | OpenAI / Gemini / DeepSeek — graceful skip if no key |

---

## Slide 13 — One-Line Summary

> *Built a production-grade security scanner — not because the challenge required it,
> but because that is the standard.*

**github.com/Sebuliba-Adrian/wk-security-guardrail-auditor**
