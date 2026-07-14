"""Exception handlers for use case domain (404)."""

from fastapi import Request
from fastapi.responses import JSONResponse

from app.domain.use_cases.exceptions import UseCaseNotFound
from app.schemas.common import ErrorResponse


async def use_case_not_found_handler(
    request: Request, exc: UseCaseNotFound
) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content=ErrorResponse(code="use_case_not_found", message=str(exc)).model_dump(),
    )


def register(app):
    app.add_exception_handler(UseCaseNotFound, use_case_not_found_handler)
