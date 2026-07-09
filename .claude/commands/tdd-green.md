# /tdd-green — Write minimum implementation to pass all failing tests

You are in the GREEN phase of TDD. Tests exist and are all failing.

Given the module name: $ARGUMENTS

1. Read the failing tests in `tests/unit/test_<module>.py` or `tests/integration/`.
2. Read the SPEC for this module in SPEC.md.
3. Write the minimum implementation to pass all tests — no extra features, no speculative code.
4. If the module produces domain objects, use Pydantic v2 BaseModel (not raw dicts).
5. If the module is an API route, wire it into `app/main.py`.
6. Run `pytest tests/ -q` — ALL previously failing tests must now pass.
7. Do not break any existing passing tests.

Acceptance: All N tests passing. No new tests added. Report final count.
