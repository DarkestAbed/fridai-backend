# app/routers/categories.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, DatabaseError
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
async def list_categories(
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
