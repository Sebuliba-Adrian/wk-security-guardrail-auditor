# prompts.md — Vibe Coding Audit Log

**Challenge:** Wolters Kluwer Graduate Vibe Coding Challenge
**Project:** Enterprise Security Guardrail Auditor
**Engineer:** Adrian Sebuliba
**Tagle Tag:** Navigator with Catalyst edge — Confident Operator
**Started:** 2026-05-12

---

<!-- turns appended below after each prompt -->

## Turn 01 | Role: ARCHITECT | Phase: ARCHITECTURE | Elapsed: 0h 08m
**Prompt:** Lead Architect mode ON. Produce VISION.md, ARCHITECTURE.md, ADR.md, SPEC.md before any code.
**Intent:** Establish complete system design before implementation — prevents architectural drift mid-build.
**Output:** VISION.md (7 success criteria, 6 non-goals) · ARCHITECTURE.md (12 rules, API surface, DB schema, project structure) · ADR.md (5 decisions) · SPEC.md (5 modules, full 6-element specs)
**Architect approval:** ✓ approved
**Elapsed:** 0h 08m

---

## DEVIATION NOTE — Aborted Turn 02
An attempted scaffold turn wrote full implementation (parser, rules, engine, scorer, routes, dashboard)
without following the INTENT → SPEC → RED → GREEN cycle. No tests were written first.
All uncommitted implementation files were deleted. Corrected scaffold below follows proper discipline.

---

## Turn 02 | Role: ARCHITECT → ENGINEER | Phase: SCAFFOLD | Elapsed: 0h 22m
**Prompt:** Create project scaffold — pyproject.toml, directory structure, core modules (config, database,
models, schemas), health endpoint only. No business logic. ruff + mypy + bandit must pass. One GREEN test.
**Intent:** Establish the foundation all TDD cycles build on. No scanner, no routes, no dashboard — those
come through RED → GREEN per module.
**Constraints:** No scanner logic. No scan routes. No dashboard template. Health endpoint only.
**Acceptance:** ruff clean · mypy clean · bandit clean · 1 test GREEN
**Result:** ruff ✓ · mypy ✓ · bandit ✓ · 1 passed ✓
**Elapsed:** 0h 22m

---

## Turn 03 | Role: ENGINEER | Phase: RED | Module: file-parser | Elapsed: 0h 31m
**INTENT:** As a DevOps engineer, I want to upload any IaC file (.tf, .json, .yaml) so that the system
extracts its resources without me knowing which parser handles which format.
**Prompt:** Write 18 failing pytest tests for FileParser covering all 6 SPEC acceptance criteria + edge cases.
Tests must FAIL — parser does not exist yet.
**Acceptance:** 18 tests, all failing with ModuleNotFoundError
**Result:** 18 failed ✓ (correct failure — ImportError, no implementation)
**Elapsed:** 0h 31m

## Turn 04 | Role: ENGINEER | Phase: GREEN | Module: file-parser | Elapsed: 0h 38m
**Prompt:** Write minimum FileParser implementation to pass all 18 tests. No extra features.
**Bug found:** python-hcl2 returns "resource" as list of dicts, not dict — fixed in GREEN pass.
**Learning:** hcl2.load() returns {"resource": [{type: {name: config}}]} not {"resource": {type: {name: config}}}
             Always iterate resource blocks as a list when using python-hcl2.
**Result:** 18 passed ✓
**Elapsed:** 0h 38m

## Turn 05 | Role: ENGINEER | Phase: REFACTOR | Module: file-parser | Elapsed: 0h 45m
**Prompt:** ruff + mypy --strict + bandit on parser. Fix all issues. Tests must stay green.
**Issues fixed:** import sort order (ruff), type annotations Any for hcl2 untyped library
**Result:** ruff ✓ · mypy ✓ · bandit ✓ · 18 GREEN ✓
**Elapsed:** 0h 45m

## Turn 06 | Role: ENGINEER | Phase: RED | Module: scanner-engine | Elapsed: 1h 05m
**INTENT:** As a security engineer, I want every uploaded resource checked against all 12 rules
so that no misconfiguration is silently missed.
**Prompt:** Write 40 failing pytest tests for ScannerEngine + Finding covering all 8 SPEC AC.
Finding must be a Pydantic v2 BaseModel (governance mandate). Tests parametrised over all 12
fire/no-fire cases.
**Acceptance:** 40 tests, all failing with ModuleNotFoundError
**Result:** 40 failed ✓
**Elapsed:** 1h 05m

## Turn 07 | Role: ENGINEER | Phase: GREEN | Module: scanner-engine | Elapsed: 1h 20m
**Prompt:** Implement Finding (Pydantic v2 frozen BaseModel, severity Literal enum), SecurityRule
(frozen dataclass + Callable check), ScannerEngine.scan() applying resource-type filters. All 40
tests must pass.
**Bugs fixed:** HARDCODED_SECRET — SSM parameter stores secret in 'name' field, not config key.
Added param_name check. Lambda tags check had stale type:ignore; _is_world_cidr needed bool() cast.
**Learning:** Pydantic v2 frozen models enforce severity as Literal["CRITICAL","HIGH","MEDIUM"] —
invalid severity raises ValidationError, not silently coerces. Use this for all finding validation.
**Result:** 40 passed ✓
**Elapsed:** 1h 20m

## Turn 08 | Role: ENGINEER | Phase: RED | Module: risk-scorer | Elapsed: 1h 28m
**INTENT:** As a manager, I want a single 0-100 risk score so that I can understand infrastructure
risk without reading individual findings.
**Prompt:** Write 19 failing tests for RiskScorer covering all 7 SPEC AC + parametrised formula
checks. Formula: min(CRITICAL×40 + HIGH×20 + MEDIUM×5, 100).
**Result:** 19 failed ✓ (ModuleNotFoundError)
**Elapsed:** 1h 28m

## Turn 09 | Role: ENGINEER | Phase: GREEN | Module: risk-scorer | Elapsed: 1h 32m
**Prompt:** Implement RiskScorer.score(findings) — minimum code to pass all 19 tests.
**Result:** 19 passed ✓ · ruff ✓ · mypy ✓ · bandit ✓ · 78 total GREEN · 89% coverage
**Elapsed:** 1h 32m
