import pytest
from httpx import AsyncClient


# ── Templates ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_template_missing(client: AsyncClient):
    """Getting a non-existent template returns empty markdown."""
    r = await client.get("/api/notifications/templates/due_soon")
    assert r.status_code == 200
    body = r.json()
    assert body["key"] == "due_soon"
    assert body["markdown"] == ""


@pytest.mark.asyncio
async def test_patch_template_create(client: AsyncClient):
    """PATCH creates a template if it doesn't exist."""
    r = await client.patch(
        "/api/notifications/templates/due_soon",
        json={"markdown": "# Custom\n{task_title} is due!"},
    )
    assert r.status_code == 200
    assert r.json()["ok"] is True

    # Verify it was persisted
    r2 = await client.get("/api/notifications/templates/due_soon")
    assert "Custom" in r2.json()["markdown"]


@pytest.mark.asyncio
async def test_patch_template_update(client: AsyncClient):
    """PATCH updates an existing template."""
    await client.patch(
        "/api/notifications/templates/overdue", json={"markdown": "v1"}
    )
    await client.patch(
        "/api/notifications/templates/overdue", json={"markdown": "v2"}
    )
    r = await client.get("/api/notifications/templates/overdue")
    assert r.json()["markdown"] == "v2"


# ── Logs ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_logs_empty(client: AsyncClient):
    r = await client.get("/api/notifications/logs")
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_get_logs_with_limit(client: AsyncClient):
    r = await client.get("/api/notifications/logs", params={"limit": 10})
    assert r.status_code == 200


# ── Cron ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_cron_no_topics(client: AsyncClient):
    """Cron with no ntfy topics configured sends zero notifications."""
    r = await client.post("/api/notifications/cron", params={"mode": "both"})
    assert r.status_code == 200
    assert r.json()["sent"] == 0


@pytest.mark.asyncio
async def test_cron_near_due_mode(client: AsyncClient):
    r = await client.post("/api/notifications/cron", params={"mode": "near_due"})
    assert r.status_code == 200
    assert "sent" in r.json()


@pytest.mark.asyncio
async def test_cron_overdue_mode(client: AsyncClient):
    r = await client.post("/api/notifications/cron", params={"mode": "overdue"})
    assert r.status_code == 200
    assert "sent" in r.json()


@pytest.mark.asyncio
async def test_cron_invalid_mode(client: AsyncClient):
    r = await client.post("/api/notifications/cron", params={"mode": "invalid"})
    assert r.status_code == 422


# ── Test endpoint ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_test_notification_no_topics(client: AsyncClient):
    """Test notification with no topics returns empty destinations."""
    r = await client.post("/api/notifications/test")
    assert r.status_code == 200
    assert r.json()["destinations"] == []
