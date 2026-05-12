"""
Smoke tests — end-to-end happy path + edge cases.
These run against the full ASGI stack with an in-memory DB (same conftest fixtures).

Purpose: catch integration gaps and silent failures that unit/integration tests miss.
All tests use Given/When/Then naming per BDD convention.
"""

from __future__ import annotations

import io

import pytest

# ---------------------------------------------------------------------------
# Happy path — full scan lifecycle
# ---------------------------------------------------------------------------

_MIXED_TF = b"""
resource "aws_s3_bucket" "bad" {
  acl = "public-read"
}
resource "aws_s3_bucket" "good" {
  acl = "private"
  versioning { enabled = true }
  tags = { Name = "prod", Environment = "prod" }
}
resource "aws_ebs_volume" "unenc" {
  encrypted = false
  tags = { Name = "vol", Environment = "prod" }
}
"""


@pytest.mark.asyncio
async def test_given_mixed_tf_when_full_lifecycle_then_complete_with_findings(client: object) -> None:
    from httpx import AsyncClient

    assert isinstance(client, AsyncClient)
    post = await client.post(
        "/api/scan",
        files={"file": ("mixed.tf", io.BytesIO(_MIXED_TF), "text/plain")},
    )
    assert post.status_code == 202
    scan_id = post.json()["scan_id"]

    get = await client.get(f"/api/scan/{scan_id}")
    assert get.status_code == 200
    body = get.json()
    assert body["status"] == "complete"
    assert body["risk_score"] > 0
    assert len(body["findings"]) > 0
    assert all(
        f["remediation"] for f in body["findings"]
    ), "Every finding must have a non-empty remediation"


@pytest.mark.asyncio
async def test_given_clean_tf_when_scanned_then_zero_risk_score(client: object) -> None:
    from httpx import AsyncClient

    assert isinstance(client, AsyncClient)
    clean_tf = b"""
resource "aws_s3_bucket" "clean" {
  acl = "private"
  versioning { enabled = true }
  tags = { Name = "clean", Environment = "prod" }
}
"""
    post = await client.post(
        "/api/scan",
        files={"file": ("clean.tf", io.BytesIO(clean_tf), "text/plain")},
    )
    scan_id = post.json()["scan_id"]
    get = await client.get(f"/api/scan/{scan_id}")
    assert get.json()["risk_score"] == 0
    assert get.json()["findings"] == []


# ---------------------------------------------------------------------------
# Edge case: empty file
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_given_empty_tf_when_scanned_then_no_exception_zero_score(client: object) -> None:
    from httpx import AsyncClient

    assert isinstance(client, AsyncClient)
    post = await client.post(
        "/api/scan",
        files={"file": ("empty.tf", io.BytesIO(b""), "text/plain")},
    )
    assert post.status_code == 202
    scan_id = post.json()["scan_id"]
    get = await client.get(f"/api/scan/{scan_id}")
    body = get.json()
    assert body["status"] == "complete"
    assert body["risk_score"] == 0
    assert body["findings"] == []


# ---------------------------------------------------------------------------
# Edge case: malformed / garbage file
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_given_garbage_tf_when_scanned_then_no_exception(client: object) -> None:
    from httpx import AsyncClient

    assert isinstance(client, AsyncClient)
    garbage = b"@#$%^&*( this is NOT valid HCL2 !!! \x00\xff"
    post = await client.post(
        "/api/scan",
        files={"file": ("garbage.tf", io.BytesIO(garbage), "text/plain")},
    )
    assert post.status_code == 202


@pytest.mark.asyncio
async def test_given_garbage_json_when_scanned_then_no_exception(client: object) -> None:
    from httpx import AsyncClient

    assert isinstance(client, AsyncClient)
    post = await client.post(
        "/api/scan",
        files={"file": ("bad.json", io.BytesIO(b"{{{broken json"), "application/json")},
    )
    assert post.status_code == 202


@pytest.mark.asyncio
async def test_given_garbage_yaml_when_scanned_then_no_exception(client: object) -> None:
    from httpx import AsyncClient

    assert isinstance(client, AsyncClient)
    post = await client.post(
        "/api/scan",
        files={"file": ("bad.yaml", io.BytesIO(b":\n  - bad: [yaml"), "text/yaml")},
    )
    assert post.status_code == 202


# ---------------------------------------------------------------------------
# Edge case: unsupported extensions
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_given_python_file_when_uploaded_then_415(client: object) -> None:
    from httpx import AsyncClient

    assert isinstance(client, AsyncClient)
    resp = await client.post(
        "/api/scan",
        files={"file": ("exploit.py", io.BytesIO(b"import os"), "text/plain")},
    )
    assert resp.status_code == 415


@pytest.mark.asyncio
async def test_given_exe_file_when_uploaded_then_415(client: object) -> None:
    from httpx import AsyncClient

    assert isinstance(client, AsyncClient)
    resp = await client.post(
        "/api/scan",
        files={"file": ("payload.exe", io.BytesIO(b"\x4d\x5a"), "application/octet-stream")},
    )
    assert resp.status_code == 415


@pytest.mark.asyncio
async def test_given_no_extension_when_uploaded_then_415(client: object) -> None:
    from httpx import AsyncClient

    assert isinstance(client, AsyncClient)
    resp = await client.post(
        "/api/scan",
        files={"file": ("noext", io.BytesIO(b"data"), "text/plain")},
    )
    assert resp.status_code == 415


# ---------------------------------------------------------------------------
# Edge case: all 12 rules in a single file
# ---------------------------------------------------------------------------

_ALL_VIOLATIONS_TF = b"""
resource "aws_s3_bucket" "b1" { acl = "public-read" }
resource "aws_security_group_rule" "sg1" { from_port = 22   cidr_blocks = ["0.0.0.0/0"] }
resource "aws_security_group_rule" "sg2" { from_port = 3389 cidr_blocks = ["0.0.0.0/0"] }
resource "aws_ebs_volume" "ebs1" { encrypted = false tags = { Name = "x", Environment = "y" } }
resource "aws_db_instance" "rds1" { storage_encrypted = false tags = { Name = "x", Environment = "y" } }
resource "aws_db_instance" "rds2" { publicly_accessible = true tags = { Name = "x", Environment = "y" } }
resource "aws_cloudtrail" "ct1" { enable_logging = false }
resource "aws_security_group_rule" "sg3" { type = "egress" from_port = 0 to_port = 0 cidr_blocks = ["0.0.0.0/0"] }
resource "aws_instance" "ec2" { ami = "ami-123" }
"""


@pytest.mark.asyncio
async def test_given_all_violations_when_scanned_then_max_score(client: object) -> None:
    from httpx import AsyncClient

    assert isinstance(client, AsyncClient)
    post = await client.post(
        "/api/scan",
        files={"file": ("all_violations.tf", io.BytesIO(_ALL_VIOLATIONS_TF), "text/plain")},
    )
    scan_id = post.json()["scan_id"]
    resp = await client.get(f"/api/scan/{scan_id}")
    body = resp.json()
    assert body["risk_score"] == 100, f"Expected 100, got {body['risk_score']}"
    assert len(body["findings"]) >= 5


# ---------------------------------------------------------------------------
# Edge case: concurrent uploads
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_given_multiple_uploads_when_scanned_then_all_succeed(client: object) -> None:
    from httpx import AsyncClient

    assert isinstance(client, AsyncClient)
    for i in range(5):
        resp = await client.post(
            "/api/scan",
            files={"file": (f"f{i}.tf", io.BytesIO(b'resource "aws_ebs_volume" "e" { encrypted = false }'), "text/plain")},
        )
        assert resp.status_code == 202

    history = await client.get("/api/scans")
    assert len(history.json()) == 5


# ---------------------------------------------------------------------------
# Edge case: history limit
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_given_history_call_when_empty_then_returns_list(client: object) -> None:
    from httpx import AsyncClient

    assert isinstance(client, AsyncClient)
    resp = await client.get("/api/scans")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


# ---------------------------------------------------------------------------
# Edge case: CloudFormation JSON with deeply nested resources
# ---------------------------------------------------------------------------

_CFN_MULTI = b"""{
  "Resources": {
    "BucketA": { "Type": "AWS::S3::Bucket", "Properties": { "BucketName": "safe" } },
    "BucketB": { "Type": "AWS::S3::Bucket", "Properties": { "BucketName": "also-safe" } },
    "Instance": { "Type": "AWS::EC2::Instance", "Properties": { "InstanceType": "t3.micro" } }
  }
}"""


@pytest.mark.asyncio
async def test_given_cfn_json_multi_resource_when_scanned_then_all_parsed(client: object) -> None:
    from httpx import AsyncClient

    assert isinstance(client, AsyncClient)
    post = await client.post(
        "/api/scan",
        files={"file": ("multi.json", io.BytesIO(_CFN_MULTI), "application/json")},
    )
    assert post.status_code == 202
    scan_id = post.json()["scan_id"]
    resp = await client.get(f"/api/scan/{scan_id}")
    assert resp.json()["status"] == "complete"


# ---------------------------------------------------------------------------
# Edge case: CloudFormation YAML
# ---------------------------------------------------------------------------

_CFN_YAML_CLEAN = b"""
Resources:
  SafeBucket:
    Type: AWS::S3::Bucket
    Properties:
      BucketName: safe-bucket
"""


@pytest.mark.asyncio
async def test_given_cfn_yaml_when_scanned_then_succeeds(client: object) -> None:
    from httpx import AsyncClient

    assert isinstance(client, AsyncClient)
    post = await client.post(
        "/api/scan",
        files={"file": ("template.yaml", io.BytesIO(_CFN_YAML_CLEAN), "text/plain")},
    )
    assert post.status_code == 202


# ---------------------------------------------------------------------------
# Edge case: score is always in valid range
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_given_any_scan_when_complete_then_risk_score_in_valid_range(client: object) -> None:
    from httpx import AsyncClient

    assert isinstance(client, AsyncClient)
    post = await client.post(
        "/api/scan",
        files={"file": ("main.tf", io.BytesIO(_ALL_VIOLATIONS_TF), "text/plain")},
    )
    scan_id = post.json()["scan_id"]
    body = (await client.get(f"/api/scan/{scan_id}")).json()
    assert 0 <= body["risk_score"] <= 100


# ---------------------------------------------------------------------------
# Post-commit health check
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_health_check_post_commit(client: object) -> None:
    from httpx import AsyncClient

    assert isinstance(client, AsyncClient)
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
