"""Integration tests for Use Case endpoints (live FastAPI + PostgreSQL)."""

import pytest
import pytest_asyncio

from tests.integration.test_agents import _agent_id

# Route audit (app/api/use_cases.py): /random is declared BEFORE /{uc_id}
#   GET  /admin/agents/{id}/use-cases/random     -> 200 list[UseCaseRead] (?limit=)
#   GET  /admin/agents/{id}/use-cases/{uc_id}     -> 200 UseCaseRead
#   GET  /admin/agents/{id}/use-cases             -> 200 UseCaseListResponse (?search=)
#   POST /admin/agents/{id}/use-cases             -> 201 UseCaseRead
#   PUT   /admin/agents/{id}/use-cases/{uc_id}    -> 200 UseCaseRead
#   DELETE /admin/agents/{id}/use-cases/{uc_id}   -> 204

_uc_id: str = ""
agent_id: str = ""


@pytest_asyncio.fixture(scope="module", autouse=True)
async def ensure_agent(client):
    """Use _agent_id if valid; otherwise create an agent for this module."""
    global agent_id
    agent_id = _agent_id
    if agent_id:
        r = await client.get(f"/admin/agents/{agent_id}")
        if r.status_code == 200:
            yield agent_id
            return
    create = await client.post(
        "/admin/agents",
        json={
            "name": "UseCaseTestAgent",
            "description": "For use cases",
            "llm_model": "gpt-4",
        },
    )
    assert create.status_code == 201
    agent_id = create.json()["agent_id"]
    yield agent_id


@pytest.mark.asyncio
async def test_create_use_case(client, ensure_agent):
    """POST; assert 201, capture _uc_id."""
    global _uc_id
    payload = {
        "pregunta": "What is the capital of France?",
        "respuesta": "Paris is the capital of France.",
    }
    response = await client.post(
        f"/admin/agents/{agent_id}/use-cases",
        json=payload,
    )
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    _uc_id = data["id"]
    assert data["pregunta"] == payload["pregunta"]
    assert data["respuesta"] == payload["respuesta"]


@pytest.mark.asyncio
async def test_get_use_case_in_list(client, ensure_agent):
    """GET list; assert created item present."""
    response = await client.get(f"/admin/agents/{agent_id}/use-cases")
    assert response.status_code == 200
    items = response.json()["items"]
    ids = [u["id"] for u in items]
    assert _uc_id in ids
    uc = next(u for u in items if u["id"] == _uc_id)
    assert uc["pregunta"] == "What is the capital of France?"


@pytest.mark.asyncio
async def test_list_search_by_pregunta(client, ensure_agent):
    """Create 2 use cases with distinct preguntas; search one; assert only 1 returned (non-matching excluded)."""
    await client.post(
        f"/admin/agents/{agent_id}/use-cases",
        json={"pregunta": "UniquePreguntaAlpha", "respuesta": "A" * 10},
    )
    await client.post(
        f"/admin/agents/{agent_id}/use-cases",
        json={"pregunta": "DifferentPreguntaBeta", "respuesta": "B" * 10},
    )
    response = await client.get(
        f"/admin/agents/{agent_id}/use-cases",
        params={"search": "UniquePreguntaAlpha"},
    )
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["pregunta"] == "UniquePreguntaAlpha"
    assert "DifferentPreguntaBeta" not in [u["pregunta"] for u in items]


@pytest.mark.asyncio
async def test_list_search_by_respuesta(client, ensure_agent):
    """Search by word in respuesta; assert correct match (list only has respuesta_truncada)."""
    await client.post(
        f"/admin/agents/{agent_id}/use-cases",
        json={
            "pregunta": "Q about zebra",
            "respuesta": "The word giraffe appears only here in answer.",
        },
    )
    response = await client.get(
        f"/admin/agents/{agent_id}/use-cases",
        params={"search": "giraffe"},
    )
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) >= 1
    assert any("giraffe" in u["respuesta_truncada"] for u in items)


@pytest.mark.asyncio
async def test_list_respuesta_truncated_to_80(client, ensure_agent):
    """Create use case with 100-char respuesta; assert list item respuesta_truncada <= 80 chars."""
    long_answer = "x" * 100
    create = await client.post(
        f"/admin/agents/{agent_id}/use-cases",
        json={"pregunta": "Long answer question", "respuesta": long_answer},
    )
    assert create.status_code == 201
    uc_id = create.json()["id"]
    response = await client.get(f"/admin/agents/{agent_id}/use-cases")
    assert response.status_code == 200
    items = response.json()["items"]
    uc = next((u for u in items if u["id"] == uc_id), None)
    assert uc is not None
    assert "respuesta_truncada" in uc
    assert len(uc["respuesta_truncada"]) <= 80


@pytest.mark.asyncio
async def test_update_use_case(client, ensure_agent):
    """PUT; assert fields changed."""
    response = await client.put(
        f"/admin/agents/{agent_id}/use-cases/{_uc_id}",
        json={
            "pregunta": "Updated question?",
            "respuesta": "Updated answer with enough chars.",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["pregunta"] == "Updated question?"
    assert data["respuesta"] == "Updated answer with enough chars."


@pytest.mark.asyncio
async def test_random_returns_correct_count(client, ensure_agent):
    """Create enough use cases; GET random?limit=3 multiple times; assert exactly 3 each time (deterministic count)."""
    for i in range(4):
        await client.post(
            f"/admin/agents/{agent_id}/use-cases",
            json={"pregunta": f"Random Q {i}", "respuesta": "A" * 10},
        )
    for _ in range(
        3
    ):  # call 3 times to reduce reliance on a single non-deterministic sample
        response = await client.get(
            f"/admin/agents/{agent_id}/use-cases/random",
            params={"limit": 3},
        )
        if response.status_code == 404:
            pytest.fail(
                "GET /use-cases/random returned 404 — route ordering bug: "
                "/random must be declared before /{uc_id} so 'random' is not matched as uc_id"
            )
        assert response.status_code == 200
        items = response.json()
        assert len(items) == 3


@pytest.mark.asyncio
async def test_random_deleted_use_case_never_appears(client, ensure_agent):
    """Delete one use case; call random at least 5 times; assert deleted id never in results."""
    create = await client.post(
        f"/admin/agents/{agent_id}/use-cases",
        json={"pregunta": "To be deleted", "respuesta": "X" * 10},
    )
    assert create.status_code == 201
    to_delete_id = create.json()["id"]
    del_resp = await client.delete(f"/admin/agents/{agent_id}/use-cases/{to_delete_id}")
    assert del_resp.status_code == 204
    for _ in range(5):
        response = await client.get(
            f"/admin/agents/{agent_id}/use-cases/random",
            params={"limit": 10},
        )
        assert response.status_code == 200
        ids = [u["id"] for u in response.json()]
        assert to_delete_id not in ids


@pytest.mark.asyncio
async def test_delete_use_case(client, ensure_agent):
    """DELETE; assert 204."""
    response = await client.delete(f"/admin/agents/{agent_id}/use-cases/{_uc_id}")
    assert response.status_code == 204
    assert response.content == b"" or len(response.content) == 0


@pytest.mark.asyncio
async def test_deleted_use_case_not_in_list(client, ensure_agent):
    """GET list; assert deleted item gone."""
    response = await client.get(f"/admin/agents/{agent_id}/use-cases")
    assert response.status_code == 200
    ids = [u["id"] for u in response.json()["items"]]
    assert _uc_id not in ids


# --- Error paths ---


@pytest.mark.asyncio
async def test_create_use_case_respuesta_too_short(client, ensure_agent):
    """respuesta = 'short' (< 10 chars); assert 422."""
    response = await client.post(
        f"/admin/agents/{agent_id}/use-cases",
        json={"pregunta": "Q?", "respuesta": "short"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_use_case_missing_pregunta(client, ensure_agent):
    """No pregunta field; assert 422."""
    response = await client.post(
        f"/admin/agents/{agent_id}/use-cases",
        json={"respuesta": "A" * 10},
    )
    assert response.status_code == 422


# Step 4 — Adversarial: test_random_deleted calls random 5 times; test_list_search_by_pregunta
# creates non-matching use case and asserts only 1 returned; test_list_respuesta_truncated
# asserts len(item["respuesta_truncada"]) <= 80.
# Step 5 — Weakest part: test_random_returns_correct_count is most likely non-deterministic
# (single call could flake). Fixed by calling random 3 times and asserting exactly 3 items
# each time; never assert on exact ordering or identity.
