"""Exception handlers for shared / cross-cutting exceptions (404, 500)."""

from fastapi import Request
from fastapi.responses import JSONResponse

from app.domain.shared.exceptions import DomainException, SessionNotFound
from app.schemas.common import ErrorResponse


async def session_not_found_handler(
    request: Request, exc: SessionNotFound
) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content=ErrorResponse(code="session_not_found", message=str(exc)).model_dump(),
    )


async def domain_exception_handler(
    request: Request, exc: DomainException
) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(code="internal_error", message=str(exc)).model_dump(),
    )


def register(app):
    app.add_exception_handler(SessionNotFound, session_not_found_handler)
    app.add_exception_handler(DomainException, domain_exception_handler)
