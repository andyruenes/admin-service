"""Integration tests for Agent endpoints (live FastAPI + PostgreSQL)."""

import pytest
import pytest_asyncio

# Route audit (app/api/agents.py):
#   GET    /admin/agents           -> 200, AgentListResponse (items, total, offset, limit)
#   POST   /admin/agents           -> 201, dict with "agent_id" only
#   GET    /admin/agents/{id}      -> 200, AgentRead
#   PUT    /admin/agents/{id}      -> 200, AgentRead (full update)
#   PATCH  /admin/agents/{id}/status -> 200, AgentRead (body: {"status": "..."})
#   DELETE /admin/agents/{id}      -> 204, empty body (409 if active)

_agent_id: str = ""


@pytest_asyncio.fixture(scope="module", autouse=True)
async def clean_db(truncate_before_module):
    """Trigger truncation once per module (fixture from conftest)."""
    yield


# --- Happy path ---


@pytest.mark.asyncio
async def test_create_agent_status_is_draft(client):
    """POST; assert 201, status is draft, capture _agent_id."""
    global _agent_id
    payload = {
        "name": "Test Agent",
        "description": "First agent",
        "llm_model": "gpt-4",
        "status": "draft",
    }
    response = await client.post("/admin/agents", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "agent_id" in data
    _agent_id = data["agent_id"]
    # POST returns only agent_id; confirm status via GET
    get_resp = await client.get(f"/admin/agents/{_agent_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["status"] == "draft"


@pytest.mark.asyncio
async def test_get_agent_after_create(client):
    """GET; assert 200, all fields match create payload."""
    response = await client.get(f"/admin/agents/{_agent_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == _agent_id
    assert data["name"] == "Test Agent"
    assert data["description"] == "First agent"
    assert data["llm_model"] == "gpt-4"
    assert data["status"] == "draft"
    assert "created_at" in data
    assert "updated_at" in data


@pytest.mark.asyncio
async def test_list_agents_contains_created(client):
    """GET list; assert agent in items."""
    response = await client.get("/admin/agents")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    items = data["items"]
    ids = [a["id"] for a in items]
    assert _agent_id in ids
    agent = next(a for a in items if a["id"] == _agent_id)
    assert agent["name"] == "Test Agent"
    assert agent["status"] == "draft"


@pytest.mark.asyncio
async def test_list_agents_search_by_name(client):
    """GET ?search=<name>; assert only matching agents in items (non-matching excluded)."""
    create_a = await client.post(
        "/admin/agents",
        json={
            "name": "SearchMatchUnique",
            "description": "For search test",
            "llm_model": "gpt-4",
        },
    )
    assert create_a.status_code == 201
    create_b = await client.post(
        "/admin/agents",
        json={
            "name": "OtherNameNotMatching",
            "description": "Other",
            "llm_model": "gpt-4",
        },
    )
    assert create_b.status_code == 201
    response = await client.get(
        "/admin/agents",
        params={"search": "SearchMatchUnique"},
    )
    assert response.status_code == 200
    items = response.json()["items"]
    # All returned items must match search; non-matching must NOT appear
    for item in items:
        assert (
            "SearchMatchUnique" in item["name"] or item["name"] == "SearchMatchUnique"
        )
    names = [a["name"] for a in items]
    assert "OtherNameNotMatching" not in names


@pytest.mark.asyncio
async def test_list_agents_pagination(client):
    """Create 3 more agents, GET ?page=1&limit=2; assert page size and total; verify page 2 differs."""
    for i in range(3):
        r = await client.post(
            "/admin/agents",
            json={
                "name": f"PaginatedAgent{i}",
                "description": "For pagination",
                "llm_model": "gpt-4",
            },
        )
        assert r.status_code == 201
    response = await client.get("/admin/agents", params={"page": 1, "limit": 2})
    assert response.status_code == 200
    data = response.json()
    items = data["items"]
    assert len(items) == 2
    assert data["limit"] == 2
    assert data["offset"] == 0
    assert data["total"] >= 2
    page1_ids = {a["id"] for a in items}
    # Verify page 2 returns a different set (proves offset/count work)
    page2 = await client.get("/admin/agents", params={"page": 2, "limit": 2})
    assert page2.status_code == 200
    page2_items = page2.json()["items"]
    page2_ids = {a["id"] for a in page2_items}
    assert page1_ids.isdisjoint(page2_ids), "page 2 must not return same ids as page 1"


@pytest.mark.asyncio
async def test_update_agent_fields(client):
    """PUT with new name, description, llm_model; assert 200, all changed."""
    response = await client.put(
        f"/admin/agents/{_agent_id}",
        json={
            "name": "Updated Agent Name",
            "description": "Updated description",
            "llm_model": "gpt-4-turbo",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Agent Name"
    assert data["description"] == "Updated description"
    assert data["llm_model"] == "gpt-4-turbo"
    assert data["status"] == "draft"


@pytest.mark.asyncio
async def test_change_status_draft_to_active(client):
    """PATCH status; assert 200, status == 'active'."""
    response = await client.patch(
        f"/admin/agents/{_agent_id}/status",
        json={"status": "active"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "active"


@pytest.mark.asyncio
async def test_change_status_active_to_inactive(client):
    """PATCH status; assert 200, status == 'inactive'."""
    response = await client.patch(
        f"/admin/agents/{_agent_id}/status",
        json={"status": "inactive"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "inactive"


@pytest.mark.asyncio
async def test_delete_inactive_agent(client, mock_agent_service):
    """DELETE; assert 204 (inactive allowed)."""
    response = await client.delete(f"/admin/agents/{_agent_id}")
    assert response.status_code == 204
    assert response.content == b"" or len(response.content) == 0


@pytest.mark.asyncio
async def test_get_deleted_agent_is_404(client):
    """GET after delete; assert 404."""
    response = await client.get(f"/admin/agents/{_agent_id}")
    assert response.status_code == 404


# --- Error path ---


@pytest.mark.asyncio
async def test_create_agent_duplicate_name(client):
    """Create same name twice; second returns 409."""
    payload = {
        "name": "DuplicateNameAgent",
        "description": "First",
        "llm_model": "gpt-4",
    }
    first = await client.post("/admin/agents", json=payload)
    assert first.status_code == 201
    second = await client.post("/admin/agents", json=payload)
    assert second.status_code == 409


@pytest.mark.asyncio
async def test_change_status_invalid_transition(client):
    """Agent already inactive; PATCH to 'active' -> 422 (invalid transition)."""
    # Use a fresh agent: create, draft->active->inactive, then try active
    create_resp = await client.post(
        "/admin/agents",
        json={
            "name": "InvalidTransitionAgent",
            "description": "For 422 test",
            "llm_model": "gpt-4",
        },
    )
    assert create_resp.status_code == 201
    aid = create_resp.json()["agent_id"]
    await client.patch(f"/admin/agents/{aid}/status", json={"status": "active"})
    await client.patch(f"/admin/agents/{aid}/status", json={"status": "inactive"})
    # Now try invalid: inactive -> active
    response = await client.patch(
        f"/admin/agents/{aid}/status",
        json={"status": "active"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_delete_active_agent_is_409(client):
    """Create fresh agent, set active, DELETE -> 409 (do not use _agent_id)."""
    create_resp = await client.post(
        "/admin/agents",
        json={
            "name": "ActiveAgentToDelete",
            "description": "For 409 test",
            "llm_model": "gpt-4",
        },
    )
    assert create_resp.status_code == 201
    fresh_id = create_resp.json()["agent_id"]
    await client.patch(
        f"/admin/agents/{fresh_id}/status",
        json={"status": "active"},
    )
    response = await client.delete(f"/admin/agents/{fresh_id}")
    assert response.status_code == 409


# Integration test suite shared state
# _agent_id is written in test_create_agent_status_is_draft and consumed by happy-path
# tests; it is deleted by test_delete_inactive_agent. Downstream test modules that need
# a live agent in draft status should create their own (e.g. POST in a fixture or
# first test) and not rely on _agent_id after this module, since it is soft-deleted.
# To share an agent id with other modules, export it after (re-)creating:
#   from tests.integration.test_agents import _agent_id  # only valid before delete
# For a persistent draft agent for other modules, add a dedicated fixture or final
# test that creates one and sets a module-level variable for import.
#
# Step 5 — Weakest part: test_list_agents_pagination would pass even if the API
# ignored page/limit and always returned the first two agents (only len==2 and
# total>=2 were asserted). Fixed by asserting page 2 returns disjoint ids from page 1.
