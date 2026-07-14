"""Use cases router — /random declared before /{uc_id}."""

from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import Response

from app.api.deps import get_use_case_service
from app.schemas.use_cases import (
    UseCaseCreate,
    UseCaseListItem,
    UseCaseListResponse,
    UseCaseRead,
    UseCaseUpdate,
)
from app.services.use_cases import UseCaseService

router = APIRouter(tags=["use_cases"])


@router.get("/agents/{agent_id}/use-cases/random", response_model=list[UseCaseRead])
async def get_random_use_cases(
    agent_id: UUID,
    limit: int = 10,
    use_case_service: UseCaseService = Depends(get_use_case_service),
) -> list[UseCaseRead]:
    items = await use_case_service.get_random(agent_id, limit)
    return [UseCaseRead.model_validate(u) for u in items]


@router.get("/agents/{agent_id}/use-cases/{uc_id}", response_model=UseCaseRead)
async def get_use_case(
    agent_id: UUID,
    uc_id: UUID,
    use_case_service: UseCaseService = Depends(get_use_case_service),
) -> UseCaseRead:
    entity = await use_case_service.get(agent_id, uc_id)
    return UseCaseRead.model_validate(entity)


@router.get(
    "/agents/{agent_id}/use-cases",
    response_model=UseCaseListResponse,
)
async def list_use_cases(
    agent_id: UUID,
    offset: int = 0,
    limit: int = 20,
    search: str | None = None,
    use_case_service: UseCaseService = Depends(get_use_case_service),
) -> UseCaseListResponse:
    items = await use_case_service.list(agent_id, offset, limit, search=search)
    return UseCaseListResponse(
        items=[UseCaseListItem.model_validate(u) for u in items],
        total=len(items),
        offset=offset,
        limit=limit,
    )


@router.post(
    "/agents/{agent_id}/use-cases",
    response_model=UseCaseRead,
    status_code=201,
)
async def create_use_case(
    agent_id: UUID,
    body: UseCaseCreate,
    use_case_service: UseCaseService = Depends(get_use_case_service),
) -> UseCaseRead:
    data = {"pregunta": body.pregunta, "respuesta": body.respuesta}
    entity = await use_case_service.create(agent_id, data)
    return UseCaseRead.model_validate(entity)


@router.put(
    "/agents/{agent_id}/use-cases/{uc_id}",
    response_model=UseCaseRead,
)
async def update_use_case(
    agent_id: UUID,
    uc_id: UUID,
    body: UseCaseUpdate,
    use_case_service: UseCaseService = Depends(get_use_case_service),
) -> UseCaseRead:
    data = {}
    if body.pregunta is not None:
        data["pregunta"] = body.pregunta
    if body.respuesta is not None:
        data["respuesta"] = body.respuesta
    entity = await use_case_service.update(agent_id, uc_id, data)
    return UseCaseRead.model_validate(entity)


@router.delete(
    "/agents/{agent_id}/use-cases/{uc_id}",
    status_code=204,
)
async def delete_use_case(
    agent_id: UUID,
    uc_id: UUID,
    use_case_service: UseCaseService = Depends(get_use_case_service),
) -> Response:
    await use_case_service.delete(agent_id, uc_id)
    return Response(status_code=204)
