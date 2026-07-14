"""Unit tests for UseCaseService."""

from uuid import uuid4

import pytest

from app.domain.use_cases.exceptions import UseCaseNotFound
from app.services.use_cases import UseCaseService
from tests.conftest import FakeSession
from tests.unit.factories import make_use_case
from tests.unit.fakes.use_cases import InMemoryUseCaseRepository


@pytest.fixture
def repo():
    return InMemoryUseCaseRepository()


@pytest.fixture
def session():
    return FakeSession()


@pytest.fixture
def service(repo, session):
    return UseCaseService(repo=repo, session=session)


@pytest.mark.asyncio
async def test_create_use_case_scoped_to_agent(service, repo):
    agent_id = uuid4()
    data = {"pregunta": "Q?", "respuesta": "A" * 10}
    created = await service.create(agent_id, data)
    assert created.agent_id == agent_id
    assert created.question == "Q?"
    assert created.answer == "A" * 10


@pytest.mark.asyncio
async def test_get_use_case_found(service, repo):
    agent_id = uuid4()
    uc = make_use_case(agent_id=agent_id, question="Q?", answer="A" * 10)
    await repo.create(uc)
    got = await service.get(agent_id, uc.id)
    assert got.id == uc.id
    assert got.question == "Q?"


@pytest.mark.asyncio
async def test_list_use_cases_by_agent(service, repo):
    agent_id = uuid4()
    other_agent = uuid4()
    uc1 = make_use_case(agent_id=agent_id, question="One", answer="A" * 10)
    uc2 = make_use_case(agent_id=agent_id, question="Two", answer="B" * 10)
    uc_other = make_use_case(agent_id=other_agent, question="Other", answer="C" * 10)
    await repo.create(uc1)
    await repo.create(uc2)
    await repo.create(uc_other)
    items = await service.list(agent_id, 0, 10)
    assert len(items) == 2
    ids = {u.id for u in items}
    assert uc1.id in ids
    assert uc2.id in ids
    assert uc_other.id not in ids


@pytest.mark.asyncio
async def test_list_use_cases_search_filters_pregunta(service, repo):
    agent_id = uuid4()
    other_agent = uuid4()
    needle = make_use_case(
        agent_id=agent_id, question="needle-in-pregunta", answer="A" * 10
    )
    other = make_use_case(agent_id=agent_id, question="other-question", answer="B" * 10)
    other_agent_uc = make_use_case(
        agent_id=other_agent, question="needle-elsewhere", answer="C" * 10
    )
    await repo.create(needle)
    await repo.create(other)
    await repo.create(other_agent_uc)
    items = await service.list(agent_id, 0, 10)
    assert len(items) == 2
    questions = [u.question for u in items]
    assert "needle-in-pregunta" in questions
    assert "other-question" in questions
    assert "needle-elsewhere" not in questions
    assert sum(1 for u in items if "needle" in u.question) == 1


@pytest.mark.asyncio
async def test_list_use_cases_search_filters_respuesta(service, repo):
    agent_id = uuid4()
    other_agent = uuid4()
    needle = make_use_case(
        agent_id=agent_id, question="Q?", answer="needle-in-respuesta" + "x" * 10
    )
    other = make_use_case(
        agent_id=agent_id, question="Q2?", answer="other-answer" + "x" * 10
    )
    other_agent_uc = make_use_case(
        agent_id=other_agent, question="Q3?", answer="needle-elsewhere" + "x" * 10
    )
    await repo.create(needle)
    await repo.create(other)
    await repo.create(other_agent_uc)
    items = await service.list(agent_id, 0, 10)
    assert len(items) == 2
    answers = [u.answer for u in items]
    assert any("needle-in-respuesta" in a for a in answers)
    assert any("other-answer" in a for a in answers)
    assert sum(1 for u in items if "needle-in-respuesta" in u.answer) == 1


@pytest.mark.asyncio
async def test_update_use_case_changes_fields(service, repo):
    agent_id = uuid4()
    uc = make_use_case(agent_id=agent_id, question="Old", answer="A" * 10)
    await repo.create(uc)
    updated = await service.update(
        agent_id,
        uc.id,
        {"pregunta": "NewQ", "respuesta": "NewAnswer" + "x" * 10},
    )
    assert updated.question == "NewQ"
    assert "NewAnswer" in updated.answer


@pytest.mark.asyncio
async def test_delete_use_case_removes_from_list(service, repo):
    agent_id = uuid4()
    uc = make_use_case(agent_id=agent_id, question="Q?", answer="A" * 10)
    await repo.create(uc)
    await service.delete(agent_id, uc.id)
    items = await service.list(agent_id, 0, 10)
    assert len(items) == 0
    assert uc.id not in [u.id for u in items]


@pytest.mark.asyncio
async def test_get_random_returns_correct_count(service, repo):
    agent_id = uuid4()
    for i in range(5):
        uc = make_use_case(agent_id=agent_id, question=f"Q{i}?", answer="A" * 10)
        await repo.create(uc)
    result = await service.get_random(agent_id, limit=3)
    assert len(result) == 3


@pytest.mark.asyncio
async def test_get_random_scoped_to_agent(service, repo):
    agent_id = uuid4()
    other_agent = uuid4()
    for i in range(3):
        await repo.create(
            make_use_case(agent_id=agent_id, question=f"Q{i}?", answer="A" * 10)
        )
    await repo.create(
        make_use_case(agent_id=other_agent, question="Other", answer="B" * 10)
    )
    result = await service.get_random(agent_id, limit=10)
    assert len(result) == 3
    assert all(u.agent_id == agent_id for u in result)


@pytest.mark.asyncio
async def test_get_use_case_not_found_raises(service):
    with pytest.raises(UseCaseNotFound):
        await service.get(uuid4(), uuid4())


@pytest.mark.asyncio
async def test_get_use_case_wrong_agent_raises(service, repo):
    agent_id = uuid4()
    other_agent = uuid4()
    uc = make_use_case(agent_id=agent_id, question="Q?", answer="A" * 10)
    await repo.create(uc)
    with pytest.raises(UseCaseNotFound):
        await service.get(other_agent, uc.id)
