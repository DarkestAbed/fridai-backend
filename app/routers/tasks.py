# app/routers/tasks.py

from __future__ import annotations
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pendulum import now
from sqlalchemy import func, select, and_, or_
from sqlalchemy.exc import IntegrityError, DatabaseError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.dependencies import get_db
from app.models import Category, Task, Tag, StatusEnum
from app.schemas import (
    TaskCreate,
    TaskOut,
    TaskPatchDescription,
    TaskPatchDue,
    AddTags,
)
from app.utils.datetime_converter import datetime_to_pendulum, verify_timestamp


router = APIRouter()


@router.post("", response_model=TaskOut)
async def create_task(body: TaskCreate, db: AsyncSession = Depends(get_db)):
    """Create a new task with comprehensive validation and error handling."""
    # Input validation
    if not body.title or not body.title.strip():
        raise HTTPException(400, "Task title cannot be empty")
    if len(body.title.strip()) > 200:
        raise HTTPException(400, "Task title too long (max 200 characters)")
    try:
        # Validate category exists if provided
        if body.category_id:
            category = (await db.execute(
                select(Category).where(Category.id == body.category_id)
            )).scalar_one_or_none()
            if not category:
                raise HTTPException(
                    400,
                    f"Category with ID {body.category_id} does not exist",
                )
        # Validate tags exist if provided
        valid_tags = []
        if body.tag_ids:
            tags = (await db.execute(
                select(Tag).where(Tag.id.in_(body.tag_ids))
            )).scalars().all()
            found_tag_ids = {tag.id for tag in tags}
            missing_tag_ids = set(body.tag_ids) - found_tag_ids
            if missing_tag_ids:
                raise HTTPException(
                    400,
                    f"Tags with IDs {list(missing_tag_ids)} do not exist"
                )
            valid_tags = list(tags)        
        # Convert datetime to Pendulum for database storage
        due_at_pendulum = (
            datetime_to_pendulum(body.due_at)
            if body.due_at
            else None
        )
        # Create task
        t = Task(
            title=body.title.strip(),
            description=body.description.strip() if body.description else None,
            due_at=due_at_pendulum,  # Use converted Pendulum datetime
            category_id=body.category_id,
        )
        if valid_tags:
            t.tags = valid_tags
        db.add(t)
        await db.commit()
        # Ensure relationships are loaded for serialization
        await db.refresh(t, ["tags", "category"])
        return TaskOut.model_validate(t, from_attributes=True)
    except HTTPException:
        # Re-raise validation errors
        await db.rollback()
        raise
    except IntegrityError as e:
        await db.rollback()
        error_msg = str(e.orig)
        if "FOREIGN KEY constraint failed" in error_msg:
            raise HTTPException(400, "Invalid category or tag reference")
        else:
            raise HTTPException(400, "Data validation error")
    except DatabaseError as e:
        await db.rollback()
        raise HTTPException(500, "Database operation failed")
    except Exception as e:
        await db.rollback()
        raise HTTPException(500, "Internal server error")


@router.delete("/{task_id}", status_code=status.HTTP_200_OK)
async def delete_task(
    task_id: int,
    force: bool = False,
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a task with proper validation and cascade handling.
    """
    try:
        # Fetch task with all relationships for response
        stmt = (
            select(Task)
            .where(Task.id == task_id)
            .options(
                selectinload(Task.tags),
                selectinload(Task.category),
                selectinload(Task.attachments)
            )
        )
        t = (await db.execute(stmt)).scalar_one_or_none()
        if not t:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task with ID {task_id} not found"
            )
        # Safety check: only delete completed tasks unless forced
        if not force and t.status != StatusEnum.completed:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot delete uncompleted task. Mark as completed first or use force=true"
            )
        # Store task info before deletion for response
        task_info = {
            "id": t.id,
            "title": t.title,
            "status": t.status.value,
            "had_attachments": len(t.attachments) > 0,
            "attachment_count": len(t.attachments),
            "had_tags": len(t.tags) > 0,
            "tag_count": len(t.tags)
        }
        # Delete the task (cascades will handle relationships and attachments)
        await db.delete(t)
        await db.commit()
        return {
            "message": "Task deleted successfully",
            "deleted_task": task_info
        }
    except HTTPException:
        await db.rollback()
        raise
    except DatabaseError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete task due to database error"
        )
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while deleting the task"
        )


@router.post("/{task_id}/complete", response_model=TaskOut)
async def complete_task(task_id: int, db: AsyncSession = Depends(get_db)):
    """Complete/un-complete task"""
    t = (
        (await db.execute(select(Task).where(Task.id==task_id)))
        .scalar_one_or_none()
    )
    if not t:
        raise HTTPException(404, "Task not found")
    if t.status == StatusEnum.pending:
        t.status = StatusEnum.completed
    elif t.status == StatusEnum.completed:
        t.status = StatusEnum.pending
    else:
        raise HTTPException(404, "Task status not found")
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
    """Set task due date, or nullify it"""
    t = (
        (await db.execute(select(Task).where(Task.id==task_id)))
        .scalar_one_or_none()
    )
    if not t:
        raise HTTPException(404, "Task not found")
    # Convert datetime to Pendulum for database storage
    ## check if input timestamp is valid
    check_ts_fg: bool = verify_timestamp(str(body.due_at))
    ## proper due date update
    if check_ts_fg:
        t.due_at = datetime_to_pendulum(body.due_at) if body.due_at else None
    else:
        raise HTTPException(400, "Wrong input timestamp value")
    await db.commit()
    await db.refresh(t)
    # print(f"{t = }\n{TaskOut.model_validate(t, from_attributes=True) = }")
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
    print(f"{tags = }")
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
        pattern = f"%{q.lower()}%"
        filters.append(
            or_(
                func.lower(Task.title).like(pattern),
                func.lower(Task.description).like(pattern),
            )
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
    if days is None and hours is None:  # Fixed condition
        raise HTTPException(400, "Must specify either days or hours")  # Fixed status code
    # Calculate horizon based on provided parameters
    if hours is not None:
        horizon = now_ts.add(hours=hours)
    elif days is not None:
        horizon = now_ts.add(days=days)
    else:
        # This shouldn't happen, but handle it gracefully
        horizon = now_ts.add(hours=48)  # Default fallback
    # exec
    stmt = (
        select(Task)
        .where(Task.due_at.is_not(None))
        .where(Task.due_at <= horizon)
        .where(Task.status != StatusEnum.completed)  # Don't show completed tasks
        .order_by(Task.due_at.asc())
    )
    rows = (await db.execute(stmt)).scalars().all()
    return [ TaskOut.model_validate(x, from_attributes=True) for x in rows ]
