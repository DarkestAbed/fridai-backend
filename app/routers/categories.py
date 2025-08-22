# app/routers/categories.py

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.dependencies import get_db
from app.models import Category, Task, StatusEnum
from app.schemas import CategoryCreate, CategoryOut, TaskOut


router = APIRouter()


@router.post("", response_model=CategoryOut)
async def create_category(
    body: CategoryCreate,
    db: AsyncSession = Depends(get_db),
):
    c = Category(name=body.name)
    db.add(c)
    await db.commit()
    await db.refresh(c)
    return CategoryOut.model_validate(c, from_attributes=True)


@router.get("", response_model=List[CategoryOut])
async def list_categories(
    q: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Category)
    if q:
        stmt = stmt.where(Category.name.like(f"%{q}%"))
    rows = (await db.execute(stmt)).scalars().all()
    return [ CategoryOut.model_validate(x, from_attributes=True) for x in rows ]


@router.get("/{category_id}/tasks", response_model=List[TaskOut])
async def tasks_by_category(
    category_id: int,
    show_completed: bool = True,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Task).where(Task.category_id==category_id)
    if not show_completed:
        stmt = stmt.where(Task.status != StatusEnum.completed)
    rows = (await db.execute(stmt)).scalars().all()
    return [ TaskOut.model_validate(x, from_attributes=True) for x in rows ]
