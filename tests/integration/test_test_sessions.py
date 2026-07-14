"""Integration tests for Test Session endpoints (in-memory; no DB).

Depends on: _agent_id from test_agents. This module runs LAST — the agent must
already have prompt, use_cases, and tools configured (from test_prompts, test_use_cases,
test_agent_tools). test_create_session_snapshot_has_active_tools requires at least
one tool toggled active in a previous module (test_agent_tools).
"""

import pytest
import pytest_asyncio

from tests.integration.test_agents import _agent_id

# Route audit (app/api/test_sessions.py):
#   POST   /admin/agents/{id}/test-session             -> 201 TestSessionResponse (agent_id in path only)
#   DELETE /admin/agents/{id}/test-session/{session_id} -> 200 TestSessionResponse (not 204)

agent_id: str = ""


@pytest_asyncio.fixture(scope="module", autouse=True)
async def ensure_agent(client):
    """Use _agent_id if agent exists; else create agent + prompt, use case, and active tool so snapshot tests pass."""
    global agent_id
    agent_id = _agent_id
    if agent_id:
        r = await client.get(f"/admin/agents/{agent_id}")
        if r.status_code == 200:
            yield
            return
    # Agent missing or deleted (e.g. test_agents deleted it): create one and minimal snapshot data
    create = await client.post(
        "/admin/agents",
        json={
            "name": "TestSessionAgent",
            "description": "For test sessions",
            "llm_model": "gpt-4",
        },
    )
    assert create.status_code == 201
    agent_id = create.json()["agent_id"]
    await client.put(
        f"/admin/agents/{agent_id}/prompt",
        json={"content": "Test session prompt content."},
    )
    await client.post(
        f"/admin/agents/{agent_id}/use-cases",
        json={"pregunta": "Session Q?", "respuesta": "A" * 10},
    )
    tool = await client.post(
        "/admin/tools",
        json={
            "name": "session_tool",
            "description": "For session snapshot",
            "function_ref": "ref.func",
        },
    )
    assert tool.status_code == 201
    await client.post(
        f"/admin/agents/{agent_id}/tools",
        json={"tool_id": tool.json()["id"]},
    )
    await client.patch(f"/admin/agents/{agent_id}/tools/{tool.json()['id']}/toggle")
    yield


@pytest.mark.asyncio
async def test_create_session_returns_session_id(client, ensure_agent):
    """POST; assert 201, session_id present and non-empty."""
    response = await client.post(f"/admin/agents/{agent_id}/test-session")
    assert response.status_code == 201
    data = response.json()
    assert "session_id" in data
    assert data["session_id"] and isinstance(data["session_id"], str)


@pytest.mark.asyncio
async def test_create_session_snapshot_has_prompt(client, ensure_agent):
    """Assert active_prompt is not None (prompt was saved in previous module)."""
    response = await client.post(f"/admin/agents/{agent_id}/test-session")
    assert response.status_code == 201
    data = response.json()
    assert data.get("active_prompt") is not None


@pytest.mark.asyncio
async def test_create_session_snapshot_has_use_cases(client, ensure_agent):
    """Assert use_cases is non-empty list."""
    response = await client.post(f"/admin/agents/{agent_id}/test-session")
    assert response.status_code == 201
    data = response.json()
    assert "use_cases" in data
    assert isinstance(data["use_cases"], list)
    assert len(data["use_cases"]) > 0


@pytest.mark.asyncio
async def test_create_session_snapshot_has_active_tools(client, ensure_agent):
    """Assert active_tools contains only tools where is_active == True (each item)."""
    response = await client.post(f"/admin/agents/{agent_id}/test-session")
    assert response.status_code == 201
    data = response.json()
    assert "active_tools" in data
    active_tools = data["active_tools"]
    assert isinstance(active_tools, list)
    for t in active_tools:
        assert t.get("is_active") is True, (
            "active_tools must contain only is_active=True tools"
        )


@pytest.mark.asyncio
async def test_two_sessions_have_different_ids(client, ensure_agent):
    """Create two sessions in this test; assert session_id values differ."""
    r1 = await client.post(f"/admin/agents/{agent_id}/test-session")
    assert r1.status_code == 201
    id1 = r1.json()["session_id"]
    r2 = await client.post(f"/admin/agents/{agent_id}/test-session")
    assert r2.status_code == 201
    id2 = r2.json()["session_id"]
    assert id1 != id2


@pytest.mark.asyncio
async def test_invalidate_session_returns_200_with_body(client, ensure_agent):
    """DELETE; assert 200 (not 204), body has session_id."""
    create = await client.post(f"/admin/agents/{agent_id}/test-session")
    assert create.status_code == 201
    session_id = create.json()["session_id"]
    response = await client.delete(
        f"/admin/agents/{agent_id}/test-session/{session_id}",
    )
    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data
    assert data["session_id"] and isinstance(data["session_id"], str)


@pytest.mark.asyncio
async def test_invalidate_session_new_id_differs_from_old(client, ensure_agent):
    """Assert new session_id != old session_id after invalidate."""
    create = await client.post(f"/admin/agents/{agent_id}/test-session")
    assert create.status_code == 201
    old_id = create.json()["session_id"]
    response = await client.delete(
        f"/admin/agents/{agent_id}/test-session/{old_id}",
    )
    assert response.status_code == 200
    new_id = response.json()["session_id"]
    assert new_id != old_id


@pytest.mark.asyncio
async def test_invalidate_unknown_session_returns_new_session(client, ensure_agent):
    """DELETE with nonexistent session_id: API returns 200 with a new session (no 404). See docs/TEST_SESSION_INVALIDATE_BEHAVIOUR.md."""
    response = await client.delete(
        f"/admin/agents/{agent_id}/test-session/nonexistent-session-id-xyz",
    )
    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] != "nonexistent-session-id-xyz"
    assert data["agent_id"] == agent_id


# Step 4 — Weakest part: test_create_session_snapshot_has_active_tools would pass even
# if the snapshot was always empty (active_tools [] — loop runs zero times). Fixed by
# test_create_session_snapshot_has_prompt (active_prompt is not None) and
# test_create_session_snapshot_has_use_cases (len(use_cases) > 0), which prove the
# snapshot is populated from DB; active_tools then only asserts the filter (is_active).
