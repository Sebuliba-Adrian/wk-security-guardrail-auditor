# /add-rule — Add a new security rule following the TDD cycle

Add a new security rule to the scanner engine.

Given the rule specification: $ARGUMENTS
Format expected: RULE_ID | SEVERITY | TRIGGER_DESCRIPTION

Steps:
1. Add a fire test and a no-fire test to `tests/unit/test_scanner.py` FIRE_CASES and NO_FIRE_CASES.
2. Run `pytest tests/unit/test_scanner.py -q` — confirm the 2 new parametrised cases fail.
3. Add a `SecurityRule(...)` entry to `app/scanner/rules.py` with:
   - A pure `check: Callable[[dict], bool]` lambda or named function
   - Non-empty `title`, `description`, and `remediation` fields
   - Correct `severity`: CRITICAL / HIGH / MEDIUM
4. If the rule only applies to specific resource types, add it to `_RESOURCE_TYPE_FILTER` in `engine.py`.
5. Run `pytest tests/ -q` — all tests must pass.
6. Run `/quality-gate` — ruff + mypy + bandit must all pass.
7. Update ARCHITECTURE.md rules table with the new entry.

Do not modify any other files. One rule = one `SecurityRule` entry + two test cases.
