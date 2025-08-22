# GPL-3.0-only
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..dependencies import get_db
from ..models import Category, Task
from ..schemas import CategoryCreate, CategoryOut, TaskOut

router = APIRouter()

@router.post("", response_model=CategoryOut)
async def create_category(body: CategoryCreate, db: AsyncSession = Depends(get_db)):
    c = Category(name=body.name)
    db.add(c)
    await db.commit()
    await db.refresh(c)
    return CategoryOut.model_validate(c, from_attributes=True)

@router.get("", response_model=List[CategoryOut])
async def list_categories(q: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    stmt = select(Category)
    if q:
        stmt = stmt.where(Category.name.like(f"%{q}%"))
    rows = (await db.execute(stmt)).scalars().all()
    return [CategoryOut.model_validate(x, from_attributes=True) for x in rows]

@router.get("/{category_id}/tasks", response_model=List[TaskOut])
async def tasks_by_category(category_id: int, show_completed: bool = True, db: AsyncSession = Depends(get_db)):
    stmt = select(Task).where(Task.category_id==category_id)
    if not show_completed:
        from ..models import StatusEnum
        stmt = stmt.where(Task.status != StatusEnum.completed)
    rows = (await db.execute(stmt)).scalars().all()
    return [TaskOut.model_validate(x, from_attributes=True) for x in rows]
