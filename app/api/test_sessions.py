"""Test session router — in-memory only; injects request.app.state.test_sessions."""

import json
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Request, WebSocket, WebSocketDisconnect

from app.api.deps import (
    get_prompt_service,
    get_stored_test_session,
    get_stored_test_session_from_state,
    get_tool_service,
    get_use_case_service,
)
from app.domain.shared.exceptions import SessionNotFound
from app.schemas.prompts import PromptRead
from app.schemas.test_sessions import TestSessionResponse
from app.schemas.tools import AgentToolRead
from app.schemas.use_cases import UseCaseRead
from app.services.prompts import PromptService
from app.services.test_sessions import create_session, invalidate_session
from app.services.tools import ToolService
from app.services.use_cases import UseCaseService

router = APIRouter(tags=["test_sessions"])


def _to_response(payload: dict) -> TestSessionResponse:
    active_prompt = payload["active_prompt"]
    use_cases = payload["use_cases"]
    active_tools = payload["active_tools"]
    return TestSessionResponse(
        session_id=payload["session_id"],
        agent_id=payload["agent_id"],
        active_prompt=PromptRead.model_validate(active_prompt)
        if active_prompt
        else None,
        use_cases=[UseCaseRead.model_validate(u) for u in use_cases],
        active_tools=[AgentToolRead.model_validate(t) for t in active_tools],
    )


@router.post(
    "/agents/{agent_id}/test-session",
    response_model=TestSessionResponse,
    status_code=201,
)
async def post_test_session(
    request: Request,
    agent_id: UUID,
    prompt_service: PromptService = Depends(get_prompt_service),
    use_case_service: UseCaseService = Depends(get_use_case_service),
    tool_service: ToolService = Depends(get_tool_service),
) -> TestSessionResponse:
    active_prompt = await prompt_service.get_active_or_empty(agent_id)
    use_cases = await use_case_service.list(agent_id, 0, 100)
    all_tools = await tool_service.list_by_agent(agent_id)
    active_tools = [t for t in all_tools if t.is_active]
    payload = create_session(
        agent_id,
        request.app.state,
        active_prompt,
        use_cases,
        active_tools,
    )
    return _to_response(payload)


@router.delete(
    "/agents/{agent_id}/test-session/{session_id}",
    response_model=TestSessionResponse,
    status_code=200,
)
async def delete_test_session(
    request: Request,
    agent_id: UUID,
    session_id: str,
    prompt_service: PromptService = Depends(get_prompt_service),
    use_case_service: UseCaseService = Depends(get_use_case_service),
    tool_service: ToolService = Depends(get_tool_service),
) -> TestSessionResponse:
    try:
        stored = get_stored_test_session(request, session_id)
        agent_id = UUID(stored["agent_id"])
        active_prompt = stored["prompt"]
        use_cases = stored["use_cases"]
        active_tools = stored["tools"]
        payload = invalidate_session(
            agent_id,
            session_id,
            request.app.state,
            active_prompt,
            use_cases,
            active_tools,
        )
    except SessionNotFound:
        # Session already expired or missing: create and return a new one (no error).
        active_prompt = await prompt_service.get_active_or_empty(agent_id)
        use_cases = await use_case_service.list(agent_id, 0, 100)
        all_tools = await tool_service.list_by_agent(agent_id)
        active_tools = [t for t in all_tools if t.is_active]
        payload = create_session(
            agent_id,
            request.app.state,
            active_prompt,
            use_cases,
            active_tools,
        )
    return _to_response(payload)


# Close code for expired/invalid test session (custom, per plan).
WS_CLOSE_SESSION_INVALID = 4001

logger = logging.getLogger(__name__)


@router.websocket("/agents/{agent_id}/test-session/ws")
async def agent_test_session_websocket(
    websocket: WebSocket,
    agent_id: UUID,
) -> None:
    """Real-time test channel. Validates session_id on connect; closes with 4001 if expired/invalid. Messages are not persisted."""
    await websocket.accept()
    session_id = websocket.query_params.get("session_id")
    if not session_id:
        await websocket.close(code=WS_CLOSE_SESSION_INVALID)
        return
    try:
        get_stored_test_session_from_state(websocket.app.state, session_id)
    except SessionNotFound:
        await websocket.close(code=WS_CLOSE_SESSION_INVALID)
        return
    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                content = msg.get("content", msg.get("text", ""))
            except (json.JSONDecodeError, TypeError):
                content = data
            # Placeholder: echo / stub response (IA service integration to be wired when chat API is defined).
            response = {
                "role": "assistant",
                "content": f"[Test] Received: {content[:200]}",
            }
            await websocket.send_text(json.dumps(response))
    except WebSocketDisconnect:
        pass
    except Exception as exc:  # noqa: BLE001
        logger.exception("Test session WebSocket error: %s", exc)
    finally:
        try:
            await websocket.close()
        except Exception:  # noqa: BLE001
            pass
