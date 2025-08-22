# app/routers/views.py

from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.models import Task, Category, Tag
from app.schemas import CountItem


router = APIRouter()


@router.get("/categories-summary", response_model=List[CountItem])
async def categories_summary(db: AsyncSession = Depends(get_db)):
    stmt = (
        select(Category.name, func.count(Task.id))
        .join(Task, isouter=True)
        .group_by(Category.id)
    )
    rows = (await db.execute(stmt)).all()
    return [ 
        CountItem(key=name or "Uncategorized", count=count) 
        for name, count in rows
        ]

@router.get("/status-summary", response_model=List[CountItem])
async def status_summary(db: AsyncSession = Depends(get_db)):
    stmt = select(Task.status, func.count(Task.id)).group_by(Task.status)
    rows = (await db.execute(stmt)).all()
    return [
        CountItem(key=status.value if hasattr(status, "value") 
                    else status, count=count)
                    for status, count in rows
    ]

@router.get("/tags-summary", response_model=List[CountItem])
async def tags_summary(db: AsyncSession = Depends(get_db)):
    stmt = (
        select(Tag.name, func.count(task_tags.c.task_id))
        .join(task_tags, task_tags.c.tag_id==Tag.id, isouter=True)
        .group_by(Tag.id)
    )
    rows = (await db.execute(stmt)).all()
    return [ CountItem(key=name, count=count) for name, count in rows ]
