"""RiskScorer — deterministic 0-100 risk score from a list of Finding objects.

Formula: min(CRITICAL×40 + HIGH×20 + MEDIUM×5, 100)
"""

from __future__ import annotations

from app.scanner.engine import Finding

_WEIGHTS: dict[str, int] = {"CRITICAL": 40, "HIGH": 20, "MEDIUM": 5}


class RiskScorer:
    @staticmethod
    def score(findings: list[Finding]) -> int:
        raw = sum(_WEIGHTS.get(f.severity, 0) for f in findings)
        return min(raw, 100)
