import pytest
from httpx import AsyncClient


async def _create_task(client: AsyncClient, **overrides) -> dict:
    payload = {"title": "Task", **overrides}
    r = await client.post("/api/tasks", json=payload)
    assert r.status_code == 200
    return r.json()


async def _create_category(client: AsyncClient, name: str) -> dict:
    r = await client.post("/api/categories", json={"name": name})
    assert r.status_code == 200
    return r.json()


async def _create_tag(client: AsyncClient, name: str) -> dict:
    r = await client.post("/api/tags", json={"name": name})
    assert r.status_code == 201
    return r.json()


# ── Categories summary ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_categories_summary_empty(client: AsyncClient):
    r = await client.get("/api/views/categories-summary")
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_categories_summary_with_data(client: AsyncClient):
    cat = await _create_category(client, "Home")
    await _create_task(client, title="T1", category_id=cat["id"])
    await _create_task(client, title="T2", category_id=cat["id"])
    r = await client.get("/api/views/categories-summary")
    items = r.json()
    home = next(i for i in items if i["key"] == "Home")
    assert home["count"] == 2


@pytest.mark.asyncio
async def test_categories_summary_empty_category(client: AsyncClient):
    """A category with zero tasks should still appear with count 0."""
    await _create_category(client, "Empty")
    r = await client.get("/api/views/categories-summary")
    empty = next(i for i in r.json() if i["key"] == "Empty")
    assert empty["count"] == 0


# ── Status summary ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_status_summary_empty(client: AsyncClient):
    r = await client.get("/api/views/status-summary")
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_status_summary_mixed(client: AsyncClient):
    t1 = await _create_task(client, title="A")
    await _create_task(client, title="B")
    await client.post(f"/api/tasks/{t1['id']}/complete")
    r = await client.get("/api/views/status-summary")
    items = {i["key"]: i["count"] for i in r.json()}
    assert items.get("pending", 0) == 1
    assert items.get("completed", 0) == 1


# ── Tags summary ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_tags_summary_empty(client: AsyncClient):
    r = await client.get("/api/views/tags-summary")
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_tags_summary_with_data(client: AsyncClient):
    tag = await _create_tag(client, "hot")
    await _create_task(client, title="T1", tag_ids=[tag["id"]])
    await _create_task(client, title="T2", tag_ids=[tag["id"]])
    r = await client.get("/api/views/tags-summary")
    items = r.json()
    hot = next(i for i in items if i["key"] == "hot")
    assert hot["count"] == 2


@pytest.mark.asyncio
async def test_tags_summary_unused_tag(client: AsyncClient):
    """A tag with no tasks should appear with count 0."""
    await _create_tag(client, "orphan")
    r = await client.get("/api/views/tags-summary")
    orphan = next(i for i in r.json() if i["key"] == "orphan")
    assert orphan["count"] == 0
