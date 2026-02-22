import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_root(client: AsyncClient):
    r = await client.get("/")
    assert r.status_code == 200
    assert "msg" in r.json()


@pytest.mark.asyncio
async def test_health_live(client: AsyncClient):
    r = await client.get("/health/live")
    assert r.status_code == 200
    assert r.json()["status"] == "alive"


@pytest.mark.asyncio
async def test_health_ready(client: AsyncClient):
    r = await client.get("/health/ready")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ready"
    assert body["database"] == "connected"


@pytest.mark.asyncio
async def test_healthz(client: AsyncClient):
    r = await client.get("/healthz")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "healthy"
    assert body["version"] == "2.0.0-vibe"
    assert body["checks"]["database"]["status"] == "up"
    assert "python" in body["checks"]["platform"]
    assert "system" in body["checks"]["platform"]
