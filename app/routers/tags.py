# app/routrs/tags.py

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.dependencies import get_db
from app.models import Tag, Task, StatusEnum
from app.schemas import TagCreate, TagOut, TaskOut


router = APIRouter()


@router.post("", response_model=TagOut, status_code=status.HTTP_201_CREATED)
async def create_tag(body: TagCreate, db: AsyncSession = Depends(get_db)):
    t = Tag(name=body.name)
    db.add(t)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Tag with that name already exists",
        )
    await db.refresh(t)
    return TagOut.model_validate(t, from_attributes=True)


@router.get("", response_model=List[TagOut])
async def list_tags(
    q: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Tag).order_by(Tag.name.asc())
    if q:
        # portable case-insensitive search
        from sqlalchemy import func
        stmt = stmt.where(func.lower(Tag.name).like(f"%{q.lower()}%"))
    rows = (await db.execute(stmt)).scalars().all()
    return [ TagOut.model_validate(x, from_attributes=True) for x in rows ]


@router.get("/{tag_id}/tasks", response_model=List[TaskOut])
async def tasks_by_tag(
    tag_id: int,
    show_completed: bool = True,
    db: AsyncSession = Depends(get_db)
):
    stmt = (
        select(Task)
        .join(Task.tags)
        .where(Task.id == tag_id)
        .options(selectinload(Task.tags))  # avoid N+1 when serializing
        .order_by(Task.due_at.asc().nulls_last())
    )
    if not show_completed:
        stmt = stmt.where(Task.status != StatusEnum.completed)
    rows = (await db.execute(stmt)).scalars().all()
    return [ TaskOut.model_validate(x, from_attributes=True) for x in rows ]
