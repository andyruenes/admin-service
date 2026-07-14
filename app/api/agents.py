"""Agents router — GET uses page/limit -> offset; POST returns agent_id only."""

import json
from collections.abc import AsyncGenerator
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import Response, StreamingResponse

from app.api.deps import get_agent_service, get_hermes_client
from app.domain.agents.exceptions import PhoneAccountNotLinked
from app.grpc.generated.hermes.v2 import whatsapp_pb2
from app.grpc.hermes.client import HermesClient
from app.schemas.agents import (
    AgentCreate,
    AgentListItem,
    AgentListResponse,
    AgentRead,
    AgentUpdate,
    BotStatusResponse,
    ChangeStatusRequest,
    PhoneAccountResponse,
)
from app.services.agents import AgentService

router = APIRouter(tags=["agents"])


@router.get("/agents", response_model=AgentListResponse)
async def list_agents(
    page: int = 1,
    limit: int = 20,
    status: str | None = None,
    search: str | None = None,
    agent_service: AgentService = Depends(get_agent_service),
) -> AgentListResponse:
    offset = (page - 1) * limit
    items = await agent_service.list(status, offset, limit, search=search)
    total = await agent_service.count(status=status, search=search)
    return AgentListResponse(
        items=[AgentListItem.model_validate(a) for a in items],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.post("/agents", status_code=201)
async def create_agent(
    body: AgentCreate,
    agent_service: AgentService = Depends(get_agent_service),
) -> dict[str, str]:
    data = {
        "name": body.name,
        "description": body.description,
        "llm_model": body.llm_model,
        "status": body.status,
    }
    agent = await agent_service.create(data)
    return {"agent_id": str(agent.id)}


@router.get("/agents/{agent_id}", response_model=AgentRead)
async def get_agent(
    agent_id: UUID,
    agent_service: AgentService = Depends(get_agent_service),
) -> AgentRead:
    entity = await agent_service.get(agent_id)
    return AgentRead.model_validate(entity)


@router.put("/agents/{agent_id}", response_model=AgentRead)
async def update_agent(
    agent_id: UUID,
    body: AgentUpdate,
    agent_service: AgentService = Depends(get_agent_service),
) -> AgentRead:
    data = {}
    if body.name is not None:
        data["name"] = body.name
    if body.description is not None:
        data["description"] = body.description
    if body.llm_model is not None:
        data["llm_model"] = body.llm_model
    if body.status is not None:
        data["status"] = body.status
    entity = await agent_service.update(agent_id, data)
    return AgentRead.model_validate(entity)


@router.patch("/agents/{agent_id}/status", response_model=AgentRead)
async def change_agent_status(
    agent_id: UUID,
    body: ChangeStatusRequest,
    agent_service: AgentService = Depends(get_agent_service),
) -> AgentRead:
    entity = await agent_service.change_status(agent_id, body.status)
    return AgentRead.model_validate(entity)


@router.post(
    "/agents/{agent_id}/phone-account",
    status_code=201,
    response_model=PhoneAccountResponse,
)
async def create_phone_account(
    agent_id: UUID,
    agent_service: AgentService = Depends(get_agent_service),
) -> PhoneAccountResponse:
    phone_account_id = await agent_service.create_phone_account(agent_id)
    return PhoneAccountResponse(agent_id=agent_id, phone_account_id=phone_account_id)


@router.post("/agents/{agent_id}/phone-account/activate", status_code=202)
async def activate_phone_account(
    agent_id: UUID,
    agent_service: AgentService = Depends(get_agent_service),
) -> Response:
    await agent_service.activate_phone_account(agent_id)
    return Response(status_code=202)


@router.get("/agents/{agent_id}/phone-account/status", response_model=BotStatusResponse)
async def get_bot_status(
    agent_id: UUID,
    agent_service: AgentService = Depends(get_agent_service),
) -> BotStatusResponse:
    data = await agent_service.get_bot_status(agent_id)
    return BotStatusResponse(**data)


@router.post("/agents/{agent_id}/phone-account/qr", status_code=202)
async def request_qr(
    agent_id: UUID,
    agent_service: AgentService = Depends(get_agent_service),
) -> Response:
    await agent_service.request_qr(agent_id)
    return Response(status_code=202)


@router.get("/agents/{agent_id}/phone-account/stream")
async def stream_bot_updates(
    agent_id: UUID,
    agent_service: AgentService = Depends(get_agent_service),
    hermes_client: HermesClient = Depends(get_hermes_client),
) -> StreamingResponse:
    agent = await agent_service.get(agent_id)
    if agent.phone_account_id is None:
        raise PhoneAccountNotLinked(f"Agent {agent_id} has no linked phone account")

    account_id = agent.phone_account_id

    async def event_stream() -> AsyncGenerator[str, None]:
        grpc_stream = hermes_client.whatsapp.StreamBotUpdates(
            whatsapp_pb2.BotUpdateRequest(accountId=account_id)
        )
        async for update in grpc_stream:
            payload = json.dumps(
                {
                    "accountId": update.accountId,
                    "status": update.status,
                    "qrCode": update.qrCode,
                    "phoneNumber": update.phoneNumber,
                    "message": update.message,
                }
            )
            yield f"data: {payload}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.delete("/agents/{agent_id}", status_code=204)
async def delete_agent(
    agent_id: UUID,
    agent_service: AgentService = Depends(get_agent_service),
) -> Response:
    await agent_service.delete(agent_id)
    return Response(status_code=204)
