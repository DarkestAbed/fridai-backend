# app/routers/relationships.py

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.limiter import limiter
from app.models import TaskRelationship
from app.schemas import RelationshipCreate


router = APIRouter()


@router.post("")
@limiter.limit("30/minute")
async def create_relationship(
    request: Request,
    body: RelationshipCreate,
    db: AsyncSession = Depends(get_db),
):
    rel = TaskRelationship(
        task_id=body.task_id,
        related_task_id=body.related_task_id,
        rel_type=body.rel_type
    )
    db.add(rel)
    await db.commit()
    await db.refresh(rel)
    return {"ok": True, "id": rel.id}


@router.get("")
@limiter.limit("120/minute")
async def list_relationships(request: Request, task_id: int, db: AsyncSession = Depends(get_db)):
    rows = (
        (
            await db.execute(
                select(TaskRelationship)
                .where(TaskRelationship.task_id==task_id)
            )
        )
        .scalars()
        .all()
    )
    return [
        {
            "id": r.id,
            "related_task_id": r.related_task_id,
            "rel_type": r.rel_type
        }
        for r in rows
    ]
