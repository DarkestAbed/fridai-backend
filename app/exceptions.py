# app/exceptions.py - Create custom exception handlers

from fastapi import Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, DatabaseError


class DatabaseExceptionHandler:
    """Centralized database exception handling."""    
    @staticmethod
    async def integrity_error_handler(
        request: Request,
        exc: IntegrityError,
    ) -> JSONResponse:
        """Handle database integrity constraint violations."""
        error_msg = str(exc.orig)
        # Parse common constraint violations
        if "UNIQUE constraint failed" in error_msg:
            if "categories.name" in error_msg:
                return JSONResponse(
                    status_code=409,
                    content={
                        "detail": "A category with this name already exists"
                    }
                )
            elif "tags.name" in error_msg:
                return JSONResponse(
                    status_code=409,
                    content={"detail": "A tag with this name already exists"}
                )
            else:
                return JSONResponse(
                    status_code=409,
                    content={"detail": "This record already exists"}
                )    
        elif "FOREIGN KEY constraint failed" in error_msg:
            return JSONResponse(
                status_code=400,
                content={"detail": "Referenced record does not exist"}
            )
        elif "NOT NULL constraint failed" in error_msg:
            return JSONResponse(
                status_code=400,
                content={"detail": "Required field is missing"}
            )
        # Generic integrity error
        return JSONResponse(
            status_code=400,
            content={"detail": "Data validation error"}
        )
    
    @staticmethod
    async def database_error_handler(request: Request, exc: DatabaseError) -> JSONResponse:
        """Handle general database errors."""
        return JSONResponse(
            status_code=500,
            content={"detail": "Database operation failed"}
        )
