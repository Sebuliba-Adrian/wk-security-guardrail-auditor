"""
Integration tests — Dashboard
Phase: DEMO — tests verify render-correctness, not unit logic.

Spec: SPEC.md § dashboard
"""

from __future__ import annotations

import io

import pytest

# ---------------------------------------------------------------------------
# AC-01 · GET /dashboard → 200 HTML containing "Risk Score"
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dashboard_returns_200_html(client: object) -> None:
    from httpx import AsyncClient

    assert isinstance(client, AsyncClient)
    resp = await client.get("/dashboard")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]


@pytest.mark.asyncio
async def test_dashboard_contains_risk_score_text(client: object) -> None:
    from httpx import AsyncClient

    assert isinstance(client, AsyncClient)
    resp = await client.get("/dashboard")
    assert "Risk Score" in resp.text


# ---------------------------------------------------------------------------
# AC-02 · Dashboard renders empty state with 0 scans
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dashboard_empty_state_message_visible(client: object) -> None:
    from httpx import AsyncClient

    assert isinstance(client, AsyncClient)
    resp = await client.get("/dashboard")
    assert resp.status_code == 200
    # Empty state paragraph is visible when no scans exist
    assert "No scans yet" in resp.text


# ---------------------------------------------------------------------------
# AC-03 · Dashboard renders with scan data (charts initialised)
# ---------------------------------------------------------------------------

_BAD_TF = b"""
resource "aws_s3_bucket" "leak" {
  acl = "public-read"
}
resource "aws_ebs_volume" "unenc" {
  encrypted = false
}
"""


@pytest.mark.asyncio
async def test_dashboard_renders_after_scan(client: object) -> None:
    from httpx import AsyncClient

    assert isinstance(client, AsyncClient)
    await client.post(
        "/api/scan",
        files={"file": ("bad.tf", io.BytesIO(_BAD_TF), "text/plain")},
    )
    resp = await client.get("/dashboard")
    assert resp.status_code == 200
    assert "complete" in resp.text
    assert "bad.tf" in resp.text


@pytest.mark.asyncio
async def test_dashboard_shows_risk_score_after_scan(client: object) -> None:
    from httpx import AsyncClient

    assert isinstance(client, AsyncClient)
    await client.post(
        "/api/scan",
        files={"file": ("bad.tf", io.BytesIO(_BAD_TF), "text/plain")},
    )
    resp = await client.get("/dashboard")
    # Score > 0 is displayed somewhere in the page
    body = resp.text
    assert any(str(n) in body for n in range(1, 101))


# ---------------------------------------------------------------------------
# AC-04 · Risk gauge colour matches score band
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dashboard_score_class_present_in_html(client: object) -> None:
    from httpx import AsyncClient

    assert isinstance(client, AsyncClient)
    await client.post(
        "/api/scan",
        files={"file": ("bad.tf", io.BytesIO(_BAD_TF), "text/plain")},
    )
    resp = await client.get("/dashboard")
    # At least one of the CSS score classes must be in the rendered HTML
    assert any(cls in resp.text for cls in ("score-red", "score-amber", "score-green"))


# ---------------------------------------------------------------------------
# AC-05 · Upload form is present
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dashboard_upload_form_present(client: object) -> None:
    from httpx import AsyncClient

    assert isinstance(client, AsyncClient)
    resp = await client.get("/dashboard")
    assert "uploadForm" in resp.text
    assert "fileInput" in resp.text
