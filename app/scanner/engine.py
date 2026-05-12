"""ScannerEngine — evaluates resources against all 12 security rules.

Returns a list of Pydantic Finding models. Never raises on malformed input.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel

from app.scanner.rules import RULES


class Finding(BaseModel):
    """Governance-grade finding record — all fields required, severity is enumerated."""

    rule_id: str
    severity: Literal["CRITICAL", "HIGH", "MEDIUM"]
    title: str
    description: str
    remediation: str
    resource_name: str
    resource_type: str

    model_config = {"frozen": True}


# Rules that apply only to specific resource types
_RESOURCE_TYPE_FILTER: dict[str, set[str]] = {
    "S3_PUBLIC_ACL": {"aws_s3_bucket"},
    "SSH_OPEN_TO_WORLD": {"aws_security_group_rule"},
    "RDP_OPEN_TO_WORLD": {"aws_security_group_rule"},
    "WILDCARD_IAM_ACTION": {"aws_iam_policy", "aws_iam_policy_document"},
    "UNENCRYPTED_EBS": {"aws_ebs_volume"},
    "UNENCRYPTED_RDS": {"aws_db_instance"},
    "PUBLIC_RDS": {"aws_db_instance"},
    "S3_VERSIONING_DISABLED": {"aws_s3_bucket"},
    "CLOUDTRAIL_DISABLED": {"aws_cloudtrail"},
    "UNRESTRICTED_EGRESS": {"aws_security_group_rule"},
}


class ScannerEngine:
    """Evaluates a list of parsed resources against all registered security rules."""

    def scan(self, resources: list[dict[str, Any]]) -> list[Finding]:
        findings: list[Finding] = []
        for resource in resources:
            rtype: str = resource.get("type", "")
            rname: str = resource.get("name", "")
            cfg: dict[str, Any] = resource.get("config", {})
            if not isinstance(cfg, dict):
                cfg = {}
            for rule in RULES:
                allowed = _RESOURCE_TYPE_FILTER.get(rule.id)
                if allowed is not None and rtype not in allowed:
                    continue
                try:
                    if rule.check(cfg):
                        findings.append(Finding(
                            rule_id=rule.id,
                            severity=rule.severity,  # type: ignore[arg-type]
                            title=rule.title,
                            description=rule.description,
                            remediation=rule.remediation,
                            resource_name=rname,
                            resource_type=rtype,
                        ))
                except Exception:  # nosec B110 — rule check must never crash the scanner
                    pass
        return findings
