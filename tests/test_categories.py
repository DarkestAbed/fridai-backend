import pytest
from httpx import AsyncClient


async def _create_category(client: AsyncClient, name: str = "Work") -> dict:
    r = await client.post("/api/categories", json={"name": name})
    assert r.status_code == 200
    return r.json()


async def _create_task(client: AsyncClient, **overrides) -> dict:
    payload = {"title": "Task", **overrides}
    r = await client.post("/api/tasks", json=payload)
    assert r.status_code == 200
    return r.json()


# ── Create ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_category(client: AsyncClient):
    cat = await _create_category(client, "Home")
    assert cat["id"] > 0
    assert cat["name"] == "Home"


@pytest.mark.asyncio
async def test_create_category_duplicate(client: AsyncClient):
    await _create_category(client, "Unique")
    r = await client.post("/api/categories", json={"name": "Unique"})
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_create_category_strips_whitespace(client: AsyncClient):
    cat = await _create_category(client, "  Padded  ")
    assert cat["name"] == "Padded"


# ── List ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_categories_empty(client: AsyncClient):
    r = await client.get("/api/categories")
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_list_categories(client: AsyncClient):
    await _create_category(client, "Alpha")
    await _create_category(client, "Beta")
    r = await client.get("/api/categories")
    names = [c["name"] for c in r.json()]
    assert "Alpha" in names
    assert "Beta" in names


@pytest.mark.asyncio
async def test_list_categories_search(client: AsyncClient):
    await _create_category(client, "Work")
    await _create_category(client, "Personal")
    r = await client.get("/api/categories", params={"q": "per"})
    assert len(r.json()) == 1
    assert r.json()[0]["name"] == "Personal"


# ── Tasks by category ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_tasks_by_category(client: AsyncClient):
    cat = await _create_category(client, "Cat1")
    await _create_task(client, title="InCat", category_id=cat["id"])
    await _create_task(client, title="NoCat")
    r = await client.get(f"/api/categories/{cat['id']}/tasks")
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.json()[0]["title"] == "InCat"


@pytest.mark.asyncio
async def test_tasks_by_category_hide_completed(client: AsyncClient):
    cat = await _create_category(client)
    task = await _create_task(client, title="Done", category_id=cat["id"])
    await client.post(f"/api/tasks/{task['id']}/complete")
    r = await client.get(
        f"/api/categories/{cat['id']}/tasks", params={"show_completed": False}
    )
    assert len(r.json()) == 0


# ── Delete ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_delete_category_empty(client: AsyncClient):
    cat = await _create_category(client)
    r = await client.delete(f"/api/categories/{cat['id']}")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_delete_category_not_found(client: AsyncClient):
    r = await client.delete("/api/categories/9999")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_delete_category_with_tasks_blocked(client: AsyncClient):
    cat = await _create_category(client)
    await _create_task(client, title="T", category_id=cat["id"])
    r = await client.delete(f"/api/categories/{cat['id']}")
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_delete_category_force(client: AsyncClient):
    cat = await _create_category(client)
    await _create_task(client, title="T", category_id=cat["id"])
    r = await client.delete(f"/api/categories/{cat['id']}", params={"force": True})
    assert r.status_code == 200
    # Task still exists but category_id is nulled
    tasks = (await client.get("/api/tasks")).json()
    assert len(tasks) == 1
    assert tasks[0]["category_id"] is None


@pytest.mark.asyncio
async def test_delete_category_reassign(client: AsyncClient):
    cat1 = await _create_category(client, "Source")
    cat2 = await _create_category(client, "Target")
    await _create_task(client, title="T", category_id=cat1["id"])
    r = await client.delete(
        f"/api/categories/{cat1['id']}", params={"reassign_to": cat2["id"]}
    )
    assert r.status_code == 200
    assert r.json()["deleted_category"]["tasks_reassigned_to"] == cat2["id"]
    tasks = (await client.get("/api/tasks")).json()
    assert tasks[0]["category_id"] == cat2["id"]


@pytest.mark.asyncio
async def test_delete_category_reassign_to_self(client: AsyncClient):
    cat = await _create_category(client)
    await _create_task(client, title="T", category_id=cat["id"])
    r = await client.delete(
        f"/api/categories/{cat['id']}", params={"reassign_to": cat["id"]}
    )
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_delete_category_reassign_to_nonexistent(client: AsyncClient):
    cat = await _create_category(client)
    await _create_task(client, title="T", category_id=cat["id"])
    r = await client.delete(
        f"/api/categories/{cat['id']}", params={"reassign_to": 9999}
    )
    assert r.status_code == 400
