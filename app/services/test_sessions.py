"""Test session service — in-memory only (app.state.test_sessions). No repo, no DB."""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from app.domain.prompts.entity import PromptVersion
from app.domain.shared.exceptions import SessionNotFound

TEST_SESSION_TTL_HOURS = 2


def create_session(
    agent_id: UUID,
    app_state: Any,
    active_prompt: PromptVersion | None,
    use_cases: list[Any],
    active_tools: list[Any],
) -> dict[str, Any]:
    """Store a new test session in app_state.test_sessions; return session payload. TTL 2 hours."""
    session_id = str(uuid4())
    if not hasattr(app_state, "test_sessions"):
        app_state.test_sessions = {}
    now = datetime.now(UTC)
    expires_at = now + timedelta(hours=TEST_SESSION_TTL_HOURS)
    app_state.test_sessions[session_id] = {
        "agent_id": str(agent_id),
        "prompt": active_prompt,
        "use_cases": use_cases,
        "tools": active_tools,
        "expires_at": expires_at,
    }
    return {
        "session_id": session_id,
        "agent_id": agent_id,
        "active_prompt": active_prompt,
        "use_cases": use_cases,
        "active_tools": active_tools,
    }


def invalidate_session(
    agent_id: UUID,
    session_id: str,
    app_state: Any,
    active_prompt: PromptVersion | None,
    use_cases: list[Any],
    active_tools: list[Any],
) -> dict[str, Any]:
    """Remove session_id from app_state.test_sessions; raise SessionNotFound if missing. Then create fresh session and return."""
    if not hasattr(app_state, "test_sessions"):
        app_state.test_sessions = {}
    if session_id not in app_state.test_sessions:
        raise SessionNotFound(f"Test session not found: {session_id}")
    app_state.test_sessions.pop(session_id)
    return create_session(agent_id, app_state, active_prompt, use_cases, active_tools)
