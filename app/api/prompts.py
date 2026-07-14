"""Prompts router — agent-scoped; version_number as int path param."""

from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.deps import get_prompt_service
from app.schemas.prompts import (
    PromptRead,
    PromptVersionListResponse,
    PromptVersionSummary,
    SavePromptRequest,
)
from app.services.prompts import PromptService

router = APIRouter(tags=["prompts"])


@router.get(
    "/agents/{agent_id}/prompt",
    response_model=PromptRead,
)
async def get_active_prompt(
    agent_id: UUID,
    prompt_service: PromptService = Depends(get_prompt_service),
) -> PromptRead:
    entity = await prompt_service.get_active_or_empty(agent_id)
    return PromptRead.model_validate(entity)


@router.put(
    "/agents/{agent_id}/prompt",
    response_model=PromptRead,
)
async def save_prompt(
    agent_id: UUID,
    body: SavePromptRequest,
    prompt_service: PromptService = Depends(get_prompt_service),
) -> PromptRead:
    entity = await prompt_service.save_as_active(agent_id, body.content)
    return PromptRead.model_validate(entity)


@router.get(
    "/agents/{agent_id}/prompt/versions",
    response_model=PromptVersionListResponse,
)
async def list_prompt_versions(
    agent_id: UUID,
    limit: int = 10,
    prompt_service: PromptService = Depends(get_prompt_service),
) -> PromptVersionListResponse:
    items = await prompt_service.list_versions(agent_id, limit)
    return PromptVersionListResponse(
        items=[PromptVersionSummary.model_validate(p) for p in items]
    )


@router.get(
    "/agents/{agent_id}/prompt/versions/{version_number}",
    response_model=PromptRead,
)
async def get_prompt_version(
    agent_id: UUID,
    version_number: int,
    prompt_service: PromptService = Depends(get_prompt_service),
) -> PromptRead:
    entity = await prompt_service.get_version(agent_id, version_number)
    return PromptRead.model_validate(entity)


@router.post(
    "/agents/{agent_id}/prompt/versions/{version_number}/restore",
    response_model=PromptRead,
)
async def restore_prompt_version(
    agent_id: UUID,
    version_number: int,
    prompt_service: PromptService = Depends(get_prompt_service),
) -> PromptRead:
    entity = await prompt_service.restore_version(agent_id, version_number)
    return PromptRead.model_validate(entity)
