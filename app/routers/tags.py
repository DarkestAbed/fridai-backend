# app/routrs/tags.py

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError, DatabaseError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from typing import List, Optional

from app.dependencies import get_db
from app.limiter import limiter
from app.models import Tag, Task, TaskTags, StatusEnum
from app.schemas import TagCreate, TagOut, TaskOut


router = APIRouter()


@router.post("", response_model=TagOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
async def create_tag(request: Request, body: TagCreate, db: AsyncSession = Depends(get_db)):
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
@limiter.limit("120/minute")
async def list_tags(
    request: Request,
    q: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Tag).order_by(Tag.name.asc())
    if q:
        # portable case-insensitive search
        stmt = stmt.where(func.lower(Tag.name).like(f"%{q.lower()}%"))
    rows = (await db.execute(stmt)).scalars().all()
    return [ TagOut.model_validate(x, from_attributes=True) for x in rows ]


@router.get("/{tag_id}/tasks", response_model=List[TaskOut])
@limiter.limit("120/minute")
async def tasks_by_tag(
    request: Request,
    tag_id: int,
    show_completed: bool = True,
    db: AsyncSession = Depends(get_db)
):
    stmt = (
        select(Task)
        .join(Task.tags)
        .where(Tag.id == tag_id)
        .options(selectinload(Task.tags))  # avoid N+1 when serializing
        .order_by(Task.due_at.asc().nulls_last())
    )
    if not show_completed:
        stmt = stmt.where(Task.status != StatusEnum.completed)
    rows = (await db.execute(stmt)).scalars().all()
    return [ TaskOut.model_validate(x, from_attributes=True) for x in rows ]


@router.delete("/{tag_id}", status_code=status.HTTP_200_OK)
@limiter.limit("30/minute")
async def delete_tag(
    request: Request,
    tag_id: int,
    force: bool = False,
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a tag with proper validation.
    """
    try:
        # Fetch the tag with tasks relationship
        tag = (
            await db.execute(
                select(Tag)
                .where(Tag.id == tag_id)
                .options(selectinload(Tag.tasks))
            )
        ).scalar_one_or_none()
        if not tag:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tag with ID {tag_id} not found"
            )
        # Count associated tasks
        task_count_stmt = (
            select(func.count(TaskTags.task_id))
            .where(TaskTags.tag_id == tag_id)
        )
        task_count = (await db.execute(task_count_stmt)).scalar() or 0
        # Check pending tasks with this tag
        pending_tasks_stmt = (
            select(func.count(Task.id))
            .join(Task.tags)
            .where(Tag.id == tag_id)
            .where(Task.status == StatusEnum.pending)
        )
        pending_count = (await db.execute(pending_tasks_stmt)).scalar() or 0
        # Safety check: prevent deletion if tag has tasks and force not specified
        if task_count > 0 and not force:
            details: str = (
                f"Tag is associated with {task_count} tasks ({pending_count} pending). "
                f"Use force=true to remove tag from all tasks"
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=details
            )
        # Store tag info for response
        tag_info = {
            "id": tag.id,
            "name": tag.name,
            "task_count": task_count,
            "pending_task_count": pending_count,
            "removed_from_tasks": task_count if force else 0
        }
        # Delete the tag (cascade will handle TaskTags relationships)
        await db.delete(tag)
        await db.commit()
        return {
            "message": "Tag deleted successfully",
            "deleted_tag": tag_info
        }
    except HTTPException:
        await db.rollback()
        raise
    except DatabaseError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete tag due to database error"
        )
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while deleting the tag"
        )
