"""Unit tests for test session service (create_session, invalidate_session)."""

from uuid import uuid4

import pytest

from app.domain.shared.exceptions import SessionNotFound
from app.services.test_sessions import create_session, invalidate_session
from tests.unit.factories import make_agent_tool, make_prompt_version, make_use_case


class AppState:
    def __init__(self) -> None:
        self.test_sessions: dict = {}


@pytest.fixture
def app_state():
    return AppState()


@pytest.mark.asyncio
async def test_create_session_returns_session_id(app_state):
    agent_id = uuid4()
    result = create_session(
        agent_id,
        app_state,
        active_prompt=None,
        use_cases=[],
        active_tools=[],
    )
    assert "session_id" in result
    assert result["session_id"]


@pytest.mark.asyncio
async def test_create_session_stored_in_app_state(app_state):
    agent_id = uuid4()
    result = create_session(
        agent_id,
        app_state,
        active_prompt=None,
        use_cases=[],
        active_tools=[],
    )
    session_id = result["session_id"]
    assert session_id in app_state.test_sessions


@pytest.mark.asyncio
async def test_create_session_snapshot_includes_active_prompt(app_state):
    agent_id = uuid4()
    prompt = make_prompt_version(agent_id=agent_id, is_active=True)
    result = create_session(
        agent_id,
        app_state,
        active_prompt=prompt,
        use_cases=[],
        active_tools=[],
    )
    session_id = result["session_id"]
    stored = app_state.test_sessions[session_id]
    assert stored["prompt"] is prompt
    assert stored["prompt"].is_active is True


@pytest.mark.asyncio
async def test_create_session_no_active_prompt_returns_none(app_state):
    agent_id = uuid4()
    result = create_session(
        agent_id,
        app_state,
        active_prompt=None,
        use_cases=[],
        active_tools=[],
    )
    assert result["active_prompt"] is None
    session_id = result["session_id"]
    assert app_state.test_sessions[session_id]["prompt"] is None


@pytest.mark.asyncio
async def test_create_session_snapshot_active_tools_only(app_state):
    agent_id = uuid4()
    active1 = make_agent_tool(agent_id=agent_id, is_active=True)
    active2 = make_agent_tool(agent_id=agent_id, is_active=True)
    inactive = make_agent_tool(agent_id=agent_id, is_active=False)
    active_tools_only = [active1, active2]
    result = create_session(
        agent_id,
        app_state,
        active_prompt=None,
        use_cases=[],
        active_tools=active_tools_only,
    )
    session_id = result["session_id"]
    stored = app_state.test_sessions[session_id]
    assert len(stored["tools"]) == 2
    assert active1 in stored["tools"]
    assert active2 in stored["tools"]
    assert inactive not in stored["tools"]


@pytest.mark.asyncio
async def test_create_session_snapshot_includes_all_use_cases(app_state):
    agent_id = uuid4()
    uc1 = make_use_case(agent_id=agent_id, question="Q1?", answer="A" * 10)
    uc2 = make_use_case(agent_id=agent_id, question="Q2?", answer="B" * 10)
    use_cases = [uc1, uc2]
    result = create_session(
        agent_id,
        app_state,
        active_prompt=None,
        use_cases=use_cases,
        active_tools=[],
    )
    session_id = result["session_id"]
    stored = app_state.test_sessions[session_id]
    assert len(stored["use_cases"]) == 2
    assert uc1 in stored["use_cases"]
    assert uc2 in stored["use_cases"]


@pytest.mark.asyncio
async def test_invalidate_session_removes_old_session_id(app_state):
    agent_id = uuid4()
    result = create_session(
        agent_id,
        app_state,
        active_prompt=None,
        use_cases=[],
        active_tools=[],
    )
    old_id = result["session_id"]
    invalidate_session(
        agent_id,
        old_id,
        app_state,
        active_prompt=None,
        use_cases=[],
        active_tools=[],
    )
    assert old_id not in app_state.test_sessions


@pytest.mark.asyncio
async def test_invalidate_session_new_id_is_different(app_state):
    agent_id = uuid4()
    result = create_session(
        agent_id,
        app_state,
        active_prompt=None,
        use_cases=[],
        active_tools=[],
    )
    old_id = result["session_id"]
    new_result = invalidate_session(
        agent_id,
        old_id,
        app_state,
        active_prompt=None,
        use_cases=[],
        active_tools=[],
    )
    assert new_result["session_id"] != old_id


@pytest.mark.asyncio
async def test_invalidate_session_new_id_stored_in_state(app_state):
    agent_id = uuid4()
    result = create_session(
        agent_id,
        app_state,
        active_prompt=None,
        use_cases=[],
        active_tools=[],
    )
    old_id = result["session_id"]
    new_result = invalidate_session(
        agent_id,
        old_id,
        app_state,
        active_prompt=None,
        use_cases=[],
        active_tools=[],
    )
    new_id = new_result["session_id"]
    assert new_id in app_state.test_sessions


@pytest.mark.asyncio
async def test_invalidate_session_unknown_id_raises(app_state):
    agent_id = uuid4()
    with pytest.raises(SessionNotFound):
        invalidate_session(
            agent_id,
            "unknown-session-id",
            app_state,
            active_prompt=None,
            use_cases=[],
            active_tools=[],
        )
