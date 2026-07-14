"""Exception handlers for document domain (403, 404, 502)."""

from fastapi import Request
from fastapi.responses import JSONResponse

from app.domain.documents.exceptions import (
    AgentServiceUnavailable,
    DocumentNotBelongToAgent,
    DocumentNotFound,
)
from app.schemas.common import ErrorResponse


async def document_not_found_handler(
    request: Request, exc: DocumentNotFound
) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content=ErrorResponse(code="document_not_found", message=str(exc)).model_dump(),
    )


async def document_not_belong_to_agent_handler(
    request: Request, exc: DocumentNotBelongToAgent
) -> JSONResponse:
    return JSONResponse(
        status_code=403,
        content=ErrorResponse(
            code="document_not_belong_to_agent", message=str(exc)
        ).model_dump(),
    )


async def agent_service_unavailable_handler(
    request: Request, exc: AgentServiceUnavailable
) -> JSONResponse:
    return JSONResponse(
        status_code=502,
        content=ErrorResponse(
            code="agent_service_unavailable", message=str(exc)
        ).model_dump(),
    )


def register(app):
    app.add_exception_handler(DocumentNotFound, document_not_found_handler)
    app.add_exception_handler(
        DocumentNotBelongToAgent, document_not_belong_to_agent_handler
    )
    app.add_exception_handler(
        AgentServiceUnavailable, agent_service_unavailable_handler
    )
