# GPL-3.0-only
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..dependencies import get_db
from ..models import TaskRelationship
from ..schemas import RelationshipCreate

router = APIRouter()

@router.post("")
async def create_relationship(body: RelationshipCreate, db: AsyncSession = Depends(get_db)):
    rel = TaskRelationship(task_id=body.task_id, related_task_id=body.related_task_id, rel_type=body.rel_type)
    db.add(rel)
    await db.commit()
    await db.refresh(rel)
    return {"ok": True, "id": rel.id}

@router.get("")
async def list_relationships(task_id: int, db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(TaskRelationship).where(TaskRelationship.task_id==task_id))).scalars().all()
    return [{"id": r.id, "related_task_id": r.related_task_id, "rel_type": r.rel_type} for r in rows]
