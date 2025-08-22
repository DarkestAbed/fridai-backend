# GPL-3.0-only
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import get_session

async def get_db(session: AsyncSession = Depends(get_session)):
    return session
