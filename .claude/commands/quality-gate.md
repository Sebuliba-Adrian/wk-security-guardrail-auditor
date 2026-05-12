# /quality-gate — Run all quality gates and report status

Run the full quality gate suite in order. Stop and report on first failure.

```
ruff check app/ tests/
mypy app/ --strict
bandit -r app/ -q
pytest tests/ --cov=app --cov-fail-under=85 -q
```

Report format:
- ruff: PASS / FAIL (with issue count)
- mypy: PASS / FAIL (with error list)
- bandit: PASS / FAIL (with severity breakdown)
- pytest: PASS / FAIL (N passed, M failed, coverage %)

If any gate fails, show the exact errors and fix them before declaring done.
A module is only complete when all 4 gates show PASS.
