import pytest, asyncio
from httpx import AsyncClient
from app.main import app
from app.db import init_models

@pytest.mark.asyncio
async def test_create_and_search_task():
    await init_models()
    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.post("/api/categories", json={"name": "Home"})
        assert r.status_code == 200
        cat = r.json()
        r = await ac.post("/api/tasks", json={"title":"Buy milk","category_id":cat["id"]})
        assert r.status_code == 200
        r = await ac.get("/api/tasks/search", params={"q":"milk"})
        lst = r.json()
        assert any("milk" in x["title"].lower() for x in lst)
