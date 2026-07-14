"""Costs router — GET organizations costs from conversation-service."""

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_conversation_service
from app.schemas.cost import (
    CostBreakdownResponse,
    OrganizationConversationsCostsResponse,
    OrganizationCostsResponse,
)
from app.services.conversations import ConversationService

router = APIRouter(tags=["costs"])


@router.get("/costs/breakdown", response_model=CostBreakdownResponse)
async def get_cost_breakdown(
    conversation_service: ConversationService = Depends(get_conversation_service),
) -> CostBreakdownResponse:
    data = await conversation_service.get_cost_breakdown()
    return CostBreakdownResponse(**data)


@router.get("/costs/organizations", response_model=OrganizationCostsResponse)
async def list_organizations_costs(
    month: int | None = Query(None, ge=1, le=12, description="Filter by month (1-12)"),
    year: int | None = Query(None, ge=2020, le=2030, description="Filter by year"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100),
    conversation_service: ConversationService = Depends(get_conversation_service),
) -> OrganizationCostsResponse:
    """List all organizations with their cost statistics."""
    data = await conversation_service.list_organizations_costs(
        month=month,
        year=year,
        offset=(page - 1) * limit,
        limit=limit,
    )
    return OrganizationCostsResponse(**data)


@router.get(
    "/costs/organizations/{organization_id}/conversations",
    response_model=OrganizationConversationsCostsResponse,
)
async def list_organization_conversations_cost(
    organization_id: str,
    month: int | None = Query(None, ge=1, le=12, description="Filter by month (1-12)"),
    year: int | None = Query(None, ge=2020, le=2030, description="Filter by year"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100),
    conversation_service: ConversationService = Depends(get_conversation_service),
) -> OrganizationConversationsCostsResponse:
    """List conversations with cost breakdown for a specific organization."""
    data = await conversation_service.list_organization_conversations_cost(
        organization_id=organization_id,
        month=month,
        year=year,
        offset=(page - 1) * limit,
        limit=limit,
    )
    return OrganizationConversationsCostsResponse(**data)
