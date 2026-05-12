"""
Unit tests — RiskScorer
Phase: RED — all tests must FAIL before implementation exists.

INTENT: As a manager, I want a single 0-100 risk score so that I can understand
infrastructure risk without reading individual findings.

Spec: SPEC.md § risk-scorer
Formula: min(CRITICAL×40 + HIGH×20 + MEDIUM×5, 100)
"""

from __future__ import annotations

import pytest

from app.scanner.engine import Finding


def _finding(severity: str, n: int = 1) -> list[Finding]:
    return [
        Finding(
            rule_id=f"TEST_{severity}_{i}",
            severity=severity,  # type: ignore[arg-type]
            title="t",
            description="d",
            remediation="r",
            resource_name="res",
            resource_type="aws_test",
        )
        for i in range(n)
    ]


# ---------------------------------------------------------------------------
# AC-01 · 0 findings → score 0
# ---------------------------------------------------------------------------


def test_given_no_findings_when_scored_then_zero() -> None:
    from app.scanner.scorer import RiskScorer

    assert RiskScorer.score([]) == 0


# ---------------------------------------------------------------------------
# AC-02 · 1 CRITICAL → 40
# ---------------------------------------------------------------------------


def test_given_one_critical_when_scored_then_40() -> None:
    from app.scanner.scorer import RiskScorer

    assert RiskScorer.score(_finding("CRITICAL")) == 40


# ---------------------------------------------------------------------------
# AC-03 · 1 HIGH → 20
# ---------------------------------------------------------------------------


def test_given_one_high_when_scored_then_20() -> None:
    from app.scanner.scorer import RiskScorer

    assert RiskScorer.score(_finding("HIGH")) == 20


# ---------------------------------------------------------------------------
# AC-04 · 1 MEDIUM → 5
# ---------------------------------------------------------------------------


def test_given_one_medium_when_scored_then_5() -> None:
    from app.scanner.scorer import RiskScorer

    assert RiskScorer.score(_finding("MEDIUM")) == 5


# ---------------------------------------------------------------------------
# AC-05 · 3 CRITICAL → 100 (capped)
# ---------------------------------------------------------------------------


def test_given_three_critical_when_scored_then_100() -> None:
    from app.scanner.scorer import RiskScorer

    assert RiskScorer.score(_finding("CRITICAL", 3)) == 100


# ---------------------------------------------------------------------------
# AC-06 · 2 CRITICAL + 1 HIGH → min(80+20, 100) = 100
# ---------------------------------------------------------------------------


def test_given_two_critical_one_high_when_scored_then_100() -> None:
    from app.scanner.scorer import RiskScorer

    findings = _finding("CRITICAL", 2) + _finding("HIGH", 1)
    assert RiskScorer.score(findings) == 100


# ---------------------------------------------------------------------------
# AC-07 · 1 CRITICAL + 1 MEDIUM → 45
# ---------------------------------------------------------------------------


def test_given_one_critical_one_medium_when_scored_then_45() -> None:
    from app.scanner.scorer import RiskScorer

    findings = _finding("CRITICAL") + _finding("MEDIUM")
    assert RiskScorer.score(findings) == 45


# ---------------------------------------------------------------------------
# Additional formula checks
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("c,h,m,expected", [
    (0, 0, 0, 0),
    (1, 0, 0, 40),
    (0, 1, 0, 20),
    (0, 0, 1, 5),
    (0, 0, 20, 100),   # 20×5=100, capped
    (1, 1, 1, 65),     # 40+20+5
    (2, 0, 0, 80),
    (2, 1, 0, 100),    # 80+20=100
    (0, 5, 0, 100),    # 5×20=100
])
def test_formula_parametrised(c: int, h: int, m: int, expected: int) -> None:
    from app.scanner.scorer import RiskScorer

    findings = _finding("CRITICAL", c) + _finding("HIGH", h) + _finding("MEDIUM", m)
    assert RiskScorer.score(findings) == expected


def test_score_is_always_integer() -> None:
    from app.scanner.scorer import RiskScorer

    result = RiskScorer.score(_finding("HIGH", 3))
    assert isinstance(result, int)


def test_score_never_exceeds_100() -> None:
    from app.scanner.scorer import RiskScorer

    # 10 criticals = 400 raw — must be capped at 100
    assert RiskScorer.score(_finding("CRITICAL", 10)) == 100


def test_score_is_deterministic() -> None:
    from app.scanner.scorer import RiskScorer

    findings = _finding("CRITICAL", 2) + _finding("MEDIUM", 3)
    assert RiskScorer.score(findings) == RiskScorer.score(findings)
