"""Exception handlers for prompt domain (404, 409)."""

from fastapi import Request
from fastapi.responses import JSONResponse

from app.domain.prompts.exceptions import (
    NoActivePrompt,
    PromptNotFound,
    PromptVersionConflict,
)
from app.schemas.common import ErrorResponse


async def no_active_prompt_handler(
    request: Request, exc: NoActivePrompt
) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content=ErrorResponse(code="no_active_prompt", message=str(exc)).model_dump(),
    )


async def prompt_not_found_handler(
    request: Request, exc: PromptNotFound
) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content=ErrorResponse(code="prompt_not_found", message=str(exc)).model_dump(),
    )


async def prompt_version_conflict_handler(
    request: Request, exc: PromptVersionConflict
) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content=ErrorResponse(
            code="prompt_version_conflict", message=str(exc)
        ).model_dump(),
    )


def register(app):
    app.add_exception_handler(NoActivePrompt, no_active_prompt_handler)
    app.add_exception_handler(PromptNotFound, prompt_not_found_handler)
    app.add_exception_handler(PromptVersionConflict, prompt_version_conflict_handler)
