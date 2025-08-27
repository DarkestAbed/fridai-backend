import asyncio, pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import engine, SessionLocal, init_models
from app.models import Task, Category

@pytest.mark.asyncio
async def test_models_create():
    await init_models()
    async with SessionLocal() as db:
        c = Category(name="Work")
        db.add(c); await db.commit(); await db.refresh(c)
        t = Task(title="Test", category_id=c.id)
        db.add(t); await db.commit(); await db.refresh(t)
        assert t.id > 0
        assert t.category_id == c.id
