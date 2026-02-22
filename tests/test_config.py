import pytest
from httpx import AsyncClient


# ── Get config ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_config_defaults(client: AsyncClient):
    r = await client.get("/api/config")
    assert r.status_code == 200
    body = r.json()
    # Verify all expected fields are present
    assert "timezone" in body
    assert "theme" in body
    assert "notifications_enabled" in body
    assert "near_due_hours" in body
    assert "scheduler_interval_seconds" in body
    assert "ntfy_topics" in body


# ── Patch config ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_patch_config_timezone(client: AsyncClient):
    # Get current to use as base
    current = (await client.get("/api/config")).json()
    current["timezone"] = "Europe/London"
    r = await client.patch("/api/config", json=current)
    assert r.status_code == 200
    assert r.json()["ok"] is True
    # Verify persistence
    r2 = await client.get("/api/config")
    assert r2.json()["timezone"] == "Europe/London"


@pytest.mark.asyncio
async def test_patch_config_notifications(client: AsyncClient):
    current = (await client.get("/api/config")).json()
    current["notifications_enabled"] = False
    r = await client.patch("/api/config", json=current)
    assert r.status_code == 200
    r2 = await client.get("/api/config")
    assert r2.json()["notifications_enabled"] is False


@pytest.mark.asyncio
async def test_patch_config_ntfy_topics(client: AsyncClient):
    current = (await client.get("/api/config")).json()
    current["ntfy_topics"] = "https://ntfy.sh/my-topic\nhttps://ntfy.sh/other"
    r = await client.patch("/api/config", json=current)
    assert r.status_code == 200
    r2 = await client.get("/api/config")
    assert "my-topic" in r2.json()["ntfy_topics"]


@pytest.mark.asyncio
async def test_patch_config_near_due_hours(client: AsyncClient):
    current = (await client.get("/api/config")).json()
    current["near_due_hours"] = 12
    r = await client.patch("/api/config", json=current)
    assert r.status_code == 200
    r2 = await client.get("/api/config")
    assert r2.json()["near_due_hours"] == 12


@pytest.mark.asyncio
async def test_patch_config_scheduler_interval(client: AsyncClient):
    current = (await client.get("/api/config")).json()
    current["scheduler_interval_seconds"] = 120
    r = await client.patch("/api/config", json=current)
    assert r.status_code == 200
    r2 = await client.get("/api/config")
    assert r2.json()["scheduler_interval_seconds"] == 120


@pytest.mark.asyncio
async def test_patch_config_language(client: AsyncClient):
    current = (await client.get("/api/config")).json()
    current["language"] = "es"
    r = await client.patch("/api/config", json=current)
    assert r.status_code == 200
    r2 = await client.get("/api/config")
    assert r2.json()["language"] == "es"
