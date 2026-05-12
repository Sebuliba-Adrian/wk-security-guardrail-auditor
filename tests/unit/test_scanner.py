"""
Unit tests — ScannerEngine + SecurityRule
Phase: RED — all tests must FAIL before implementation exists.

INTENT: As a security engineer, I want every uploaded resource checked against
all 12 rules so that no misconfiguration is silently missed.

Spec: SPEC.md § scanner-engine
"""

from __future__ import annotations

import pytest

# ---------------------------------------------------------------------------
# Helpers — resource factory
# ---------------------------------------------------------------------------


def _res(rtype: str, rname: str, **config: object) -> dict:  # type: ignore[type-arg]
    return {"type": rtype, "name": rname, "config": config}


# ---------------------------------------------------------------------------
# Finding is a Pydantic BaseModel with all required governance fields
# ---------------------------------------------------------------------------


def test_finding_is_pydantic_model() -> None:
    from pydantic import BaseModel

    from app.scanner.engine import Finding

    assert issubclass(Finding, BaseModel)


def test_finding_has_all_required_fields() -> None:
    from app.scanner.engine import Finding

    f = Finding(
        rule_id="S3_PUBLIC_ACL",
        severity="CRITICAL",
        title="S3 bucket is publicly accessible",
        description="The bucket ACL permits public read access.",
        remediation="Set acl to private.",
        resource_name="my_bucket",
        resource_type="aws_s3_bucket",
    )
    assert f.rule_id == "S3_PUBLIC_ACL"
    assert f.severity == "CRITICAL"
    assert f.resource_name == "my_bucket"


def test_finding_rejects_invalid_severity() -> None:
    from pydantic import ValidationError

    from app.scanner.engine import Finding

    with pytest.raises(ValidationError):
        Finding(
            rule_id="X",
            severity="BANANA",  # type: ignore[arg-type]
            title="t",
            description="d",
            remediation="r",
            resource_name="n",
            resource_type="t",
        )


# ---------------------------------------------------------------------------
# AC-01 · S3_PUBLIC_ACL — CRITICAL
# ---------------------------------------------------------------------------


def test_s3_public_acl_fires_on_public_read() -> None:
    from app.scanner.engine import ScannerEngine

    resources = [_res("aws_s3_bucket", "bucket", acl="public-read")]
    findings = ScannerEngine().scan(resources)
    rule_ids = [f.rule_id for f in findings]
    assert "S3_PUBLIC_ACL" in rule_ids


def test_s3_public_acl_fires_on_public_read_write() -> None:
    from app.scanner.engine import ScannerEngine

    resources = [_res("aws_s3_bucket", "bucket", acl="public-read-write")]
    findings = ScannerEngine().scan(resources)
    assert any(f.rule_id == "S3_PUBLIC_ACL" for f in findings)


def test_s3_public_acl_finding_is_critical() -> None:
    from app.scanner.engine import ScannerEngine

    resources = [_res("aws_s3_bucket", "bucket", acl="public-read")]
    findings = ScannerEngine().scan(resources)
    s3_findings = [f for f in findings if f.rule_id == "S3_PUBLIC_ACL"]
    assert s3_findings[0].severity == "CRITICAL"


# AC-02 · no finding on private ACL
def test_s3_private_acl_no_finding() -> None:
    from app.scanner.engine import ScannerEngine

    resources = [_res("aws_s3_bucket", "bucket", acl="private")]
    findings = ScannerEngine().scan(resources)
    assert not any(f.rule_id == "S3_PUBLIC_ACL" for f in findings)


# ---------------------------------------------------------------------------
# AC-03 · SSH_OPEN_TO_WORLD — CRITICAL
# ---------------------------------------------------------------------------


def test_ssh_open_fires_on_port_22_world() -> None:
    from app.scanner.engine import ScannerEngine

    resources = [_res("aws_security_group_rule", "sg", from_port=22, cidr_blocks=["0.0.0.0/0"])]
    findings = ScannerEngine().scan(resources)
    assert any(f.rule_id == "SSH_OPEN_TO_WORLD" for f in findings)


# AC-04 · no finding on private CIDR
def test_ssh_open_no_finding_on_private_cidr() -> None:
    from app.scanner.engine import ScannerEngine

    resources = [_res("aws_security_group_rule", "sg", from_port=22, cidr_blocks=["10.0.0.0/8"])]
    findings = ScannerEngine().scan(resources)
    assert not any(f.rule_id == "SSH_OPEN_TO_WORLD" for f in findings)


# ---------------------------------------------------------------------------
# AC-07 / AC-08 parametrised — all 12 rules fire + no-fire
# ---------------------------------------------------------------------------

FIRE_CASES: list[tuple[str, dict]] = [  # type: ignore[type-arg]
    ("S3_PUBLIC_ACL", _res("aws_s3_bucket", "b", acl="public-read")),
    ("SSH_OPEN_TO_WORLD", _res("aws_security_group_rule", "sg", from_port=22, cidr_blocks=["0.0.0.0/0"])),
    ("RDP_OPEN_TO_WORLD", _res("aws_security_group_rule", "sg", from_port=3389, cidr_blocks=["0.0.0.0/0"])),
    ("WILDCARD_IAM_ACTION", _res("aws_iam_policy_document", "pol", statement=[{"actions": ["*"]}])),
    ("UNENCRYPTED_EBS", _res("aws_ebs_volume", "ebs", encrypted=False)),
    ("UNENCRYPTED_RDS", _res("aws_db_instance", "rds", storage_encrypted=False)),
    ("PUBLIC_RDS", _res("aws_db_instance", "rds", publicly_accessible=True)),
    ("HARDCODED_SECRET", _res("aws_ssm_parameter", "p", name="db_password", value="s3cr3t!")),
    ("S3_VERSIONING_DISABLED", _res("aws_s3_bucket", "b")),  # versioning block absent
    ("CLOUDTRAIL_DISABLED", _res("aws_cloudtrail", "ct", enable_logging=False)),
    ("UNRESTRICTED_EGRESS", _res("aws_security_group_rule", "sg", type="egress", from_port=0, to_port=0, cidr_blocks=["0.0.0.0/0"])),
    ("MISSING_REQUIRED_TAGS", _res("aws_instance", "ec2")),  # no tags at all
]

NO_FIRE_CASES: list[tuple[str, dict]] = [  # type: ignore[type-arg]
    ("S3_PUBLIC_ACL", _res("aws_s3_bucket", "b", acl="private")),
    ("SSH_OPEN_TO_WORLD", _res("aws_security_group_rule", "sg", from_port=22, cidr_blocks=["10.0.0.0/8"])),
    ("RDP_OPEN_TO_WORLD", _res("aws_security_group_rule", "sg", from_port=3389, cidr_blocks=["192.168.1.0/24"])),
    ("WILDCARD_IAM_ACTION", _res("aws_iam_policy_document", "pol", statement=[{"actions": ["s3:GetObject"]}])),
    ("UNENCRYPTED_EBS", _res("aws_ebs_volume", "ebs", encrypted=True)),
    ("UNENCRYPTED_RDS", _res("aws_db_instance", "rds", storage_encrypted=True)),
    ("PUBLIC_RDS", _res("aws_db_instance", "rds", publicly_accessible=False)),
    ("HARDCODED_SECRET", _res("aws_ssm_parameter", "p", name="region", value="us-east-1")),
    ("S3_VERSIONING_DISABLED", _res("aws_s3_bucket", "b", versioning={"enabled": True})),
    ("CLOUDTRAIL_DISABLED", _res("aws_cloudtrail", "ct", enable_logging=True)),
    ("UNRESTRICTED_EGRESS", _res("aws_security_group_rule", "sg", type="egress", from_port=443, to_port=443, cidr_blocks=["10.0.0.0/8"])),
    ("MISSING_REQUIRED_TAGS", _res("aws_instance", "ec2", tags={"Name": "web", "Environment": "prod"})),
]


@pytest.mark.parametrize("rule_id,resource", FIRE_CASES, ids=[c[0] for c in FIRE_CASES])
def test_rule_fires_on_bad_input(rule_id: str, resource: dict) -> None:  # type: ignore[type-arg]
    from app.scanner.engine import ScannerEngine

    findings = ScannerEngine().scan([resource])
    assert any(f.rule_id == rule_id for f in findings), (
        f"Expected {rule_id} to fire on {resource}"
    )


@pytest.mark.parametrize("rule_id,resource", NO_FIRE_CASES, ids=[c[0] for c in NO_FIRE_CASES])
def test_rule_does_not_fire_on_compliant_input(rule_id: str, resource: dict) -> None:  # type: ignore[type-arg]
    from app.scanner.engine import ScannerEngine

    findings = ScannerEngine().scan([resource])
    assert not any(f.rule_id == rule_id for f in findings), (
        f"Expected {rule_id} NOT to fire on {resource}"
    )


# ---------------------------------------------------------------------------
# AC-05 · Missing / partial keys — no finding, no exception
# ---------------------------------------------------------------------------


def test_resource_with_no_config_keys_does_not_raise() -> None:
    from app.scanner.engine import ScannerEngine

    resources = [{"type": "aws_s3_bucket", "name": "bare", "config": {}}]
    result = ScannerEngine().scan(resources)
    assert isinstance(result, list)


def test_unknown_resource_type_does_not_raise() -> None:
    from app.scanner.engine import ScannerEngine

    resources = [_res("aws_unknown_service", "x", foo="bar")]
    result = ScannerEngine().scan(resources)
    assert isinstance(result, list)


def test_resource_missing_config_key_entirely_does_not_raise() -> None:
    from app.scanner.engine import ScannerEngine

    resources = [{"type": "aws_s3_bucket", "name": "bare"}]  # no 'config' key
    result = ScannerEngine().scan(resources)
    assert isinstance(result, list)


# ---------------------------------------------------------------------------
# AC-06 · Clean scan — empty findings
# ---------------------------------------------------------------------------


def test_all_compliant_resources_return_empty_findings() -> None:
    from app.scanner.engine import ScannerEngine

    resources = [
        _res("aws_s3_bucket", "b", acl="private", versioning={"enabled": True},
             tags={"Name": "prod", "Environment": "prod"}),
        _res("aws_ebs_volume", "ebs", encrypted=True, tags={"Name": "x", "Environment": "y"}),
        _res("aws_db_instance", "rds", storage_encrypted=True, publicly_accessible=False,
             tags={"Name": "db", "Environment": "prod"}),
    ]
    findings = ScannerEngine().scan(resources)
    assert findings == []


# ---------------------------------------------------------------------------
# Governance: all findings carry resource provenance
# ---------------------------------------------------------------------------


def test_finding_carries_resource_name_and_type() -> None:
    from app.scanner.engine import ScannerEngine

    resources = [_res("aws_s3_bucket", "my_bucket", acl="public-read")]
    findings = ScannerEngine().scan(resources)
    s3 = next(f for f in findings if f.rule_id == "S3_PUBLIC_ACL")
    assert s3.resource_name == "my_bucket"
    assert s3.resource_type == "aws_s3_bucket"


def test_finding_has_non_empty_remediation() -> None:
    from app.scanner.engine import ScannerEngine

    resources = [_res("aws_s3_bucket", "b", acl="public-read")]
    findings = ScannerEngine().scan(resources)
    s3 = next(f for f in findings if f.rule_id == "S3_PUBLIC_ACL")
    assert len(s3.remediation) > 10


def test_scan_is_deterministic() -> None:
    from app.scanner.engine import ScannerEngine

    resources = [_res("aws_s3_bucket", "b", acl="public-read")]
    engine = ScannerEngine()
    run1 = [f.rule_id for f in engine.scan(resources)]
    run2 = [f.rule_id for f in engine.scan(resources)]
    assert run1 == run2
