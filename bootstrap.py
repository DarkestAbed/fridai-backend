# Bootstrap sample data into the platform via direct DB and API calls
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db import SessionLocal, init_models
from app.models import Category, Tag, Task

async def main():
    await init_models()
    async with SessionLocal() as db:
        # Categories
        for name in ["Work","Home","Errands"]:
            db.add(Category(name=name))
        await db.commit()
        # Tags
        for name in ["urgent","low-prio","next"]:
            db.add(Tag(name=name))
        await db.commit()
        cats = (await db.execute(select(Category))).scalars().all()
        tags = (await db.execute(select(Tag))).scalars().all()
        # Tasks
        for i in range(25):
            t = Task(title=f"Sample Task {i}", category_id=cats[i % len(cats)].id)
            if i % 2 == 0:
                t.tags = [tags[0]]
            db.add(t)
        await db.commit()
    print("Bootstrap complete")
if __name__ == "__main__":
    asyncio.run(main())
