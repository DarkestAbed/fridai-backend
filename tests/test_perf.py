import pytest, asyncio
from httpx import AsyncClient
from app.main import app
from app.db import init_models

@pytest.mark.asyncio
async def test_perf_200_tasks():
    await init_models()
    async with AsyncClient(app=app, base_url="http://test") as ac:
        for i in range(200):
            await ac.post("/api/tasks", json={"title":f"T{i}"})
        r = await ac.get("/api/tasks")
        assert r.status_code == 200
        assert len(r.json()) >= 200
