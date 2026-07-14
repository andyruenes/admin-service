"""Exception handlers for agent domain (404, 409, 422)."""

from fastapi import Request
from fastapi.responses import JSONResponse

from app.domain.agents.exceptions import (
    AgentAlreadyExists,
    AgentIsActive,
    AgentNotFound,
    InvalidStatusTransition,
    PhoneAccountAlreadyLinked,
    PhoneAccountNotLinked,
)
from app.schemas.common import ErrorResponse


async def agent_not_found_handler(request: Request, exc: AgentNotFound) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content=ErrorResponse(code="agent_not_found", message=str(exc)).model_dump(),
    )


async def agent_already_exists_handler(
    request: Request, exc: AgentAlreadyExists
) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content=ErrorResponse(
            code="agent_already_exists", message=str(exc)
        ).model_dump(),
    )


async def agent_is_active_handler(request: Request, exc: AgentIsActive) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content=ErrorResponse(code="agent_is_active", message=str(exc)).model_dump(),
    )


async def invalid_status_transition_handler(
    request: Request, exc: InvalidStatusTransition
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content=ErrorResponse(
            code="invalid_status_transition", message=str(exc)
        ).model_dump(),
    )


async def phone_account_not_linked_handler(
    request: Request, exc: PhoneAccountNotLinked
) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content=ErrorResponse(
            code="phone_account_not_linked", message=str(exc)
        ).model_dump(),
    )


async def phone_account_already_linked_handler(
    request: Request, exc: PhoneAccountAlreadyLinked
) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content=ErrorResponse(
            code="phone_account_already_linked", message=str(exc)
        ).model_dump(),
    )


def register(app):
    app.add_exception_handler(AgentNotFound, agent_not_found_handler)
    app.add_exception_handler(AgentAlreadyExists, agent_already_exists_handler)
    app.add_exception_handler(AgentIsActive, agent_is_active_handler)
    app.add_exception_handler(
        InvalidStatusTransition, invalid_status_transition_handler
    )
    app.add_exception_handler(
        PhoneAccountAlreadyLinked, phone_account_already_linked_handler
    )
    app.add_exception_handler(PhoneAccountNotLinked, phone_account_not_linked_handler)
