"""
Input validation and security boundary tests.
Covers XSS prevention, SQL injection, boundary conditions, and schema validation.
"""

import pytest
from httpx import AsyncClient


# ── Task title validation ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_task_title_html_rejected(client: AsyncClient):
    r = await client.post("/api/tasks", json={"title": "<b>bold</b>"})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_task_title_empty_rejected(client: AsyncClient):
    r = await client.post("/api/tasks", json={"title": ""})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_task_title_whitespace_only_rejected(client: AsyncClient):
    r = await client.post("/api/tasks", json={"title": "   "})
    # The schema strips whitespace first, so "   " becomes "" which fails min_length=1
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_task_title_max_length(client: AsyncClient):
    r = await client.post("/api/tasks", json={"title": "A" * 201})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_task_title_at_max_length(client: AsyncClient):
    r = await client.post("/api/tasks", json={"title": "A" * 200})
    assert r.status_code == 200


# ── Task description validation ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_task_description_script_rejected(client: AsyncClient):
    r = await client.post(
        "/api/tasks",
        json={"title": "T", "description": "<script>alert(1)</script>"},
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_task_description_max_length(client: AsyncClient):
    r = await client.post(
        "/api/tasks", json={"title": "T", "description": "X" * 5001}
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_task_description_html_allowed(client: AsyncClient):
    """Non-script HTML in description is allowed (only <script> is blocked)."""
    r = await client.post(
        "/api/tasks", json={"title": "T", "description": "<b>bold text</b>"}
    )
    assert r.status_code == 200


# ── Category name validation ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_category_name_html_rejected(client: AsyncClient):
    r = await client.post("/api/categories", json={"name": "<img src=x>"})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_category_name_empty_rejected(client: AsyncClient):
    r = await client.post("/api/categories", json={"name": ""})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_category_name_max_length(client: AsyncClient):
    r = await client.post("/api/categories", json={"name": "C" * 101})
    assert r.status_code == 422


# ── Tag name validation ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_tag_name_html_rejected(client: AsyncClient):
    r = await client.post("/api/tags", json={"name": "<div>bad</div>"})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_tag_name_empty_rejected(client: AsyncClient):
    r = await client.post("/api/tags", json={"name": ""})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_tag_name_max_length(client: AsyncClient):
    r = await client.post("/api/tags", json={"name": "T" * 101})
    assert r.status_code == 422


# ── Tag IDs validation ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_task_negative_tag_id_rejected(client: AsyncClient):
    r = await client.post("/api/tasks", json={"title": "T", "tag_ids": [-1]})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_task_zero_tag_id_rejected(client: AsyncClient):
    r = await client.post("/api/tasks", json={"title": "T", "tag_ids": [0]})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_task_duplicate_tag_ids_rejected(client: AsyncClient):
    r = await client.post("/api/tasks", json={"title": "T", "tag_ids": [1, 1]})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_task_too_many_tags_rejected(client: AsyncClient):
    r = await client.post(
        "/api/tasks", json={"title": "T", "tag_ids": list(range(1, 52))}
    )
    assert r.status_code == 422


# ── Category ID validation ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_task_negative_category_id_rejected(client: AsyncClient):
    r = await client.post("/api/tasks", json={"title": "T", "category_id": -1})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_task_zero_category_id_rejected(client: AsyncClient):
    r = await client.post("/api/tasks", json={"title": "T", "category_id": 0})
    assert r.status_code == 422


# ── PATCH validation ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_patch_title_html_rejected(client: AsyncClient):
    r = await client.post("/api/tasks", json={"title": "OK"})
    tid = r.json()["id"]
    r2 = await client.patch(f"/api/tasks/{tid}", json={"title": "<script>x</script>"})
    assert r2.status_code == 422


@pytest.mark.asyncio
async def test_patch_description_script_rejected(client: AsyncClient):
    r = await client.post("/api/tasks", json={"title": "OK"})
    tid = r.json()["id"]
    r2 = await client.patch(
        f"/api/tasks/{tid}", json={"description": "<script>evil()</script>"}
    )
    assert r2.status_code == 422


# ── SQL injection in various search endpoints ────────────────────────────────

@pytest.mark.asyncio
async def test_search_sqli_tasks(client: AsyncClient):
    r = await client.get("/api/tasks/search", params={"q": "' OR 1=1 --"})
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_search_sqli_categories(client: AsyncClient):
    r = await client.get("/api/categories", params={"q": "'; DROP TABLE categories;--"})
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_search_sqli_tags(client: AsyncClient):
    r = await client.get("/api/tags", params={"q": "'; DROP TABLE tags;--"})
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_search_sqli_list_tasks(client: AsyncClient):
    r = await client.get("/api/tasks", params={"q": "' UNION SELECT * FROM app_settings--"})
    assert r.status_code == 200
