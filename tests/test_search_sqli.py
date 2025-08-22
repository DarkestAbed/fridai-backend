import pytest
from httpx import AsyncClient
from app.main import app
from app.db import init_models

@pytest.mark.asyncio
async def test_search_injection_safe():
    await init_models()
    async with AsyncClient(app=app, base_url="http://test") as ac:
        await ac.post("/api/tasks", json={"title":"Hello","description":"world"})
        # Attempt to inject
        r = await ac.get("/api/tasks/search", params={"q":"%'; DROP TABLE tasks; --"})
        assert r.status_code == 200
        # Should still be able to list tasks
        r2 = await ac.get("/api/tasks")
        assert r2.status_code == 200
