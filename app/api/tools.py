"""Tools router — catalog CRUD + agent tools; active_count from same list in router."""

from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import Response

from app.api.deps import get_tool_service
from app.schemas.tools import (
    AgentToolAttach,
    AgentToolListResponse,
    AgentToolPatch,
    AgentToolRead,
    ToolCreate,
    ToolRead,
    ToolUpdate,
)
from app.services.tools import ToolService

router = APIRouter(tags=["tools"])


# --- Catalog (unscoped) ---


@router.get("/tools", response_model=list[ToolRead])
async def list_tools(
    page: int = 1,
    limit: int = 20,
    tool_service: ToolService = Depends(get_tool_service),
) -> list[ToolRead]:
    offset = (page - 1) * limit
    items = await tool_service.list_tools(offset, limit)
    return [ToolRead.model_validate(t) for t in items]


@router.post("/tools", response_model=ToolRead, status_code=201)
async def create_tool(
    body: ToolCreate,
    tool_service: ToolService = Depends(get_tool_service),
) -> ToolRead:
    data = {
        "name": body.name,
        "description": body.description,
        "function_ref": body.function_ref,
    }
    entity = await tool_service.create_tool(data)
    return ToolRead.model_validate(entity)


@router.get("/tools/{tool_id}", response_model=ToolRead)
async def get_tool(
    tool_id: UUID,
    tool_service: ToolService = Depends(get_tool_service),
) -> ToolRead:
    entity = await tool_service.get_tool(tool_id)
    return ToolRead.model_validate(entity)


@router.patch("/tools/{tool_id}", response_model=ToolRead)
async def update_tool(
    tool_id: UUID,
    body: ToolUpdate,
    tool_service: ToolService = Depends(get_tool_service),
) -> ToolRead:
    data = {}
    if body.name is not None:
        data["name"] = body.name
    if body.description is not None:
        data["description"] = body.description
    if body.function_ref is not None:
        data["function_ref"] = body.function_ref
    entity = await tool_service.update_tool(tool_id, data)
    return ToolRead.model_validate(entity)


@router.delete("/tools/{tool_id}", status_code=204)
async def delete_tool(
    tool_id: UUID,
    tool_service: ToolService = Depends(get_tool_service),
) -> Response:
    await tool_service.delete_tool(tool_id)
    return Response(status_code=204)


# --- Agent tools (scoped by agent_id) ---


@router.get(
    "/agents/{agent_id}/tools",
    response_model=AgentToolListResponse,
)
async def list_agent_tools(
    agent_id: UUID,
    tool_service: ToolService = Depends(get_tool_service),
) -> AgentToolListResponse:
    items = await tool_service.list_by_agent(agent_id)
    # active_count computed in router from the same list that is serialized
    active_count = sum(1 for t in items if t.is_active)
    read_items = [
        AgentToolRead(
            agent_id=at.agent_id,
            tool_id=at.tool_id,
            is_active=at.is_active,
            name=at.name or "",
            description=at.description or "",
        )
        for at in items
    ]
    return AgentToolListResponse(items=read_items, active_count=active_count)


@router.post(
    "/agents/{agent_id}/tools",
    response_model=AgentToolRead,
    status_code=201,
)
async def attach_tool(
    agent_id: UUID,
    body: AgentToolAttach,
    tool_service: ToolService = Depends(get_tool_service),
) -> AgentToolRead:
    entity = await tool_service.attach(agent_id, body.tool_id)
    return AgentToolRead(
        agent_id=entity.agent_id,
        tool_id=entity.tool_id,
        is_active=entity.is_active,
        name=entity.name or "",
        description=entity.description or "",
    )


@router.delete(
    "/agents/{agent_id}/tools/{tool_id}",
    status_code=204,
)
async def detach_tool(
    agent_id: UUID,
    tool_id: UUID,
    tool_service: ToolService = Depends(get_tool_service),
) -> Response:
    await tool_service.detach(agent_id, tool_id)
    return Response(status_code=204)


@router.patch(
    "/agents/{agent_id}/tools/{tool_id}/active",
    response_model=AgentToolRead,
)
async def set_agent_tool_active(
    agent_id: UUID,
    tool_id: UUID,
    body: AgentToolPatch,
    tool_service: ToolService = Depends(get_tool_service),
) -> AgentToolRead:
    entity = await tool_service.set_active(agent_id, tool_id, body.is_active)
    return AgentToolRead(
        agent_id=entity.agent_id,
        tool_id=entity.tool_id,
        is_active=entity.is_active,
        name=entity.name or "",
        description=entity.description or "",
    )


@router.patch(
    "/agents/{agent_id}/tools/{tool_id}/toggle",
    response_model=AgentToolRead,
)
async def toggle_agent_tool(
    agent_id: UUID,
    tool_id: UUID,
    tool_service: ToolService = Depends(get_tool_service),
) -> AgentToolRead:
    """Flip is_active for the agent-tool association; no request body."""
    entity = await tool_service.toggle(agent_id, tool_id)
    return AgentToolRead(
        agent_id=entity.agent_id,
        tool_id=entity.tool_id,
        is_active=entity.is_active,
        name=entity.name or "",
        description=entity.description or "",
    )
