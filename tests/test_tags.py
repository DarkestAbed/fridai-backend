import pytest
from httpx import AsyncClient


async def _create_tag(client: AsyncClient, name: str = "urgent") -> dict:
    r = await client.post("/api/tags", json={"name": name})
    assert r.status_code == 201
    return r.json()


async def _create_task(client: AsyncClient, **overrides) -> dict:
    payload = {"title": "Task", **overrides}
    r = await client.post("/api/tasks", json=payload)
    assert r.status_code == 200
    return r.json()


# ── Create ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_tag(client: AsyncClient):
    tag = await _create_tag(client, "important")
    assert tag["id"] > 0
    assert tag["name"] == "important"


@pytest.mark.asyncio
async def test_create_tag_duplicate(client: AsyncClient):
    await _create_tag(client, "unique-tag")
    r = await client.post("/api/tags", json={"name": "unique-tag"})
    assert r.status_code == 409


# ── List ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_tags_empty(client: AsyncClient):
    r = await client.get("/api/tags")
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_list_tags(client: AsyncClient):
    await _create_tag(client, "alpha")
    await _create_tag(client, "beta")
    r = await client.get("/api/tags")
    names = [t["name"] for t in r.json()]
    assert "alpha" in names
    assert "beta" in names


@pytest.mark.asyncio
async def test_list_tags_search(client: AsyncClient):
    await _create_tag(client, "frontend")
    await _create_tag(client, "backend")
    r = await client.get("/api/tags", params={"q": "front"})
    assert len(r.json()) == 1
    assert r.json()[0]["name"] == "frontend"


# ── Tasks by tag ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_tasks_by_tag(client: AsyncClient):
    tag = await _create_tag(client, "hot")
    task = await _create_task(client, title="Tagged", tag_ids=[tag["id"]])
    await _create_task(client, title="Untagged")
    r = await client.get(f"/api/tags/{tag['id']}/tasks")
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.json()[0]["id"] == task["id"]


@pytest.mark.asyncio
async def test_tasks_by_tag_hide_completed(client: AsyncClient):
    tag = await _create_tag(client)
    task = await _create_task(client, title="Done", tag_ids=[tag["id"]])
    await client.post(f"/api/tasks/{task['id']}/complete")
    r = await client.get(
        f"/api/tags/{tag['id']}/tasks", params={"show_completed": False}
    )
    assert len(r.json()) == 0


# ── Delete ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_delete_tag_no_tasks(client: AsyncClient):
    tag = await _create_tag(client)
    r = await client.delete(f"/api/tags/{tag['id']}")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_delete_tag_not_found(client: AsyncClient):
    r = await client.delete("/api/tags/9999")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_delete_tag_with_tasks_blocked(client: AsyncClient):
    tag = await _create_tag(client)
    await _create_task(client, title="T", tag_ids=[tag["id"]])
    r = await client.delete(f"/api/tags/{tag['id']}")
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_delete_tag_force(client: AsyncClient):
    tag = await _create_tag(client)
    await _create_task(client, title="T", tag_ids=[tag["id"]])
    r = await client.delete(f"/api/tags/{tag['id']}", params={"force": True})
    assert r.status_code == 200
    body = r.json()
    assert body["message"] == "Tag deleted successfully"
    assert body["deleted_tag"]["id"] == tag["id"]
    # Tag no longer listed
    tags_r = await client.get("/api/tags")
    assert all(t["id"] != tag["id"] for t in tags_r.json())
