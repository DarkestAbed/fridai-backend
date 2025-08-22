# app/routers/tasks.py

from __future__ import annotations
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pendulum import now
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.models import Task, Tag, StatusEnum
from app.schemas import (
    TaskCreate,
    TaskOut,
    TaskPatchDescription,
    TaskPatchDue,
    AddTags,
)


router = APIRouter()


@router.post("", response_model=TaskOut)
async def create_task(body: TaskCreate, db: AsyncSession = Depends(get_db)):
    t = Task(
        title=body.title,
        description=body.description,
        due_at=body.due_at,
        category_id=body.category_id,
    )
    if body.tag_ids:
        tags = (
            (await db.execute(select(Tag).where(Tag.id.in_(body.tag_ids))))
            .scalars()
            .all()
        )
        t.tags = list(tags)
    db.add(t)
    await db.commit()
    await db.refresh(t)
    # Ensure the tags relationship is loaded
    await db.refresh(t, ["tags"])
    # Use consistent model validation instead of manual construction
    return TaskOut.model_validate(t, from_attributes=True)


@router.delete("/{task_id}")
async def delete_task(task_id: int, db: AsyncSession = Depends(get_db)):
    t = (
        (await db.execute(select(Task).where(Task.id==task_id)))
        .scalar_one_or_none()
    )
    if not t:
        raise HTTPException(404, "Task not found")
    await db.delete(t)
    await db.commit()
    return {
        "ok": True,
    }


@router.post("/{task_id}/complete", response_model=TaskOut)
async def complete_task(task_id: int, db: AsyncSession = Depends(get_db)):
    t = (
        (await db.execute(select(Task).where(Task.id==task_id)))
        .scalar_one_or_none()
    )
    if not t:
        raise HTTPException(404, "Task not found")
    t.status = StatusEnum.completed
    await db.commit()
    await db.refresh(t)
    return TaskOut.model_validate(t, from_attributes=True)


@router.patch("/{task_id}/description", response_model=TaskOut)
async def set_description(
    task_id: int,
    body: TaskPatchDescription,
    db: AsyncSession = Depends(get_db),
):
    t = (
        (await db.execute(select(Task).where(Task.id==task_id)))
        .scalar_one_or_none()
    )
    if not t:
        raise HTTPException(404, "Task not found")
    t.description = body.description
    await db.commit()
    await db.refresh(t)
    return TaskOut.model_validate(t, from_attributes=True)


@router.patch("/{task_id}/due", response_model=TaskOut)
async def set_due(
    task_id: int,
    body: TaskPatchDue,
    db: AsyncSession = Depends(get_db),
):
    t = (
        (await db.execute(select(Task).where(Task.id==task_id)))
        .scalar_one_or_none()
    )
    if not t:
        raise HTTPException(404, "Task not found")
    t.due_at = body.due_at
    await db.commit()
    await db.refresh(t)
    return TaskOut.model_validate(t, from_attributes=True)


@router.post("/{task_id}/tags")
async def add_tags(
    task_id: int,
    body: AddTags,
    db: AsyncSession = Depends(get_db),
):
    t = (
        (await db.execute(select(Task).where(Task.id==task_id)))
        .scalar_one_or_none()
    )
    if not t:
        raise HTTPException(404, "Task not found")
    tags = (
        (await db.execute(select(Tag).where(Tag.id.in_(body.tag_ids))))
        .scalars()
        .all()
    )
    for tg in tags:
        if tg not in t.tags:
            t.tags.append(tg)
    await db.commit()
    return {
        "ok": True,
        "tag_ids": [ x.id for x in t.tags ],
    }


@router.get("", response_model=List[TaskOut])
async def list_tasks(
    q: Optional[str] = None,
    tag: Optional[int] = None,
    overdue_only: bool = False,
    category: Optional[int] = None,
    status: Optional[StatusEnum] = None,
    db: AsyncSession = Depends(get_db)
):
    stmt = (
        select(Task)
        .order_by(Task.due_at.is_(None), Task.due_at.asc().nulls_last())
    )
    filters = []
    if q:
        pattern = f"%{q}%"
        filters.append(
            or_(Task.title.like(pattern), Task.description.like(pattern))
        )
    if overdue_only:
        now_ts = now("America/Santiago")
        filters.append(Task.due_at.is_not(None))
        filters.append(Task.due_at < now_ts)
    if category:
        filters.append(Task.category_id == category)
    if status:
        filters.append(Task.status == status)
    if filters:
        stmt = stmt.where(and_(*filters))
    if tag:
        stmt = stmt.join(Task.tags).where(Tag.id == tag)
    rows = (await db.execute(stmt)).scalars().all()
    return [ TaskOut.model_validate(x, from_attributes=True) for x in rows ]


@router.get("/all", response_model=List[TaskOut])
async def list_all(
    q: Optional[str] = None,
    tag: Optional[int] = None,
    overdue_only: bool = False,
    db: AsyncSession = Depends(get_db)
):
    return await list_tasks(q=q, tag=tag, overdue_only=overdue_only, db=db)  # same filters


@router.get("/search", response_model=List[TaskOut])
async def search(q: str, db: AsyncSession = Depends(get_db)):
    pattern = f"%{q}%"
    stmt = (
        select(Task)
        .where(or_(Task.title.like(pattern), Task.description.like(pattern)))
    )
    rows = (await db.execute(stmt)).scalars().all()
    return [ TaskOut.model_validate(x, from_attributes=True) for x in rows ]


@router.get("/next", response_model=List[TaskOut])
async def next_window(
    days: Optional[int] = None,
    hours: Optional[int] = 48,
    db: AsyncSession = Depends(get_db),
):
    now_ts = now("America/Santiago")
    if days is None:
        if hours is None:
            return HTTPException(
                status_code=401,
                detail="Missing time differences",
            )
    horizon = (
        now_ts
        .add(hours=hours) if hours is not None else now_ts.add(days=days)   # type: ignore
    )
    stmt = (
        select(Task)
        .where(Task.due_at.is_not(None))
        .where(Task.due_at <= horizon)
        .order_by(Task.due_at.asc())
    )
    rows = (await db.execute(stmt)).scalars().all()
    return [ TaskOut.model_validate(x, from_attributes=True) for x in rows ]
