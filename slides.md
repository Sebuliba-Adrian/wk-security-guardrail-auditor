---
marp: true
theme: default
paginate: true
backgroundColor: '#ffffff'
style: |
  section {
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 22px;
    padding: 40px 60px;
    color: #1a1a2e;
  }
  section.cover {
    background: linear-gradient(135deg, #003087 0%, #0057b8 60%, #0099cc 100%);
    color: white;
    justify-content: flex-end;
    padding-bottom: 60px;
  }
  section.cover h1 {
    font-size: 48px;
    font-weight: 800;
    margin-bottom: 8px;
    color: white;
  }
  section.cover h2 {
    font-size: 22px;
    font-weight: 400;
    color: rgba(255,255,255,0.85);
    margin-bottom: 4px;
  }
  section.cover p {
    color: rgba(255,255,255,0.7);
    font-size: 16px;
  }
  section.divider {
    background: #003087;
    color: white;
    justify-content: center;
    align-items: center;
    text-align: center;
  }
  section.divider h1 {
    font-size: 48px;
    color: white;
  }
  h1 {
    font-size: 34px;
    color: #003087;
    border-bottom: 3px solid #0099cc;
    padding-bottom: 10px;
    margin-bottom: 24px;
  }
  h2 { font-size: 24px; color: #003087; }
  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 18px;
  }
  th {
    background: #003087;
    color: white;
    padding: 10px 14px;
    text-align: left;
  }
  td { padding: 8px 14px; border-bottom: 1px solid #e0e8f0; }
  tr:nth-child(even) td { background: #f0f6ff; }
  code {
    background: #f0f6ff;
    color: #003087;
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 0.9em;
  }
  pre {
    background: #1a1a2e;
    color: #a8d8ea;
    padding: 20px;
    border-radius: 8px;
    font-size: 16px;
  }
  .tag {
    display: inline-block;
    background: #0099cc;
    color: white;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 16px;
    font-weight: 600;
    margin: 4px;
  }
  .critical { color: #d32f2f; font-weight: bold; }
  .high { color: #e65100; font-weight: bold; }
  .medium { color: #f57c00; font-weight: bold; }
  .green { color: #2e7d32; font-weight: bold; }
  footer {
    color: #999;
    font-size: 14px;
  }
---

<!-- _class: cover -->
<!-- _paginate: false -->
<!-- _footer: "" -->

# Enterprise Security Guardrail Auditor

## Wolters Kluwer · Graduate Vibe Coding Challenge · Project 2
## Adrian Sebuliba · The Navigator · AI Operator · AI Ready

*github.com/Sebuliba-Adrian/wk-security-guardrail-auditor*

---

<!-- _footer: "Wolters Kluwer · Graduate Vibe Coding Challenge · Adrian Sebuliba" -->

# The Problem

> Every week, a misconfigured S3 bucket or open SSH port goes undetected in a Terraform commit. By the time it reaches production, the blast radius is a compliance incident or a breach.

<br>

| Gap | Reality |
|-----|---------|
| **Who writes IaC** | Infrastructure engineers |
| **Who audits it** | Security engineers |
| **When it's reviewed** | Too late — after the PR merges |
| **Current tooling** | Manual, inconsistent, slow |

<br>

**WK's ask:** A scanner that catches misconfigurations *before* they ship — with a visual risk score and actionable remediation.

---

# Solution in 30 Seconds

<br>

```
Upload main.tf  →  Risk Score: 100  →  "Your RDS instance is publicly
                                         accessible. Set publicly_accessible
                                         = false immediately."
```

<br>

| | Capability |
|-|------------|
| 📁 | Upload `.tf`, `.json`, `.yaml` — Terraform, CloudFormation, Pulumi |
| 📊 | **0–100 risk score** returned in under 5 seconds |
| 🛠️ | Every finding includes the **exact fix** — not just a flag |
| 🖥️ | Visual dashboard: gauge, severity charts, scan history |
| 🤖 | Optional AI executive summary (OpenAI / Gemini / DeepSeek) |

---

# Architecture

```
  Upload .tf / .json / .yaml
         │
         ▼
   ┌─────────────┐   list[dict]   ┌──────────────────┐   list[Finding]
   │  FileParser  │ ─────────────► │  ScannerEngine   │ ──────────────►
   └─────────────┘                │   (12 rules)     │
                                  └──────────────────┘
                                                             │
                                                    ┌────────▼────────┐
                                                    │   RiskScorer    │
                                                    │    0 – 100      │
                                                    └────────┬────────┘
                                                             │
                                              ┌──────────────▼──────────────┐
                                              │  AIAnalyser (optional)       │
                                              │  OpenAI · Gemini · DeepSeek  │
                                              └──────────────┬──────────────┘
                                                             │
                                                    ┌────────▼────────┐
                                                    │  FastAPI + SQLite│
                                                    │  Dashboard       │
                                                    └─────────────────┘
```

---

# 12 Security Rules

| Severity | Rule | Trigger |
|:--------:|------|---------|
| 🔴 CRITICAL | `S3_PUBLIC_ACL` | `acl = "public-read"` |
| 🔴 CRITICAL | `SSH_OPEN_TO_WORLD` | Port 22 → `0.0.0.0/0` |
| 🔴 CRITICAL | `RDP_OPEN_TO_WORLD` | Port 3389 → `0.0.0.0/0` |
| 🔴 CRITICAL | `WILDCARD_IAM_ACTION` | IAM action `"*"` |
| 🟠 HIGH | `UNENCRYPTED_EBS` | `encrypted = false` |
| 🟠 HIGH | `UNENCRYPTED_RDS` | `storage_encrypted = false` |
| 🟠 HIGH | `PUBLIC_RDS` | `publicly_accessible = true` |
| 🟠 HIGH | `HARDCODED_SECRET` | password / token / api_key in config |
| 🟡 MEDIUM | `S3_VERSIONING_DISABLED` | No versioning block |
| 🟡 MEDIUM | `CLOUDTRAIL_DISABLED` | `enable_logging = false` |
| 🟡 MEDIUM | `UNRESTRICTED_EGRESS` | All-port egress → `0.0.0.0/0` |
| 🟡 MEDIUM | `MISSING_REQUIRED_TAGS` | No `Name` or `Environment` tag |

**Formula:** `risk_score = min(CRITICAL×40 + HIGH×20 + MEDIUM×5, 100)`

---

# Vibe Coding Workflow

> *"You are the architect; the AI is the engineer."* — WK Challenge Brief

**This is exactly how it was built — every turn documented in `prompts.md`**

| Turn | Phase | Module | Gate |
|------|-------|--------|------|
| 01 | ARCHITECT | VISION + ARCHITECTURE + ADR + SPEC | Approved before any code |
| 02 | SCAFFOLD | Health endpoint only | ruff ✓ mypy ✓ bandit ✓ |
| 03–05 | RED→GREEN→REFACTOR | FileParser | hcl2 bug caught + fixed |
| 06–07 | RED→GREEN | ScannerEngine | Pydantic Finding model |
| 08–09 | RED→GREEN | RiskScorer | 5-line implementation |
| 10–11 | RED→GREEN | API Routes | Full Pydantic schema layer |
| 12 | DEMO | Dashboard | Bootstrap 5 + Chart.js |
| 13 | SMOKE | 20 edge cases | Versioning block bug caught |

**Deviation note logged** when discipline slipped — visible in `prompts.md`.

---

# Pydantic v2 as Governance

The challenge asked for compliance tooling. The code demonstrates compliance discipline.

```python
class Finding(BaseModel):
    rule_id:       str
    severity:      Literal["CRITICAL", "HIGH", "MEDIUM"]  # enum enforced
    title:         str
    description:   str
    remediation:   str                                      # never empty
    resource_name: str                                      # full provenance
    resource_type: str
    model_config = {"frozen": True}                         # immutable

class ScanResponse(BaseModel):
    risk_score: int | None = Field(None, ge=0, le=100)     # range constrained
    findings:   list[FindingResponse]                       # typed, not raw dicts
```

**A finding with severity `"BANANA"` raises `ValidationError`. It never reaches the database.**

---

# Quality Gates — Every Commit

```bash
ruff check app/ tests/          →  linting + import order
mypy app/ --strict               →  full type safety, no Any leakage  
bandit -r app/                   →  security scan
pip-audit                        →  dependency vulnerability check
pytest --cov-fail-under=85       →  132 tests · 87% coverage floor
```

**All 5 gates run automatically on every push via GitHub Actions CI**

![CI badge](https://github.com/Sebuliba-Adrian/wk-security-guardrail-auditor/actions/workflows/ci.yml/badge.svg)

The badge at the top of README.md is live. If CI is green, the code is clean.

---

# Test Pyramid

```
              ┌────────────────────────┐
              │     Smoke  (20)        │  Garbage input · all-violations ·
              │                        │  empty files · multi-upload
           ┌──┴────────────────────────┴──┐
           │      Integration  (26)       │  HTTP contract · Pydantic schemas
        ┌──┴──────────────────────────────┴──┐
        │           Unit  (86)               │  Parser · Engine · Scorer · AI
        └────────────────────────────────────┘
```

**What smoke tests caught that unit tests missed:**

| Bug | How It Was Found |
|-----|-----------------|
| hcl2 returns type names with quotes on Linux | Score was 30 instead of 100 on CI |
| Versioning block parsed as list, not dict | Clean bucket scored 5 instead of 0 |

These are **production-grade bugs** caught before submission.

---

# AI Executive Summary — Live

With any AI key set, every scan returns:

```json
{
  "risk_score": 100,
  "summary": "Overall Risk Level: Critical. The S3 bucket data_lake
               poses a critical risk due to a public ACL. SSH port 22
               is exposed to all IPs, enabling brute-force attacks.
               The RDS prod_db is unencrypted and publicly accessible.

               Recommended first action: Remove the public ACL from
               data_lake and restrict SSH access immediately.",
  "findings": [...]
}
```

**Three providers — one SDK, zero vendor lock-in:**
`OPENAI_API_KEY` → gpt-4o-mini · `GEMINI_API_KEY` → gemini-2.0-flash · `DEEPSEEK_API_KEY` → deepseek-chat

---

# What This Means for Wolters Kluwer

WK platform teams ship IaC daily. Every Terraform PR is a potential compliance incident.

**Direct CI/CD integration:**
```bash
curl -F "file=@main.tf" https://guardrail.internal/api/scan | jq '.risk_score'
# 0   → merge allowed
# 100 → block PR + notify security team
```

**Extending to WK compliance needs — zero changes outside `rules.py`:**

| New Rule | WK Use Case |
|----------|-------------|
| `MISSING_COST_CENTER_TAG` | FinOps — enforce cost attribution |
| `NON_APPROVED_REGION` | Data residency compliance |
| `CIS_BENCHMARK_*` | CIS AWS Foundations alignment |

---

# Submission Checklist

<br>

| | Deliverable | Status |
|-|-------------|--------|
| ✅ | Tagle.ai Profile | The Navigator · AI Operator · AI Ready · 73/100 |
| ✅ | Public GitHub Repository | github.com/Sebuliba-Adrian/wk-security-guardrail-auditor |
| ✅ | `prompts.md` audit log | 13 turns · deviation note · bugs caught |
| ✅ | Presentation Deck | This deck |
| ✅ | Cloud decommissioned | SQLite only — no cloud resources |
| ✅ | CI passing | ruff · mypy · bandit · pip-audit · 132 tests |
| ✅ | AI summary | OpenAI / Gemini / DeepSeek |

---

<!-- _class: divider -->
<!-- _paginate: false -->
<!-- _footer: "" -->

# Built to a higher standard.

**github.com/Sebuliba-Adrian/wk-security-guardrail-auditor**

*The Navigator · AI Operator · AI Ready*
*Adrian Sebuliba · 2026*
