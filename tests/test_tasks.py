import pytest
from httpx import AsyncClient


# ── Helpers ──────────────────────────────────────────────────────────────────

async def _create_task(client: AsyncClient, **overrides) -> dict:
    payload = {"title": "Default task", **overrides}
    r = await client.post("/api/tasks", json=payload)
    assert r.status_code == 200
    return r.json()


async def _create_category(client: AsyncClient, name: str = "Work") -> dict:
    r = await client.post("/api/categories", json={"name": name})
    assert r.status_code == 200
    return r.json()


async def _create_tag(client: AsyncClient, name: str = "urgent") -> dict:
    r = await client.post("/api/tags", json={"name": name})
    assert r.status_code == 201
    return r.json()


# ── Create ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_task_minimal(client: AsyncClient):
    task = await _create_task(client, title="Buy milk")
    assert task["id"] > 0
    assert task["title"] == "Buy milk"
    assert task["status"] == "pending"
    assert task["description"] is None
    assert task["due_at"] is None
    assert task["category_id"] is None
    assert task["tag_ids"] == []


@pytest.mark.asyncio
async def test_create_task_with_description(client: AsyncClient):
    task = await _create_task(client, title="T1", description="Some details")
    assert task["description"] == "Some details"


@pytest.mark.asyncio
async def test_create_task_with_category(client: AsyncClient):
    cat = await _create_category(client)
    task = await _create_task(client, title="T1", category_id=cat["id"])
    assert task["category_id"] == cat["id"]


@pytest.mark.asyncio
async def test_create_task_with_tags(client: AsyncClient):
    t1 = await _create_tag(client, "alpha")
    t2 = await _create_tag(client, "beta")
    task = await _create_task(client, title="Tagged", tag_ids=[t1["id"], t2["id"]])
    assert set(task["tag_ids"]) == {t1["id"], t2["id"]}


@pytest.mark.asyncio
async def test_create_task_with_due_date(client: AsyncClient):
    task = await _create_task(client, title="Due", due_at="2099-12-31T23:59:00")
    assert task["due_at"] is not None


@pytest.mark.asyncio
async def test_create_task_invalid_category(client: AsyncClient):
    r = await client.post("/api/tasks", json={"title": "T", "category_id": 9999})
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_create_task_invalid_tags(client: AsyncClient):
    r = await client.post("/api/tasks", json={"title": "T", "tag_ids": [9999]})
    assert r.status_code == 400


# ── List / Filter ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_tasks_empty(client: AsyncClient):
    r = await client.get("/api/tasks")
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_list_tasks_returns_created(client: AsyncClient):
    await _create_task(client, title="A")
    await _create_task(client, title="B")
    r = await client.get("/api/tasks")
    assert len(r.json()) == 2


@pytest.mark.asyncio
async def test_list_tasks_filter_by_status(client: AsyncClient):
    task = await _create_task(client, title="X")
    await client.post(f"/api/tasks/{task['id']}/complete")
    r = await client.get("/api/tasks", params={"status": "completed"})
    assert all(t["status"] == "completed" for t in r.json())

    r2 = await client.get("/api/tasks", params={"status": "pending"})
    assert all(t["status"] == "pending" for t in r2.json())


@pytest.mark.asyncio
async def test_list_tasks_filter_by_category(client: AsyncClient):
    cat = await _create_category(client, "Home")
    await _create_task(client, title="With cat", category_id=cat["id"])
    await _create_task(client, title="No cat")
    r = await client.get("/api/tasks", params={"category": cat["id"]})
    assert len(r.json()) == 1
    assert r.json()[0]["category_id"] == cat["id"]


@pytest.mark.asyncio
async def test_list_tasks_filter_by_tag(client: AsyncClient):
    tag = await _create_tag(client, "vip")
    task = await _create_task(client, title="Tagged", tag_ids=[tag["id"]])
    await _create_task(client, title="Not tagged")
    r = await client.get("/api/tasks", params={"tag": tag["id"]})
    assert len(r.json()) == 1
    assert r.json()[0]["id"] == task["id"]


@pytest.mark.asyncio
async def test_list_tasks_text_search(client: AsyncClient):
    await _create_task(client, title="Buy groceries")
    await _create_task(client, title="Clean house")
    r = await client.get("/api/tasks", params={"q": "groceries"})
    assert len(r.json()) == 1
    assert "groceries" in r.json()[0]["title"].lower()


@pytest.mark.asyncio
async def test_list_all_alias(client: AsyncClient):
    await _create_task(client, title="A1")
    r = await client.get("/api/tasks/all")
    assert r.status_code == 200
    assert len(r.json()) == 1


# ── Search ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_search_by_title(client: AsyncClient):
    await _create_task(client, title="Unique needle")
    await _create_task(client, title="Other task")
    r = await client.get("/api/tasks/search", params={"q": "needle"})
    assert len(r.json()) == 1


@pytest.mark.asyncio
async def test_search_by_description(client: AsyncClient):
    await _create_task(client, title="T1", description="hidden gem here")
    r = await client.get("/api/tasks/search", params={"q": "hidden gem"})
    assert len(r.json()) == 1


@pytest.mark.asyncio
async def test_search_no_results(client: AsyncClient):
    await _create_task(client, title="Something")
    r = await client.get("/api/tasks/search", params={"q": "nonexistent"})
    assert r.json() == []


@pytest.mark.asyncio
async def test_search_sql_injection(client: AsyncClient):
    """SQL injection attempts must not crash or drop tables."""
    await _create_task(client, title="Safe task")
    r = await client.get("/api/tasks/search", params={"q": "%'; DROP TABLE tasks; --"})
    assert r.status_code == 200
    # Table still intact
    r2 = await client.get("/api/tasks")
    assert r2.status_code == 200
    assert len(r2.json()) == 1


# ── Overdue ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_overdue_endpoint(client: AsyncClient):
    # Past due date → should appear in overdue
    await _create_task(client, title="Past", due_at="2020-01-01T00:00:00")
    # Future due date → should NOT appear
    await _create_task(client, title="Future", due_at="2099-01-01T00:00:00")
    # No due date → should NOT appear
    await _create_task(client, title="NoDue")
    r = await client.get("/api/tasks/overdue")
    assert r.status_code == 200
    titles = [t["title"] for t in r.json()]
    assert "Past" in titles
    assert "Future" not in titles
    assert "NoDue" not in titles


@pytest.mark.asyncio
async def test_overdue_excludes_completed(client: AsyncClient):
    task = await _create_task(client, title="Done", due_at="2020-01-01T00:00:00")
    await client.post(f"/api/tasks/{task['id']}/complete")
    r = await client.get("/api/tasks/overdue")
    assert len(r.json()) == 0


# ── Next window ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_next_window_default(client: AsyncClient):
    """Default window is 48 hours; far-future tasks excluded."""
    await _create_task(client, title="Far", due_at="2099-06-01T00:00:00")
    r = await client.get("/api/tasks/next")
    assert r.status_code == 200
    # Far future task should not appear in 48h window
    assert all(t["title"] != "Far" for t in r.json())


@pytest.mark.asyncio
async def test_next_window_excludes_completed(client: AsyncClient):
    task = await _create_task(client, title="Comp", due_at="2020-01-01T00:00:00")
    await client.post(f"/api/tasks/{task['id']}/complete")
    r = await client.get("/api/tasks/next", params={"hours": 999999})
    ids = [t["id"] for t in r.json()]
    assert task["id"] not in ids


# ── Complete / Toggle ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_complete_task(client: AsyncClient):
    task = await _create_task(client, title="Toggle me")
    assert task["status"] == "pending"

    r = await client.post(f"/api/tasks/{task['id']}/complete")
    assert r.status_code == 200
    assert r.json()["status"] == "completed"

    # Toggle back
    r2 = await client.post(f"/api/tasks/{task['id']}/complete")
    assert r2.json()["status"] == "pending"


@pytest.mark.asyncio
async def test_complete_task_not_found(client: AsyncClient):
    r = await client.post("/api/tasks/9999/complete")
    assert r.status_code == 404


# ── Delete ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_delete_completed_task(client: AsyncClient):
    task = await _create_task(client, title="Del me")
    await client.post(f"/api/tasks/{task['id']}/complete")
    r = await client.delete(f"/api/tasks/{task['id']}")
    assert r.status_code == 200
    assert "deleted_task" in r.json()


@pytest.mark.asyncio
async def test_delete_pending_task_blocked(client: AsyncClient):
    task = await _create_task(client, title="Pending")
    r = await client.delete(f"/api/tasks/{task['id']}")
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_delete_pending_task_force(client: AsyncClient):
    task = await _create_task(client, title="Forced")
    r = await client.delete(f"/api/tasks/{task['id']}", params={"force": True})
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_delete_task_not_found(client: AsyncClient):
    r = await client.delete("/api/tasks/9999", params={"force": True})
    assert r.status_code == 404


# ── Patch (general) ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_patch_task_title(client: AsyncClient):
    task = await _create_task(client, title="Old title")
    r = await client.patch(f"/api/tasks/{task['id']}", json={"title": "New title"})
    assert r.status_code == 200
    assert r.json()["title"] == "New title"


@pytest.mark.asyncio
async def test_patch_task_description(client: AsyncClient):
    task = await _create_task(client, title="T")
    r = await client.patch(f"/api/tasks/{task['id']}", json={"description": "Added"})
    assert r.json()["description"] == "Added"


@pytest.mark.asyncio
async def test_patch_task_clear_description(client: AsyncClient):
    task = await _create_task(client, title="T", description="Has desc")
    r = await client.patch(f"/api/tasks/{task['id']}", json={"description": None})
    assert r.json()["description"] is None


@pytest.mark.asyncio
async def test_patch_task_status(client: AsyncClient):
    task = await _create_task(client, title="T")
    r = await client.patch(f"/api/tasks/{task['id']}", json={"status": "completed"})
    assert r.json()["status"] == "completed"


@pytest.mark.asyncio
async def test_patch_task_category(client: AsyncClient):
    cat = await _create_category(client, "Errands")
    task = await _create_task(client, title="T")
    r = await client.patch(f"/api/tasks/{task['id']}", json={"category_id": cat["id"]})
    assert r.json()["category_id"] == cat["id"]


@pytest.mark.asyncio
async def test_patch_task_clear_category(client: AsyncClient):
    cat = await _create_category(client)
    task = await _create_task(client, title="T", category_id=cat["id"])
    r = await client.patch(f"/api/tasks/{task['id']}", json={"category_id": None})
    assert r.json()["category_id"] is None


@pytest.mark.asyncio
async def test_patch_task_tags(client: AsyncClient):
    t1 = await _create_tag(client, "a")
    t2 = await _create_tag(client, "b")
    task = await _create_task(client, title="T", tag_ids=[t1["id"]])
    # Replace tags entirely
    r = await client.patch(f"/api/tasks/{task['id']}", json={"tag_ids": [t2["id"]]})
    assert r.json()["tag_ids"] == [t2["id"]]


@pytest.mark.asyncio
async def test_patch_task_clear_tags(client: AsyncClient):
    tag = await _create_tag(client, "x")
    task = await _create_task(client, title="T", tag_ids=[tag["id"]])
    r = await client.patch(f"/api/tasks/{task['id']}", json={"tag_ids": None})
    assert r.json()["tag_ids"] == []


@pytest.mark.asyncio
async def test_patch_task_invalid_category(client: AsyncClient):
    task = await _create_task(client, title="T")
    r = await client.patch(f"/api/tasks/{task['id']}", json={"category_id": 9999})
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_patch_task_invalid_tags(client: AsyncClient):
    task = await _create_task(client, title="T")
    r = await client.patch(f"/api/tasks/{task['id']}", json={"tag_ids": [9999]})
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_patch_task_not_found(client: AsyncClient):
    r = await client.patch("/api/tasks/9999", json={"title": "X"})
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_patch_task_no_fields_is_noop(client: AsyncClient):
    task = await _create_task(client, title="Original")
    r = await client.patch(f"/api/tasks/{task['id']}", json={})
    assert r.status_code == 200
    assert r.json()["title"] == "Original"


@pytest.mark.asyncio
async def test_patch_task_due_at(client: AsyncClient):
    task = await _create_task(client, title="T")
    r = await client.patch(
        f"/api/tasks/{task['id']}", json={"due_at": "2099-06-15T10:00:00"}
    )
    assert r.status_code == 200
    assert r.json()["due_at"] is not None


@pytest.mark.asyncio
async def test_patch_task_clear_due(client: AsyncClient):
    task = await _create_task(client, title="T", due_at="2099-01-01T00:00:00")
    r = await client.patch(f"/api/tasks/{task['id']}", json={"due_at": None})
    assert r.json()["due_at"] is None


# ── Description sub-endpoint ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_set_description_endpoint(client: AsyncClient):
    task = await _create_task(client, title="T")
    r = await client.patch(
        f"/api/tasks/{task['id']}/description", json={"description": "Updated"}
    )
    assert r.status_code == 200
    assert r.json()["description"] == "Updated"


@pytest.mark.asyncio
async def test_set_description_not_found(client: AsyncClient):
    r = await client.patch("/api/tasks/9999/description", json={"description": "X"})
    assert r.status_code == 404


# ── Due sub-endpoint ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_set_due_endpoint(client: AsyncClient):
    task = await _create_task(client, title="T")
    r = await client.patch(
        f"/api/tasks/{task['id']}/due", json={"due_at": "2099-06-15T10:00:00"}
    )
    assert r.status_code == 200
    assert r.json()["due_at"] is not None


@pytest.mark.asyncio
async def test_set_due_nullify(client: AsyncClient):
    task = await _create_task(client, title="T", due_at="2099-01-01T00:00:00")
    r = await client.patch(f"/api/tasks/{task['id']}/due", json={"due_at": None})
    assert r.status_code == 200
    assert r.json()["due_at"] is None


@pytest.mark.asyncio
async def test_set_due_not_found(client: AsyncClient):
    r = await client.patch("/api/tasks/9999/due", json={"due_at": None})
    assert r.status_code == 404


# ── Add / Remove tags ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_add_tags_to_task(client: AsyncClient):
    tag = await _create_tag(client, "new-tag")
    task = await _create_task(client, title="T")
    r = await client.post(
        f"/api/tasks/{task['id']}/tags", json={"tag_ids": [tag["id"]]}
    )
    assert r.status_code == 200
    assert tag["id"] in r.json()["tag_ids"]


@pytest.mark.asyncio
async def test_add_tags_prevents_duplicates(client: AsyncClient):
    tag = await _create_tag(client, "dup")
    task = await _create_task(client, title="T", tag_ids=[tag["id"]])
    r = await client.post(
        f"/api/tasks/{task['id']}/tags", json={"tag_ids": [tag["id"]]}
    )
    assert r.json()["tag_ids"].count(tag["id"]) == 1


@pytest.mark.asyncio
async def test_add_tags_task_not_found(client: AsyncClient):
    r = await client.post("/api/tasks/9999/tags", json={"tag_ids": [1]})
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_remove_tag_from_task(client: AsyncClient):
    tag = await _create_tag(client, "removable")
    task = await _create_task(client, title="T", tag_ids=[tag["id"]])
    r = await client.delete(f"/api/tasks/{task['id']}/tags/{tag['id']}")
    assert r.status_code == 200
    assert tag["id"] not in r.json()["tag_ids"]


@pytest.mark.asyncio
async def test_remove_tag_not_on_task(client: AsyncClient):
    tag = await _create_tag(client, "orphan")
    task = await _create_task(client, title="T")
    r = await client.delete(f"/api/tasks/{task['id']}/tags/{tag['id']}")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_remove_tag_task_not_found(client: AsyncClient):
    r = await client.delete("/api/tasks/9999/tags/1")
    assert r.status_code == 404
