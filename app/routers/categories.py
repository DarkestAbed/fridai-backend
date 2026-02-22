# app/routers/categories.py

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError, DatabaseError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from typing import List, Optional

from app.dependencies import get_db
from app.limiter import limiter
from app.models import Category, Task, StatusEnum
from app.schemas import CategoryCreate, CategoryOut, TaskOut


router = APIRouter()


@router.post("", response_model=CategoryOut)
@limiter.limit("30/minute")
async def create_category(
    request: Request,
    body: CategoryCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new category with comprehensive error handling."""
    # Validate input
    if not body.name or not body.name.strip():
        raise HTTPException(400, "Category name cannot be empty")
    if len(body.name.strip()) > 100:
        raise HTTPException(400, "Category name too long (max 100 characters)")
    c = Category(name=body.name.strip())
    db.add(c)
    try:
        await db.commit()
        await db.refresh(c)
        return CategoryOut.model_validate(c, from_attributes=True)
    except IntegrityError as e:
        await db.rollback()
        error_msg = str(e.orig)
        if "UNIQUE constraint failed" in error_msg:
            raise HTTPException(
                status_code=409,
                detail="A category with this name already exists"
            )
        else:
            raise HTTPException(
                status_code=400,
                detail="Invalid category data"
            )
    except DatabaseError as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Database operation failed"
        )
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )


@router.get("", response_model=List[CategoryOut])
@limiter.limit("120/minute")
async def list_categories(
    request: Request,
    q: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """List categories with error handling."""
    try:
        stmt = select(Category).order_by(Category.name)
        if q:
            stmt = stmt.where(Category.name.ilike(f"%{q.strip()}%"))
        rows = (await db.execute(stmt)).scalars().all()
        return [
            CategoryOut.model_validate(x, from_attributes=True)
            for x in rows
        ]
    except DatabaseError as e:
        raise HTTPException(500, "Failed to retrieve categories")


@router.get("/{category_id}/tasks", response_model=List[TaskOut])
@limiter.limit("120/minute")
async def tasks_by_category(
    request: Request,
    category_id: int,
    show_completed: bool = True,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Task).where(Task.category_id==category_id)
    if not show_completed:
        stmt = stmt.where(Task.status != StatusEnum.completed)
    rows = (await db.execute(stmt)).scalars().all()
    return [ TaskOut.model_validate(x, from_attributes=True) for x in rows ]


@router.delete("/{category_id}", status_code=status.HTTP_200_OK)
@limiter.limit("30/minute")
async def delete_category(
    request: Request,
    category_id: int,
    reassign_to: Optional[int] = None,
    force: bool = False,
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a category with proper validation and task handling.
    """
    try:
        # Fetch the category to delete
        category = (
            await db.execute(
                select(Category)
                .where(Category.id == category_id)
                .options(selectinload(Category.tasks))
            )
        ).scalar_one_or_none()
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Category with ID {category_id} not found"
            )
        # Count associated tasks
        task_count_stmt = (
            select(func.count(Task.id))
            .where(Task.category_id == category_id)
        )
        task_count = (await db.execute(task_count_stmt)).scalar() or 0
        # Check if category has tasks and no resolution strategy provided
        if task_count > 0 and not reassign_to and not force:
            details: str = (
                f"Category has {task_count} associated tasks. "
                f"Specify reassign_to category ID or use force=true to set tasks category to NULL"
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=details,
            )
        # If reassigning, validate the target category exists and is different
        if reassign_to is not None:
            if reassign_to == category_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot reassign to the same category being deleted"
                )
                
            target_category = (
                await db.execute(
                    select(Category).where(Category.id == reassign_to)
                )
            ).scalar_one_or_none()
            
            if not target_category:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Target category with ID {reassign_to} not found"
                )
            # Reassign all tasks to the target category
            if task_count > 0:
                update_stmt = (
                    select(Task).where(Task.category_id == category_id)
                )
                tasks_to_update = (await db.execute(update_stmt)).scalars().all()
                for task in tasks_to_update:
                    task.category = target_category
                await db.flush()
        # Store category info for response
        category_info = {
            "id": category.id,
            "name": category.name,
            "task_count": task_count,
            "tasks_reassigned_to": reassign_to if reassign_to else None,
            "tasks_set_to_null": task_count > 0 and force and not reassign_to
        }
        # Delete the category (tasks will be set to NULL due to SET NULL constraint if force=true)
        await db.delete(category)
        await db.commit()
        return {
            "message": "Category deleted successfully",
            "deleted_category": category_info
        }
    except HTTPException:
        await db.rollback()
        raise
    except DatabaseError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete category due to database error"
        )
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while deleting the category"
        )
