"""
Integration tests — API routes
Phase: RED — all tests must FAIL before implementation exists.

INTENT: As a developer, I want a clean REST API so that I can integrate the
scanner into any CI/CD pipeline or tool.

Spec: SPEC.md § api-routes
"""

from __future__ import annotations

import io

import pytest

# ---------------------------------------------------------------------------
# Pydantic schema contracts — these must be importable as BaseModels
# ---------------------------------------------------------------------------


def test_scan_queued_response_is_pydantic_model() -> None:
    from pydantic import BaseModel

    from app.schemas.scan import ScanQueuedResponse

    assert issubclass(ScanQueuedResponse, BaseModel)


def test_finding_response_is_pydantic_model() -> None:
    from pydantic import BaseModel

    from app.schemas.scan import FindingResponse

    assert issubclass(FindingResponse, BaseModel)


def test_scan_response_is_pydantic_model() -> None:
    from pydantic import BaseModel

    from app.schemas.scan import ScanResponse

    assert issubclass(ScanResponse, BaseModel)


def test_scan_history_item_is_pydantic_model() -> None:
    from pydantic import BaseModel

    from app.schemas.scan import ScanHistoryItem

    assert issubclass(ScanHistoryItem, BaseModel)


def test_scan_response_has_required_fields() -> None:
    """AC-08: result must contain scan_id, filename, status, risk_score, findings, summary, scanned_at."""
    from app.schemas.scan import ScanResponse

    fields = set(ScanResponse.model_fields.keys())
    required = {"scan_id", "filename", "status", "risk_score", "findings", "scanned_at"}
    assert required.issubset(fields), f"Missing fields: {required - fields}"


def test_finding_response_has_governance_fields() -> None:
    from app.schemas.scan import FindingResponse

    fields = set(FindingResponse.model_fields.keys())
    required = {"rule_id", "severity", "title", "description", "remediation",
                "resource_name", "resource_type"}
    assert required.issubset(fields), f"Missing fields: {required - fields}"


# ---------------------------------------------------------------------------
# AC-07 · GET /api/health → 200 {status: "ok"}
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_health_endpoint_returns_ok(client: object) -> None:
    from httpx import AsyncClient

    assert isinstance(client, AsyncClient)
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_health_endpoint_returns_request_id_header(client: object) -> None:
    from httpx import AsyncClient

    assert isinstance(client, AsyncClient)
    resp = await client.get("/api/health")
    assert "x-request-id" in resp.headers
    assert len(resp.headers["x-request-id"]) >= 8


# ---------------------------------------------------------------------------
# AC-01 · POST /api/scan — valid .tf → 202 with scan_id + status
# ---------------------------------------------------------------------------

_TF_CONTENT = b"""
resource "aws_s3_bucket" "bad_bucket" {
  acl = "public-read"
}
"""

_CFN_CONTENT = b"""{
  "Resources": {
    "MyBucket": {
      "Type": "AWS::S3::Bucket",
      "Properties": {"BucketName": "safe-bucket"}
    }
  }
}"""


@pytest.mark.asyncio
async def test_post_scan_valid_tf_returns_202(client: object) -> None:
    from httpx import AsyncClient

    assert isinstance(client, AsyncClient)
    resp = await client.post(
        "/api/scan",
        files={"file": ("main.tf", io.BytesIO(_TF_CONTENT), "text/plain")},
    )
    assert resp.status_code == 202
    body = resp.json()
    assert "scan_id" in body
    assert body["status"] in ("queued", "complete")


@pytest.mark.asyncio
async def test_post_scan_valid_json_returns_202(client: object) -> None:
    from httpx import AsyncClient

    assert isinstance(client, AsyncClient)
    resp = await client.post(
        "/api/scan",
        files={"file": ("template.json", io.BytesIO(_CFN_CONTENT), "application/json")},
    )
    assert resp.status_code == 202


@pytest.mark.asyncio
async def test_get_scan_cfn_public_bucket_returns_public_acl_finding(client: object) -> None:
    from httpx import AsyncClient

    assert isinstance(client, AsyncClient)
    cfn_public = b"""{
      "Resources": {
        "BadBucket": {
          "Type": "AWS::S3::Bucket",
          "Properties": {
            "BucketName": "bad-bucket",
            "AccessControl": "PublicRead"
          }
        }
      }
    }"""
    post = await client.post(
        "/api/scan",
        files={"file": ("bad.json", io.BytesIO(cfn_public), "application/json")},
    )
    scan_id = post.json()["scan_id"]
    resp = await client.get(f"/api/scan/{scan_id}")
    body = resp.json()

    assert any(f["rule_id"] == "S3_PUBLIC_ACL" for f in body["findings"])
    assert body["risk_score"] > 0


@pytest.mark.asyncio
async def test_post_scan_returns_scan_id_uuid_format(client: object) -> None:
    import re

    from httpx import AsyncClient

    assert isinstance(client, AsyncClient)
    resp = await client.post(
        "/api/scan",
        files={"file": ("main.tf", io.BytesIO(_TF_CONTENT), "text/plain")},
    )
    scan_id = resp.json()["scan_id"]
    assert re.match(r"[0-9a-f-]{36}", scan_id), f"Not a UUID: {scan_id}"


# ---------------------------------------------------------------------------
# AC-02 · .py upload → 415 Unsupported Media Type
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_post_scan_unsupported_extension_returns_415(client: object) -> None:
    from httpx import AsyncClient

    assert isinstance(client, AsyncClient)
    resp = await client.post(
        "/api/scan",
        files={"file": ("script.py", io.BytesIO(b"print('hello')"), "text/plain")},
    )
    assert resp.status_code == 415


# ---------------------------------------------------------------------------
# AC-03 · No file field → 422 Unprocessable Entity
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_post_scan_no_file_returns_422(client: object) -> None:
    from httpx import AsyncClient

    assert isinstance(client, AsyncClient)
    resp = await client.post("/api/scan")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_post_scan_oversized_file_returns_413(client: object, monkeypatch: pytest.MonkeyPatch) -> None:
    from httpx import AsyncClient

    from app.api.routes import scan as scan_module

    assert isinstance(client, AsyncClient)
    monkeypatch.setattr(scan_module.settings, "max_file_size_mb", 0)
    resp = await client.post(
        "/api/scan",
        files={"file": ("main.tf", io.BytesIO(_TF_CONTENT), "text/plain")},
    )
    assert resp.status_code == 413


# ---------------------------------------------------------------------------
# AC-04 · GET /api/scan/{id} → 200 with full result
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_scan_valid_id_returns_200(client: object) -> None:
    from httpx import AsyncClient

    assert isinstance(client, AsyncClient)
    post = await client.post(
        "/api/scan",
        files={"file": ("main.tf", io.BytesIO(_TF_CONTENT), "text/plain")},
    )
    scan_id = post.json()["scan_id"]

    resp = await client.get(f"/api/scan/{scan_id}")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_get_scan_result_contains_all_required_fields(client: object) -> None:
    """AC-08 via HTTP — result must have all schema fields."""
    from httpx import AsyncClient

    assert isinstance(client, AsyncClient)
    post = await client.post(
        "/api/scan",
        files={"file": ("main.tf", io.BytesIO(_TF_CONTENT), "text/plain")},
    )
    scan_id = post.json()["scan_id"]
    resp = await client.get(f"/api/scan/{scan_id}")
    body = resp.json()

    for field in ("scan_id", "filename", "status", "risk_score", "findings", "scanned_at"):
        assert field in body, f"Missing field: {field}"


@pytest.mark.asyncio
async def test_get_scan_tf_with_violations_returns_findings(client: object) -> None:
    from httpx import AsyncClient

    assert isinstance(client, AsyncClient)
    post = await client.post(
        "/api/scan",
        files={"file": ("main.tf", io.BytesIO(_TF_CONTENT), "text/plain")},
    )
    scan_id = post.json()["scan_id"]
    resp = await client.get(f"/api/scan/{scan_id}")
    body = resp.json()

    assert isinstance(body["findings"], list)
    assert len(body["findings"]) > 0
    assert body["risk_score"] > 0


@pytest.mark.asyncio
async def test_get_scan_finding_has_remediation(client: object) -> None:
    from httpx import AsyncClient

    assert isinstance(client, AsyncClient)
    post = await client.post(
        "/api/scan",
        files={"file": ("main.tf", io.BytesIO(_TF_CONTENT), "text/plain")},
    )
    scan_id = post.json()["scan_id"]
    resp = await client.get(f"/api/scan/{scan_id}")
    finding = resp.json()["findings"][0]

    assert "remediation" in finding
    assert len(finding["remediation"]) > 10


# ---------------------------------------------------------------------------
# AC-05 · GET /api/scan/{unknown_id} → 404
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_scan_unknown_id_returns_404(client: object) -> None:
    from httpx import AsyncClient

    assert isinstance(client, AsyncClient)
    resp = await client.get("/api/scan/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# AC-06 · GET /api/scans — empty database → 200 []
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_scans_empty_db_returns_200_empty_list(client: object) -> None:
    from httpx import AsyncClient

    assert isinstance(client, AsyncClient)
    resp = await client.get("/api/scans")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_get_scans_after_upload_returns_one_item(client: object) -> None:
    from httpx import AsyncClient

    assert isinstance(client, AsyncClient)
    await client.post(
        "/api/scan",
        files={"file": ("main.tf", io.BytesIO(_TF_CONTENT), "text/plain")},
    )
    resp = await client.get("/api/scans")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 1
    assert "scan_id" in items[0]
    assert "filename" in items[0]
    assert "risk_score" in items[0]
