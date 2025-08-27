# app/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.encoders import jsonable_encoder
from json import JSONEncoder
from pendulum import DateTime
from sqlalchemy.exc import IntegrityError, DatabaseError
from uvicorn import run as server_run

from app.db import init_models, enable_sqlite_wal
from app.exceptions import DatabaseExceptionHandler
from app.routers import (
    tasks,
    categories,
    tags,
    relationships,
    attachments,
    views,
    notifications,
    config,
)
from app.settings import settings_cache


class CustomJSONEncoder(JSONEncoder):
    """Custom JSON encoder to handle Pendulum DateTime objects."""
    def default(self, o):
        if isinstance(o, DateTime):
            return o.isoformat()
        return super().default(o)


app = FastAPI(title="Tasks Platform API", version="2.0.0-vibe")

# Register exception handlers
app.add_exception_handler(IntegrityError, DatabaseExceptionHandler.integrity_error_handler)
app.add_exception_handler(DatabaseError, DatabaseExceptionHandler.database_error_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # single-user demo; tighten if needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def on_startup():
    await enable_sqlite_wal()
    await init_models()
    await settings_cache.load()


# Routers
app.include_router(tasks.router, prefix="/api/tasks", tags=["tasks"])
app.include_router(categories.router, prefix="/api/categories", tags=["categories"])
app.include_router(tags.router, prefix="/api/tags", tags=["tags"])
app.include_router(relationships.router, prefix="/api/relationships", tags=["relationships"])
app.include_router(attachments.router, prefix="/api/tasks", tags=["attachments"])
app.include_router(views.router, prefix="/api/views", tags=["views"])
app.include_router(notifications.router, prefix="/api/notifications", tags=["notifications"])
app.include_router(config.router, prefix="/api/config", tags=["config"])


@app.get("/")
async def hello():
    return {"msg": "Hello, friend. Hello, friend?"}


@app.get("/healthz")
async def healthz():
    return {"ok": True, "version": "2.0.0-vibe"}


if __name__ == "__main__":
    # server_run(
    #     "app.main:app",
    #     host="0.0.0.0",
    #     port=8000,
    #     debug=True,
    # )
    pass
else:
    pass
