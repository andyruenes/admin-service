"""Unit tests for ToolService."""

from uuid import uuid4

import pytest

from app.domain.tools.exceptions import AgentToolNotFound, ToolNotFound
from app.services.tools import ToolService
from tests.conftest import FakeSession
from tests.unit.factories import make_tool
from tests.unit.fakes.tools import InMemoryToolRepository


@pytest.fixture
def repo():
    return InMemoryToolRepository()


@pytest.fixture
def session():
    return FakeSession()


@pytest.fixture
def service(repo, session):
    return ToolService(repo=repo, session=session)


@pytest.mark.asyncio
async def test_list_agent_tools_returns_all_catalog(service, repo):
    agent_id = uuid4()
    for i in range(3):
        tool = make_tool(name=f"tool_{i}")
        await repo.create(tool)
        await repo.attach(agent_id, tool.id)
    items = await service.list_by_agent(agent_id)
    assert len(items) == 3


@pytest.mark.asyncio
async def test_list_agent_tools_correct_is_active(service, repo):
    agent_id = uuid4()
    tool_a = make_tool(name="tool_a")
    tool_b = make_tool(name="tool_b")
    await repo.create(tool_a)
    await repo.create(tool_b)
    await repo.attach(agent_id, tool_a.id)
    await repo.attach(agent_id, tool_b.id)
    await service.set_active(agent_id, tool_a.id, True)
    items = await service.list_by_agent(agent_id)
    assert len(items) == 2
    by_tool = {a.tool_id: a for a in items}
    assert by_tool[tool_a.id].is_active is True
    assert by_tool[tool_b.id].is_active is False


@pytest.mark.asyncio
async def test_toggle_active_becomes_inactive(service, repo):
    agent_id = uuid4()
    tool = make_tool(name="t")
    await repo.create(tool)
    await repo.attach(agent_id, tool.id)
    await service.set_active(agent_id, tool.id, True)
    await service.toggle(agent_id, tool.id)
    items = await service.list_by_agent(agent_id)
    at = next(a for a in items if a.tool_id == tool.id)
    assert at.is_active is False


@pytest.mark.asyncio
async def test_toggle_inactive_becomes_active(service, repo):
    agent_id = uuid4()
    tool = make_tool(name="t")
    await repo.create(tool)
    await repo.attach(agent_id, tool.id)
    assert (
        next(
            a for a in await service.list_by_agent(agent_id) if a.tool_id == tool.id
        ).is_active
        is False
    )
    await service.toggle(agent_id, tool.id)
    items = await service.list_by_agent(agent_id)
    at = next(a for a in items if a.tool_id == tool.id)
    assert at.is_active is True


@pytest.mark.asyncio
async def test_toggle_returns_updated_agent_tool(service, repo):
    agent_id = uuid4()
    tool = make_tool(name="t")
    await repo.create(tool)
    await repo.attach(agent_id, tool.id)
    returned = await service.toggle(agent_id, tool.id)
    assert returned.is_active is True
    returned2 = await service.toggle(agent_id, tool.id)
    assert returned2.is_active is False


@pytest.mark.asyncio
async def test_create_catalog_tool(service, repo):
    data = {"name": "my_tool", "description": "Desc", "function_ref": "ref://x"}
    created = await service.create_tool(data)
    assert created.name == "my_tool"
    got = await service.get_tool(created.id)
    assert got.id == created.id


@pytest.mark.asyncio
async def test_delete_catalog_tool_removes_it(service, repo):
    created = await service.create_tool(
        {"name": "x", "description": "d", "function_ref": "r"}
    )
    await service.delete_tool(created.id)
    with pytest.raises(ToolNotFound):
        await service.get_tool(created.id)


@pytest.mark.asyncio
async def test_toggle_not_attached_raises(service, repo):
    agent_id = uuid4()
    tool = make_tool(name="t")
    await repo.create(tool)
    with pytest.raises(AgentToolNotFound):
        await service.toggle(agent_id, tool.id)


@pytest.mark.asyncio
async def test_delete_catalog_tool_not_found_raises(service):
    with pytest.raises(ToolNotFound):
        await service.delete_tool(uuid4())
