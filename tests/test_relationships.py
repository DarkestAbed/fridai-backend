import pytest
from httpx import AsyncClient


async def _create_task(client: AsyncClient, title: str = "Task") -> dict:
    r = await client.post("/api/tasks", json={"title": title})
    assert r.status_code == 200
    return r.json()


# ── Create ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_generic_relationship(client: AsyncClient):
    t1 = await _create_task(client, "Parent")
    t2 = await _create_task(client, "Child")
    r = await client.post(
        "/api/relationships",
        json={
            "task_id": t1["id"],
            "related_task_id": t2["id"],
            "rel_type": "generic",
        },
    )
    assert r.status_code == 200
    assert r.json()["ok"] is True
    assert r.json()["id"] > 0


@pytest.mark.asyncio
async def test_create_dependency_relationship(client: AsyncClient):
    t1 = await _create_task(client, "Blocker")
    t2 = await _create_task(client, "Blocked")
    r = await client.post(
        "/api/relationships",
        json={
            "task_id": t1["id"],
            "related_task_id": t2["id"],
            "rel_type": "dependency",
        },
    )
    assert r.status_code == 200


# ── List ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_relationships(client: AsyncClient):
    t1 = await _create_task(client, "A")
    t2 = await _create_task(client, "B")
    t3 = await _create_task(client, "C")
    await client.post(
        "/api/relationships",
        json={"task_id": t1["id"], "related_task_id": t2["id"], "rel_type": "generic"},
    )
    await client.post(
        "/api/relationships",
        json={
            "task_id": t1["id"],
            "related_task_id": t3["id"],
            "rel_type": "dependency",
        },
    )
    r = await client.get("/api/relationships", params={"task_id": t1["id"]})
    assert r.status_code == 200
    assert len(r.json()) == 2


@pytest.mark.asyncio
async def test_list_relationships_empty(client: AsyncClient):
    t1 = await _create_task(client, "Solo")
    r = await client.get("/api/relationships", params={"task_id": t1["id"]})
    assert r.json() == []


@pytest.mark.asyncio
async def test_list_relationships_missing_param(client: AsyncClient):
    """task_id is required."""
    r = await client.get("/api/relationships")
    assert r.status_code == 422
