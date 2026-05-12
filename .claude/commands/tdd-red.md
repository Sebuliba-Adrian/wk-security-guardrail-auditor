# /tdd-red — Write failing tests for a new module

You are in the RED phase of TDD. No implementation exists yet.

Given the module name: $ARGUMENTS

1. Read SPEC.md and find the spec for this module (INTENT, OUTCOMES, ACCEPTANCE CRITERIA).
2. Write pytest tests in `tests/unit/test_<module>.py` (or `tests/integration/` if it's an API module).
3. Every test must use Given/When/Then naming: `test_given_<context>_when_<action>_then_<outcome>`.
4. Cover every SPEC acceptance criterion with at least one test.
5. Add parametrised tests for any rule-based logic (fire / no-fire pairs).
6. Do NOT write any implementation — the tests must fail with `ModuleNotFoundError` or `ImportError`.
7. Run `pytest tests/ -q` and confirm all new tests fail.

Acceptance: N tests, all failing with ImportError. Report the count.
