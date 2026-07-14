"""Integration tests for Tool Catalog endpoints (live FastAPI + PostgreSQL)."""

import uuid

import pytest
import pytest_asyncio

# Route audit (app/api/tools.py):
#   GET    /admin/tools         -> 200, list[ToolRead] (array, no "items" wrapper)
#   POST   /admin/tools         -> 201, ToolRead
#   GET    /admin/tools/{id}    -> 200, ToolRead
#   PATCH  /admin/tools/{id}    -> 200, ToolRead
#   DELETE /admin/tools/{id}    -> 204, empty body

_tool_id: str = ""


@pytest_asyncio.fixture(scope="module", autouse=True)
async def clean_db(truncate_before_module):
    """Trigger truncation once per module (fixture from conftest)."""
    yield


@pytest.mark.asyncio
async def test_create_tool(client):
    """POST with valid payload; assert 201, id present, name matches."""
    global _tool_id
    payload = {
        "name": "test_slug_tool",
        "description": "A test tool",
        "function_ref": "my_module.my_func",
    }
    response = await client.post("/admin/tools", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    _tool_id = data["id"]
    assert data["name"] == payload["name"]
    assert data["description"] == payload["description"]
    assert data["function_ref"] == payload["function_ref"]
    assert "created_at" in data


@pytest.mark.asyncio
async def test_get_tool_after_create(client):
    """GET /{tool_id}; assert 200 and all fields match create payload."""
    response = await client.get(f"/admin/tools/{_tool_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == _tool_id
    assert data["name"] == "test_slug_tool"
    assert data["description"] == "A test tool"
    assert data["function_ref"] == "my_module.my_func"
    assert "created_at" in data


@pytest.mark.asyncio
async def test_list_tools_contains_created(client):
    """GET /; assert 200, tool in list, length >= 1."""
    response = await client.get("/admin/tools")
    assert response.status_code == 200
    items = response.json()
    assert isinstance(items, list)
    assert len(items) >= 1
    ids = [t["id"] for t in items]
    assert _tool_id in ids
    created = next(t for t in items if t["id"] == _tool_id)
    assert created["name"] == "test_slug_tool"


@pytest.mark.asyncio
async def test_update_tool_description(client):
    """PATCH with new description; assert 200 and field changed."""
    response = await client.patch(
        f"/admin/tools/{_tool_id}",
        json={"description": "Updated description"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["description"] == "Updated description"
    assert data["name"] == "test_slug_tool"


@pytest.mark.asyncio
async def test_list_tools_reflects_update(client):
    """GET / after PATCH; assert updated description in list."""
    response = await client.get("/admin/tools")
    assert response.status_code == 200
    items = response.json()
    created = next(t for t in items if t["id"] == _tool_id)
    assert created["description"] == "Updated description"


@pytest.mark.asyncio
async def test_delete_tool(client):
    """DELETE; assert 204 and response body empty."""
    response = await client.delete(f"/admin/tools/{_tool_id}")
    assert response.status_code == 204
    assert response.content == b"" or len(response.content) == 0


@pytest.mark.asyncio
async def test_get_tool_after_delete_is_404(client):
    """GET /{tool_id} after delete; assert 404."""
    response = await client.get(f"/admin/tools/{_tool_id}")
    assert response.status_code == 404


# --- Error path ---


@pytest.mark.asyncio
async def test_create_tool_invalid_name_slug(client):
    """POST with name='My Tool!'; assert 422."""
    response = await client.post(
        "/admin/tools",
        json={
            "name": "My Tool!",
            "description": "Bad name",
            "function_ref": "ref",
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_tool_duplicate_name(client):
    """POST same name twice; first 201, second 409."""
    payload = {
        "name": "unique_dup_check",
        "description": "First",
        "function_ref": "ref",
    }
    first = await client.post("/admin/tools", json=payload)
    assert first.status_code == 201
    second = await client.post("/admin/tools", json=payload)
    assert second.status_code == 409


@pytest.mark.asyncio
async def test_get_nonexistent_tool(client):
    """GET random UUID returns 404; prove GET works for valid id first so test fails if endpoint is broken."""
    # Prove GET returns 200 for a valid tool (would fail if GET always returned 404)
    create_resp = await client.post(
        "/admin/tools",
        json={"name": "probe_get_ok", "description": "Probe", "function_ref": "ref"},
    )
    assert create_resp.status_code == 201
    existing_id = create_resp.json()["id"]
    get_resp = await client.get(f"/admin/tools/{existing_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["name"] == "probe_get_ok"
    # Now assert nonexistent id returns 404
    random_id = str(uuid.uuid4())
    response = await client.get(f"/admin/tools/{random_id}")
    assert response.status_code == 404
