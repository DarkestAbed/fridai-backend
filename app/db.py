# GPL-3.0-only
import os, asyncio
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./data/app.db")

engine = create_async_engine(DATABASE_URL, echo=False, pool_pre_ping=True, future=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session

async def init_models():
    from . import models
    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)

async def enable_sqlite_wal():
    if DATABASE_URL.startswith("sqlite"):
        async with engine.begin() as conn:
            await conn.execute(text("PRAGMA journal_mode=WAL;"))
