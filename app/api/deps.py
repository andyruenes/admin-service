"""Composition root — wires repositories and services for FastAPI DI.

This module is the seam between infrastructure (SQL repos + AsyncSession) and
application services. Routers depend on services only; they must not import
concrete repositories. Session is injected once per request via get_session and
passed to both repo and service so commits in the service use the same tx.
"""

from typing import Any

import httpx
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.session import get_session
from app.domain.shared.exceptions import SessionNotFound
from app.grpc.hermes.client import HermesClient
from app.repositories.agents import SQLAgentRepository
from app.repositories.documents import SQLDocumentRepository
from app.repositories.prompts import SQLPromptRepository
from app.repositories.tools import SQLToolRepository
from app.repositories.use_cases import SQLUseCaseRepository
from app.services.agents import AgentService
from app.services.conversations import ConversationService
from app.services.documents import DocumentService
from app.services.prompts import PromptService
from app.services.tools import ToolService
from app.services.use_cases import UseCaseService


def _get_test_sessions_state(app_state: Any) -> dict:
    if not hasattr(app_state, "test_sessions"):
        return {}
    return app_state.test_sessions


def get_stored_test_session(request: Request, session_id: str) -> dict:
    """Return stored test session dict or raise SessionNotFound. Expired sessions (2h TTL) are treated as not found."""
    from datetime import UTC, datetime

    state = _get_test_sessions_state(request.app.state)
    if session_id not in state:
        raise SessionNotFound(f"Test session not found: {session_id}")
    stored = state[session_id]
    expires_at = stored.get("expires_at")
    if expires_at is not None and datetime.now(UTC) >= expires_at:
        state.pop(session_id, None)
        raise SessionNotFound(f"Test session expired: {session_id}")
    return stored


def get_stored_test_session_from_state(app_state: Any, session_id: str) -> dict:
    """Same as get_stored_test_session but using app_state (e.g. for WebSocket)."""
    from datetime import UTC, datetime

    state = _get_test_sessions_state(app_state)
    if session_id not in state:
        raise SessionNotFound(f"Test session not found: {session_id}")
    stored = state[session_id]
    expires_at = stored.get("expires_at")
    if expires_at is not None and datetime.now(UTC) >= expires_at:
        state.pop(session_id, None)
        raise SessionNotFound(f"Test session expired: {session_id}")
    return stored


async def get_http_client(request: Request) -> httpx.AsyncClient:
    return request.app.state.http_client


async def get_hermes_client(request: Request) -> HermesClient:
    return request.app.state.hermes_client


async def get_agent_service(
    session: AsyncSession = Depends(get_session),
    http_client: httpx.AsyncClient = Depends(get_http_client),
    hermes_client: HermesClient = Depends(get_hermes_client),
) -> AgentService:
    repo = SQLAgentRepository(session)
    return AgentService(
        repo, session, http_client, settings.AGENT_SERVICE_URL, hermes_client
    )


async def get_document_service(
    session: AsyncSession = Depends(get_session),
    http_client: httpx.AsyncClient = Depends(get_http_client),
) -> DocumentService:
    repo = SQLDocumentRepository(session)
    return DocumentService(repo, session, http_client, settings.AGENT_SERVICE_URL)


async def get_prompt_service(
    session: AsyncSession = Depends(get_session),
) -> PromptService:
    repo = SQLPromptRepository(session)
    return PromptService(repo, session)


async def get_use_case_service(
    session: AsyncSession = Depends(get_session),
) -> UseCaseService:
    repo = SQLUseCaseRepository(session)
    return UseCaseService(repo, session)


async def get_tool_service(
    session: AsyncSession = Depends(get_session),
) -> ToolService:
    repo = SQLToolRepository(session)
    return ToolService(repo, session)


async def get_conversation_service(
    session: AsyncSession = Depends(get_session),
    http_client: httpx.AsyncClient = Depends(get_http_client),
) -> ConversationService:
    return ConversationService(http_client, settings.CONVERSATION_SERVICE_URL)
