"""Unit tests — health endpoint."""

from httpx import AsyncClient


async def test_given_running_app_when_health_called_then_returns_ok(
    client: AsyncClient,
) -> None:
    response = await client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
