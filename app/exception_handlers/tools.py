"""Exception handlers for tools domain (404, 409)."""

from fastapi import Request
from fastapi.responses import JSONResponse

from app.domain.tools.exceptions import (
    AgentToolAlreadyAttached,
    AgentToolNotFound,
    ToolAlreadyExists,
    ToolNotFound,
)
from app.schemas.common import ErrorResponse


async def tool_not_found_handler(request: Request, exc: ToolNotFound) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content=ErrorResponse(code="tool_not_found", message=str(exc)).model_dump(),
    )


async def agent_tool_not_found_handler(
    request: Request, exc: AgentToolNotFound
) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content=ErrorResponse(
            code="agent_tool_not_found", message=str(exc)
        ).model_dump(),
    )


async def agent_tool_already_attached_handler(
    request: Request, exc: AgentToolAlreadyAttached
) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content=ErrorResponse(
            code="agent_tool_already_attached", message=str(exc)
        ).model_dump(),
    )


async def tool_already_exists_handler(
    request: Request, exc: ToolAlreadyExists
) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content=ErrorResponse(
            code="tool_already_exists", message=str(exc)
        ).model_dump(),
    )


def register(app):
    app.add_exception_handler(ToolNotFound, tool_not_found_handler)
    app.add_exception_handler(AgentToolNotFound, agent_tool_not_found_handler)
    app.add_exception_handler(
        AgentToolAlreadyAttached, agent_tool_already_attached_handler
    )
    app.add_exception_handler(ToolAlreadyExists, tool_already_exists_handler)
