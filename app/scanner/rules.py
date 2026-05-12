"""12 SecurityRule definitions — each rule is a pure predicate over a resource config dict."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SecurityRule:
    id: str
    severity: str  # Literal enforced by Finding schema
    title: str
    description: str
    remediation: str
    check: Callable[[dict[str, Any]], bool]


_SECRET_PATTERN = re.compile(
    r"(password|passwd|secret|token|api_key|apikey|private_key)",
    re.IGNORECASE,
)

_PUBLIC_ACLS = {"public-read", "public-read-write"}
_WORLD_CIDR = "0.0.0.0/0"


def _is_world_cidr(cidrs: Any) -> bool:
    if isinstance(cidrs, list):
        return _WORLD_CIDR in cidrs
    return bool(cidrs == _WORLD_CIDR)


def _has_wildcard_action(cfg: dict[str, Any]) -> bool:
    for stmt in cfg.get("statement", []):
        if not isinstance(stmt, dict):
            continue
        actions = stmt.get("actions", stmt.get("action", []))
        if isinstance(actions, list) and "*" in actions:
            return True
        if actions == "*":
            return True
    return False


def _has_hardcoded_secret(cfg: dict[str, Any]) -> bool:
    def _is_literal(v: Any) -> bool:
        return isinstance(v, str) and len(v) > 0 and not v.startswith("${") and not v.startswith("arn:")

    for key, val in cfg.items():
        if _SECRET_PATTERN.search(str(key)) and _is_literal(val):
            return True
    # SSM / Secrets Manager: parameter 'name' field indicates the secret type
    param_name = cfg.get("name", "")
    if isinstance(param_name, str) and _SECRET_PATTERN.search(param_name):
        if _is_literal(cfg.get("value")):
            return True
    return False


def _versioning_enabled(cfg: dict[str, Any]) -> bool:
    v = cfg.get("versioning")
    if not isinstance(v, dict):
        return False
    return bool(v.get("enabled", False))


RULES: list[SecurityRule] = [
    SecurityRule(
        id="S3_PUBLIC_ACL",
        severity="CRITICAL",
        title="S3 bucket has public ACL",
        description="The bucket ACL grants public read or read-write access to the internet.",
        remediation="Set the bucket acl to 'private' and use bucket policies for controlled access.",
        check=lambda cfg: cfg.get("acl") in _PUBLIC_ACLS,
    ),
    SecurityRule(
        id="SSH_OPEN_TO_WORLD",
        severity="CRITICAL",
        title="SSH port 22 open to the world",
        description="Inbound SSH is reachable from any IP address (0.0.0.0/0).",
        remediation="Restrict ingress on port 22 to known corporate CIDR ranges or use a bastion/VPN.",
        check=lambda cfg: (
            int(cfg.get("from_port", -1)) == 22
            and _is_world_cidr(cfg.get("cidr_blocks"))
        ),
    ),
    SecurityRule(
        id="RDP_OPEN_TO_WORLD",
        severity="CRITICAL",
        title="RDP port 3389 open to the world",
        description="Inbound RDP is reachable from any IP address (0.0.0.0/0).",
        remediation="Restrict ingress on port 3389 to known corporate CIDR ranges or use a VPN.",
        check=lambda cfg: (
            int(cfg.get("from_port", -1)) == 3389
            and _is_world_cidr(cfg.get("cidr_blocks"))
        ),
    ),
    SecurityRule(
        id="WILDCARD_IAM_ACTION",
        severity="CRITICAL",
        title="IAM policy grants wildcard action (*)",
        description="A policy statement allows all actions, violating the principle of least privilege.",
        remediation="Replace '*' actions with the minimum required IAM actions for this resource.",
        check=_has_wildcard_action,
    ),
    SecurityRule(
        id="UNENCRYPTED_EBS",
        severity="HIGH",
        title="EBS volume is not encrypted",
        description="The EBS volume does not have encryption enabled, risking data exposure.",
        remediation="Set 'encrypted = true' on the aws_ebs_volume resource.",
        check=lambda cfg: cfg.get("encrypted") is False,
    ),
    SecurityRule(
        id="UNENCRYPTED_RDS",
        severity="HIGH",
        title="RDS instance storage is not encrypted",
        description="The RDS instance storage is unencrypted, risking data-at-rest exposure.",
        remediation="Set 'storage_encrypted = true' on the aws_db_instance resource.",
        check=lambda cfg: cfg.get("storage_encrypted") is False,
    ),
    SecurityRule(
        id="PUBLIC_RDS",
        severity="HIGH",
        title="RDS instance is publicly accessible",
        description="The RDS instance is exposed to the public internet.",
        remediation="Set 'publicly_accessible = false' and use VPC security groups to restrict access.",
        check=lambda cfg: cfg.get("publicly_accessible") is True,
    ),
    SecurityRule(
        id="HARDCODED_SECRET",
        severity="HIGH",
        title="Hardcoded secret detected in resource config",
        description="A config attribute name matches a secret pattern (password/token/key) with a literal value.",
        remediation="Store secrets in AWS Secrets Manager or SSM Parameter Store and reference them dynamically.",
        check=_has_hardcoded_secret,
    ),
    SecurityRule(
        id="S3_VERSIONING_DISABLED",
        severity="MEDIUM",
        title="S3 bucket versioning is disabled",
        description="Versioning is not enabled, preventing recovery from accidental deletion or overwrites.",
        remediation="Add a versioning block with 'enabled = true' to the aws_s3_bucket resource.",
        check=lambda cfg: (
            cfg.get("type_hint", "aws_s3_bucket") == "aws_s3_bucket"
            and not _versioning_enabled(cfg)
        ),
    ),
    SecurityRule(
        id="CLOUDTRAIL_DISABLED",
        severity="MEDIUM",
        title="CloudTrail logging is disabled",
        description="API activity is not being audited, limiting incident response and compliance.",
        remediation="Set 'enable_logging = true' on the aws_cloudtrail resource.",
        check=lambda cfg: cfg.get("enable_logging") is False,
    ),
    SecurityRule(
        id="UNRESTRICTED_EGRESS",
        severity="MEDIUM",
        title="Unrestricted outbound traffic to the internet",
        description="A security group allows all-port egress to 0.0.0.0/0, enabling data exfiltration.",
        remediation="Restrict egress to required ports and destination CIDRs only.",
        check=lambda cfg: (
            cfg.get("type") == "egress"
            and int(cfg.get("from_port", -1)) == 0
            and int(cfg.get("to_port", -1)) == 0
            and _is_world_cidr(cfg.get("cidr_blocks"))
        ),
    ),
    SecurityRule(
        id="MISSING_REQUIRED_TAGS",
        severity="MEDIUM",
        title="Resource is missing required governance tags",
        description="The resource does not have the required 'Name' and 'Environment' tags for cost/compliance tracking.",
        remediation="Add 'Name' and 'Environment' tags to all resources per organisational tagging policy.",
        check=lambda cfg: not (
            isinstance(cfg.get("tags"), dict)
            and "Name" in cfg["tags"]
            and "Environment" in cfg["tags"]
        ),
    ),
]

# Rule lookup by id — O(1) for audit trail
RULES_BY_ID: dict[str, SecurityRule] = {r.id: r for r in RULES}
