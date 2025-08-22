# GPL-3.0-only
from typing import List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..dependencies import get_db
from ..models import Tag, Task, StatusEnum, task_tags
from ..schemas import TagCreate, TagOut, TaskOut

router = APIRouter()

@router.post("", response_model=TagOut)
async def create_tag(body: TagCreate, db: AsyncSession = Depends(get_db)):
    t = Tag(name=body.name)
    db.add(t)
    await db.commit()
    await db.refresh(t)
    return TagOut.model_validate(t, from_attributes=True)

@router.get("", response_model=List[TagOut])
async def list_tags(q: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    stmt = select(Tag)
    if q:
        stmt = stmt.where(Tag.name.like(f"%{q}%"))
    rows = (await db.execute(stmt)).scalars().all()
    return [TagOut.model_validate(x, from_attributes=True) for x in rows]

@router.get("/{tag_id}/tasks", response_model=List[TaskOut])
async def tasks_by_tag(tag_id: int, show_completed: bool = True, db: AsyncSession = Depends(get_db)):
    stmt = select(Task).join(task_tags, task_tags.c.task_id==Task.id).where(task_tags.c.tag_id==tag_id)
    if not show_completed:
        stmt = stmt.where(Task.status != StatusEnum.completed)
    rows = (await db.execute(stmt)).scalars().all()
    return [TaskOut.model_validate(x, from_attributes=True) for x in rows]
