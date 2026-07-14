"""Unit tests for AgentService.delete and get_bot_status."""

import unittest.mock as mock
from uuid import uuid4

import httpx
import pytest

from app.domain.agents.exceptions import AgentNotFound, PhoneAccountNotLinked
from app.domain.documents.exceptions import AgentServiceUnavailable
from app.grpc.generated.hermes.v2 import whatsapp_pb2
from app.services.agents import AgentService
from tests.conftest import FakeSession
from tests.unit.factories import make_agent
from tests.unit.fakes.agents import InMemoryAgentRepository


def _make_client(status_code: int = 200):
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code)

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


@pytest.mark.asyncio
async def test_delete_calls_agent_vectors_before_repo_delete():
    """DELETE to agent/agents/{id}/vectors runs before the agent row is removed."""
    calls: list[str] = []

    async def capture(request: httpx.Request) -> httpx.Response:
        calls.append(request.method + " " + str(request.url))
        return httpx.Response(200)

    client = httpx.AsyncClient(transport=httpx.MockTransport(capture))
    repo = InMemoryAgentRepository()
    session = FakeSession()
    agent = make_agent(status="inactive")
    await repo.create(agent)
    svc = AgentService(
        repo=repo,
        session=session,
        http_client=client,
        agent_service_url="http://agent-service",
    )
    await svc.delete(agent.id)
    assert len(calls) == 1
    assert "DELETE" in calls[0]
    assert f"/agent/agents/{agent.id}/vectors" in calls[0]
    assert await repo.get(agent.id) is None


@pytest.mark.asyncio
async def test_delete_agent_vector_404_still_deletes_db():
    client = _make_client(404)
    repo = InMemoryAgentRepository()
    session = FakeSession()
    agent = make_agent(status="inactive")
    await repo.create(agent)
    svc = AgentService(
        repo=repo,
        session=session,
        http_client=client,
        agent_service_url="http://agent-service",
    )
    await svc.delete(agent.id)
    assert await repo.get(agent.id) is None


@pytest.mark.asyncio
async def test_delete_agent_vector_500_raises_and_keeps_agent():
    client = _make_client(500)
    repo = InMemoryAgentRepository()
    session = FakeSession()
    agent = make_agent(status="inactive")
    await repo.create(agent)
    svc = AgentService(
        repo=repo,
        session=session,
        http_client=client,
        agent_service_url="http://agent-service",
    )
    with pytest.raises(AgentServiceUnavailable):
        await svc.delete(agent.id)
    got = await repo.get(agent.id)
    assert got is not None
    assert got.id == agent.id


@pytest.mark.asyncio
async def test_delete_agent_network_error_raises():
    async def boom(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("nope")

    client = httpx.AsyncClient(transport=httpx.MockTransport(boom))
    repo = InMemoryAgentRepository()
    session = FakeSession()
    agent = make_agent(status="inactive")
    await repo.create(agent)
    svc = AgentService(
        repo=repo,
        session=session,
        http_client=client,
        agent_service_url="http://agent-service",
    )
    with pytest.raises(AgentServiceUnavailable):
        await svc.delete(agent.id)
    assert await repo.get(agent.id) is not None


# ---------------------------------------------------------------------------
# get_bot_status
# ---------------------------------------------------------------------------


def _make_fake_hermes(
    account_id="acc-1", status="BOT_STATUS_CONNECTED", phone="5355551234", qr=""
):
    """Return a mock HermesClient whose whatsapp.GetBotStatus returns a fake response."""
    fake_response = mock.MagicMock()
    fake_response.accountId = account_id
    fake_response.status = status
    fake_response.phoneNumber = phone
    fake_response.qrCode = qr

    hermes = mock.MagicMock()
    hermes.whatsapp.GetBotStatus = mock.AsyncMock(return_value=fake_response)
    return hermes


@pytest.mark.asyncio
async def test_get_bot_status_returns_status_data():
    """get_bot_status returns accountId, status, phoneNumber, qrCode from hermes."""
    repo = InMemoryAgentRepository()
    session = FakeSession()
    agent = make_agent(phone_account_id="acc-abc")
    await repo.create(agent)

    hermes = _make_fake_hermes(
        account_id="acc-abc", status="BOT_STATUS_CONNECTED", phone="5355551234"
    )
    svc = AgentService(
        repo=repo,
        session=session,
        http_client=_make_client(),
        agent_service_url="http://agent-service",
        hermes_client=hermes,
    )

    result = await svc.get_bot_status(agent.id)

    assert result["account_id"] == "acc-abc"
    assert result["status"] == "BOT_STATUS_CONNECTED"
    assert result["phone_number"] == "5355551234"
    assert result["qr_code"] == ""
    hermes.whatsapp.GetBotStatus.assert_awaited_once_with(
        whatsapp_pb2.GetBotStatusRequest(accountId="acc-abc")
    )


@pytest.mark.asyncio
async def test_get_bot_status_raises_when_no_phone_account():
    """get_bot_status raises PhoneAccountNotLinked when phone_account_id is None."""
    repo = InMemoryAgentRepository()
    session = FakeSession()
    agent = make_agent(phone_account_id=None)
    await repo.create(agent)

    svc = AgentService(
        repo=repo,
        session=session,
        http_client=_make_client(),
        agent_service_url="http://agent-service",
    )

    with pytest.raises(PhoneAccountNotLinked):
        await svc.get_bot_status(agent.id)


@pytest.mark.asyncio
async def test_get_bot_status_raises_when_agent_not_found():
    """get_bot_status raises AgentNotFound for unknown agent_id."""
    repo = InMemoryAgentRepository()
    session = FakeSession()

    svc = AgentService(
        repo=repo,
        session=session,
        http_client=_make_client(),
        agent_service_url="http://agent-service",
    )

    with pytest.raises(AgentNotFound):
        await svc.get_bot_status(uuid4())


# ---------------------------------------------------------------------------
# activate_phone_account
# ---------------------------------------------------------------------------


def _make_activate_hermes(success: bool = True, message: str = "ok"):
    """Return a mock HermesClient whose whatsapp.ActivateAccount returns a fake response."""
    fake_response = mock.MagicMock()
    fake_response.success = success
    fake_response.message = message

    hermes = mock.MagicMock()
    hermes.whatsapp.ActivateAccount = mock.AsyncMock(return_value=fake_response)
    return hermes


@pytest.mark.asyncio
async def test_activate_phone_account_calls_hermes():
    """activate_phone_account calls ActivateAccount with accountId and businessDni=agent_id."""
    repo = InMemoryAgentRepository()
    session = FakeSession()
    agent = make_agent(phone_account_id="acc-xyz")
    await repo.create(agent)

    hermes = _make_activate_hermes(success=True)
    svc = AgentService(
        repo=repo,
        session=session,
        http_client=_make_client(),
        agent_service_url="http://agent-service",
        hermes_client=hermes,
    )

    await svc.activate_phone_account(agent.id)

    hermes.whatsapp.ActivateAccount.assert_awaited_once_with(
        whatsapp_pb2.ActivateAccountRequest(
            accountId="acc-xyz",
            businessDni=str(agent.id),
        )
    )


@pytest.mark.asyncio
async def test_activate_phone_account_raises_on_hermes_failure():
    """activate_phone_account raises RuntimeError when hermes returns success=False."""
    repo = InMemoryAgentRepository()
    session = FakeSession()
    agent = make_agent(phone_account_id="acc-xyz")
    await repo.create(agent)

    hermes = _make_activate_hermes(success=False, message="account not found")
    svc = AgentService(
        repo=repo,
        session=session,
        http_client=_make_client(),
        agent_service_url="http://agent-service",
        hermes_client=hermes,
    )

    with pytest.raises(RuntimeError, match="account not found"):
        await svc.activate_phone_account(agent.id)


@pytest.mark.asyncio
async def test_activate_phone_account_raises_when_no_phone_account():
    """activate_phone_account raises PhoneAccountNotLinked when phone_account_id is None."""
    repo = InMemoryAgentRepository()
    session = FakeSession()
    agent = make_agent(phone_account_id=None)
    await repo.create(agent)

    svc = AgentService(
        repo=repo,
        session=session,
        http_client=_make_client(),
        agent_service_url="http://agent-service",
    )

    with pytest.raises(PhoneAccountNotLinked):
        await svc.activate_phone_account(agent.id)
