"""Integration tests for Agent↔Tool association endpoints (live FastAPI + PostgreSQL)."""

import uuid

import pytest
import pytest_asyncio

from tests.integration.test_agents import _agent_id
from tests.integration.test_tools_catalog import _tool_id

# Route audit (app/api/tools.py):
#   GET   /admin/agents/{agent_id}/tools                      -> 200 AgentToolListResponse (items, active_count)
#   POST  /admin/agents/{agent_id}/tools                       -> 201 attach (body: {tool_id})
#   PATCH /admin/agents/{agent_id}/tools/{tool_id}/toggle      -> 200 flip is_active (no body)
#   PATCH /admin/agents/{agent_id}/tools/{tool_id}/active      -> 200 set is_active (body)
#   DELETE /admin/agents/{agent_id}/tools/{tool_id}            -> 204 detach

agent_id: str = ""
tool_id: str = ""


@pytest_asyncio.fixture(scope="module", autouse=True)
async def ensure_agent_and_tool(client):
    """Use _agent_id / _tool_id if valid; otherwise create. Attach tool to agent for list tests."""
    global agent_id, tool_id
    agent_id = _agent_id
    if agent_id:
        r = await client.get(f"/admin/agents/{agent_id}")
        if r.status_code != 200:
            agent_id = ""
    if not agent_id:
        create_a = await client.post(
            "/admin/agents",
            json={
                "name": "AgentToolsAgent",
                "description": "For agent-tools",
                "llm_model": "gpt-4",
            },
        )
        assert create_a.status_code == 201
        agent_id = create_a.json()["agent_id"]

    tool_id = _tool_id
    if tool_id:
        r = await client.get(f"/admin/tools/{tool_id}")
        if r.status_code != 200:
            tool_id = ""
    if not tool_id:
        create_t = await client.post(
            "/admin/tools",
            json={
                "name": "agent_tools_catalog_tool",
                "description": "Tool for agent-tools tests",
                "function_ref": "ref.func",
            },
        )
        assert create_t.status_code == 201
        tool_id = create_t.json()["id"]

    # Attach tool to agent so it appears in list (is_active False initially)
    attach = await client.post(
        f"/admin/agents/{agent_id}/tools",
        json={"tool_id": tool_id},
    )
    assert attach.status_code == 201
    yield


@pytest.mark.asyncio
async def test_list_agent_tools_tool_present(client, ensure_agent_and_tool):
    """GET list; assert the catalog tool appears in items with name and description."""
    response = await client.get(f"/admin/agents/{agent_id}/tools")
    assert response.status_code == 200
    data = response.json()
    items = data["items"]
    tool_ids = [t["tool_id"] for t in items]
    assert tool_id in tool_ids
    our = next(t for t in items if t["tool_id"] == tool_id)
    assert "name" in our and our["name"], "list item must have name"
    assert "description" in our, "list item must have description"
    # Exact values when we created the tool in this module; when using _tool_id they come from catalog
    assert our["name"] in ("agent_tools_catalog_tool", "test_slug_tool")
    assert len(our["description"]) > 0


@pytest.mark.asyncio
async def test_list_agent_tools_initially_inactive(client, ensure_agent_and_tool):
    """Assert is_active == False for the tool."""
    response = await client.get(f"/admin/agents/{agent_id}/tools")
    assert response.status_code == 200
    items = response.json()["items"]
    our = next(t for t in items if t["tool_id"] == tool_id)
    assert our["is_active"] is False


@pytest.mark.asyncio
async def test_list_agent_tools_active_count_zero(client, ensure_agent_and_tool):
    """Assert active_count == 0."""
    response = await client.get(f"/admin/agents/{agent_id}/tools")
    assert response.status_code == 200
    assert response.json()["active_count"] == 0


@pytest.mark.asyncio
async def test_toggle_tool_activates(client, ensure_agent_and_tool):
    """PATCH toggle (no body); assert 200, is_active == True."""
    response = await client.patch(
        f"/admin/agents/{agent_id}/tools/{tool_id}/toggle",
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_list_after_toggle_active_count_one(client, ensure_agent_and_tool):
    """GET list AFTER the toggle; assert active_count == 1."""
    response = await client.get(f"/admin/agents/{agent_id}/tools")
    assert response.status_code == 200
    assert response.json()["active_count"] == 1


@pytest.mark.asyncio
async def test_toggle_tool_deactivates(client, ensure_agent_and_tool):
    """PATCH toggle a second time; assert is_active == False (do not reuse first toggle response)."""
    response = await client.patch(
        f"/admin/agents/{agent_id}/tools/{tool_id}/toggle",
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_active"] is False


@pytest.mark.asyncio
async def test_list_after_deactivate_active_count_zero(client, ensure_agent_and_tool):
    """GET list; assert active_count == 0."""
    response = await client.get(f"/admin/agents/{agent_id}/tools")
    assert response.status_code == 200
    assert response.json()["active_count"] == 0


@pytest.mark.asyncio
async def test_attach_tool_explicit_endpoint(client, ensure_agent_and_tool):
    """POST attach endpoint; assert 201 and association payload."""
    create_t = await client.post(
        "/admin/tools",
        json={
            "name": "agent_tools_attach_flow",
            "description": "Tool for attach/detach/set-active flow",
            "function_ref": "ref.attach_flow",
        },
    )
    assert create_t.status_code == 201
    attach_tool_id = create_t.json()["id"]

    attach = await client.post(
        f"/admin/agents/{agent_id}/tools",
        json={"tool_id": attach_tool_id},
    )
    assert attach.status_code == 201
    data = attach.json()
    assert data["agent_id"] == agent_id
    assert data["tool_id"] == attach_tool_id
    assert data["is_active"] is False

    # stash id on module-global for subsequent tests in this flow
    globals()["_ATTACH_FLOW_TOOL_ID"] = attach_tool_id


@pytest.mark.asyncio
async def test_set_active_endpoint_true_then_false(client, ensure_agent_and_tool):
    """PATCH /active endpoint; assert persisted true then false."""
    attach_tool_id = globals().get("_ATTACH_FLOW_TOOL_ID")
    assert attach_tool_id, "attach flow tool id not initialized"

    activate = await client.patch(
        f"/admin/agents/{agent_id}/tools/{attach_tool_id}/active",
        json={"is_active": True},
    )
    assert activate.status_code == 200
    assert activate.json()["is_active"] is True

    deactivate = await client.patch(
        f"/admin/agents/{agent_id}/tools/{attach_tool_id}/active",
        json={"is_active": False},
    )
    assert deactivate.status_code == 200
    assert deactivate.json()["is_active"] is False


@pytest.mark.asyncio
async def test_detach_tool_endpoint(client, ensure_agent_and_tool):
    """DELETE detach endpoint; assert 204 and no longer present in list."""
    attach_tool_id = globals().get("_ATTACH_FLOW_TOOL_ID")
    assert attach_tool_id, "attach flow tool id not initialized"

    response = await client.delete(
        f"/admin/agents/{agent_id}/tools/{attach_tool_id}",
    )
    assert response.status_code == 204

    list_resp = await client.get(f"/admin/agents/{agent_id}/tools")
    assert list_resp.status_code == 200
    ids = [t["tool_id"] for t in list_resp.json()["items"]]
    assert attach_tool_id not in ids


# --- Error path ---


@pytest.mark.asyncio
async def test_toggle_nonexistent_tool(client, ensure_agent_and_tool):
    """PATCH toggle with random UUID as tool_id; assert 404."""
    random_tool_id = str(uuid.uuid4())
    response = await client.patch(
        f"/admin/agents/{agent_id}/tools/{random_tool_id}/toggle",
    )
    assert response.status_code == 404


# Step 3 — Adversarial: test_list_agent_tools_tool_present asserts name and description;
# test_toggle_tool_deactivates calls toggle a second time (not reuse first response);
# test_list_after_toggle_active_count_one calls GET after the toggle.
# Step 4 — Weakest part: asserting only the toggle response is_active would pass if toggle
# did nothing but the response still returned is_active True/False. Fixed by asserting
# active_count from the LIST response (test_list_after_toggle_active_count_one and
# test_list_after_deactivate_active_count_zero) so we verify persisted state.
