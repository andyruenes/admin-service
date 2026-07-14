from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.schemas.common import PaginatedResponse


class OrganizationCostListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    organization_id: str
    created_at: datetime
    is_active: bool
    total_conversations: int
    total_cost: float
    input_tokens: int
    input_cost: float
    output_tokens: int
    output_cost: float
    cache_tokens: int
    cache_cost: float
    agents_count: int


class MonthlyCost(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    month: str
    total_cost: float


class OrganizationCostsResponse(BaseModel):
    items: list[OrganizationCostListItem]
    monthly_evolution: list[MonthlyCost]
    total: int
    offset: int
    limit: int


class ConversationCostListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    session_id: UUID
    user_id: str
    input_tokens: int
    output_tokens: int
    cache_tokens: int
    input_cost: float
    output_cost: float
    cache_cost: float
    total_cost: float
    is_open: bool
    closed_at: datetime | None


OrganizationConversationsCostsResponse = PaginatedResponse[ConversationCostListItem]


class TokenBreakdown(BaseModel):
    tokens: int
    cost: float
    percentage: float


class ModelCost(BaseModel):
    model: str
    cost: float
    percentage: float


class CostBreakdownResponse(BaseModel):
    input_tokens: TokenBreakdown
    output_tokens: TokenBreakdown
    cache_tokens: TokenBreakdown
    by_model: list[ModelCost]
