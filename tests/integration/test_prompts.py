"""Integration tests for Prompt Version endpoints (live FastAPI + PostgreSQL)."""

import pytest
import pytest_asyncio

from tests.integration.test_agents import _agent_id

# Route audit (app/api/prompts.py):
#   GET  /admin/agents/{id}/prompt                             -> 200 PromptRead, 404 if no active
#   PUT  /admin/agents/{id}/prompt                             -> 200 PromptRead (body: {"content": "..."})
#   GET  /admin/agents/{id}/prompt/versions                     -> 200 PromptVersionListResponse (items)
#   GET  /admin/agents/{id}/prompt/versions/{version_number}    -> 200 PromptRead
#   POST /admin/agents/{id}/prompt/versions/{version_number}/restore -> 200 PromptRead

# Module-level agent: use _agent_id when suite runs test_agents first and does not truncate
# before this module; otherwise we create one in the fixture below.
agent_id: str = ""


@pytest_asyncio.fixture(scope="module", autouse=True)
async def ensure_agent(client):
    """Ensure we have a valid agent_id (create one if DB was truncated)."""
    global agent_id
    agent_id = _agent_id
    # If agent was truncated or deleted, create one
    if agent_id:
        r = await client.get(f"/admin/agents/{agent_id}")
        if r.status_code == 200:
            yield agent_id
            return
    create = await client.post(
        "/admin/agents",
        json={
            "name": "PromptTestAgent",
            "description": "For prompts",
            "llm_model": "gpt-4",
        },
    )
    assert create.status_code == 201
    agent_id = create.json()["agent_id"]
    yield agent_id


@pytest.mark.asyncio
async def test_get_active_prompt_before_any_save_returns_empty(client, ensure_agent):
    """GET active prompt before any save; assert 200 with empty content (no error)."""
    response = await client.get(f"/admin/agents/{ensure_agent}/prompt")
    assert response.status_code == 200
    data = response.json()
    assert data["content"] == ""
    assert data["version_number"] == 0
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_save_first_prompt_version(client, ensure_agent):
    """PUT content; assert 200, version_number == 1, is_active == True."""
    content = "First prompt content."
    response = await client.put(
        f"/admin/agents/{agent_id}/prompt",
        json={"content": content},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["version_number"] == 1
    assert data["is_active"] is True
    assert data["content"] == content


@pytest.mark.asyncio
async def test_get_active_prompt_returns_version_1(client, ensure_agent):
    """GET active; assert version_number == 1."""
    response = await client.get(f"/admin/agents/{agent_id}/prompt")
    assert response.status_code == 200
    assert response.json()["version_number"] == 1
    assert response.json()["is_active"] is True


@pytest.mark.asyncio
async def test_char_count_is_correct(client, ensure_agent):
    """Assert char_count == len(content); use exact same content from GET active."""
    response = await client.get(f"/admin/agents/{agent_id}/prompt")
    assert response.status_code == 200
    data = response.json()
    content = data["content"]
    assert data["char_count"] == len(content)


@pytest.mark.asyncio
async def test_save_second_prompt_increments_version(client, ensure_agent):
    """PUT new content (200 chars for later truncation test); assert version_number == 2, first no longer active."""
    long_second = "Second prompt content. " + ("x" * 180)  # 200+ chars
    response = await client.put(
        f"/admin/agents/{agent_id}/prompt",
        json={"content": long_second},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["version_number"] == 2
    assert data["is_active"] is True
    # Explicit is_active transition: version 1 no longer active
    get_v1 = await client.get(f"/admin/agents/{agent_id}/prompt/versions/1")
    assert get_v1.status_code == 200
    assert get_v1.json()["is_active"] is False


@pytest.mark.asyncio
async def test_get_active_prompt_is_now_version_2(client, ensure_agent):
    """GET active; assert version_number == 2."""
    response = await client.get(f"/admin/agents/{agent_id}/prompt")
    assert response.status_code == 200
    data = response.json()
    assert data["version_number"] == 2
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_list_versions_ordered_desc(client, ensure_agent):
    """GET versions; assert first item has highest version_number (2)."""
    response = await client.get(f"/admin/agents/{agent_id}/prompt/versions")
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) >= 2
    first_version = items[0]["version_number"]
    assert first_version == 2


@pytest.mark.asyncio
async def test_list_versions_content_truncated_to_150(client, ensure_agent):
    """v2 was saved with 200+ chars; assert list content_preview length <= 150."""
    response = await client.get(f"/admin/agents/{agent_id}/prompt/versions")
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) >= 2
    v2 = next((x for x in items if x["version_number"] == 2), None)
    assert v2 is not None
    preview = v2["content_preview"]
    assert len(preview) <= 150


@pytest.mark.asyncio
async def test_get_specific_version_full_content(client, ensure_agent):
    """GET /versions/1; assert full content (not truncated)."""
    response = await client.get(f"/admin/agents/{agent_id}/prompt/versions/1")
    assert response.status_code == 200
    data = response.json()
    assert data["version_number"] == 1
    assert data["content"] == "First prompt content."


@pytest.mark.asyncio
async def test_restore_version_1_creates_version_3(client, ensure_agent):
    """POST restore/1; assert version_number == 3, content matches v1, and version 1 still exists unchanged."""
    get_v1_before = await client.get(f"/admin/agents/{agent_id}/prompt/versions/1")
    assert get_v1_before.status_code == 200
    v1_content = get_v1_before.json()["content"]
    response = await client.post(f"/admin/agents/{agent_id}/prompt/versions/1/restore")
    assert response.status_code == 200
    data = response.json()
    assert data["version_number"] == 3
    assert data["is_active"] is True
    assert data["content"] == v1_content, (
        "restore must return v1 content, not current active"
    )
    # Source version 1 must still exist unchanged
    get_v1 = await client.get(f"/admin/agents/{agent_id}/prompt/versions/1")
    assert get_v1.status_code == 200
    v1_data = get_v1.json()
    assert v1_data["version_number"] == 1
    assert v1_data["content"] == v1_content


@pytest.mark.asyncio
async def test_restored_content_matches_version_1(client, ensure_agent):
    """Assert content of version 3 == content of version 1."""
    get_v1 = await client.get(f"/admin/agents/{agent_id}/prompt/versions/1")
    assert get_v1.status_code == 200
    v1_content = get_v1.json()["content"]
    get_v3 = await client.get(f"/admin/agents/{agent_id}/prompt/versions/3")
    assert get_v3.status_code == 200
    assert get_v3.json()["content"] == v1_content


@pytest.mark.asyncio
async def test_active_after_restore_is_version_3(client, ensure_agent):
    """GET active; assert version_number == 3 and is_active."""
    response = await client.get(f"/admin/agents/{agent_id}/prompt")
    assert response.status_code == 200
    data = response.json()
    assert data["version_number"] == 3
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_create_prompt_then_get_returns_it(client, ensure_agent):
    """Create a prompt via PUT, then GET it; assert 200 and content matches."""
    content = "Test prompt content for create-then-get."
    put_resp = await client.put(
        f"/admin/agents/{ensure_agent}/prompt",
        json={"content": content},
    )
    assert put_resp.status_code == 200
    get_resp = await client.get(f"/admin/agents/{ensure_agent}/prompt")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["content"] == content
    assert data["is_active"] is True
    assert data["version_number"] >= 1


# Step 4 — Adversarial: test_list_versions_content_truncated uses v2 saved with 200+ chars
# in test_save_second_prompt_increments_version; test_restore verifies v1 unchanged;
# test_char_count uses GET active and same content for len().
# Step 5 — Weakest part: test_restore_version_1_creates_version_3 would pass if restore
# returned the existing active prompt (v2) with version_number spoofed to 3. Fixed by
# asserting response content equals version 1 content in that test.
