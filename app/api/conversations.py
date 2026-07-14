"""Conversations router — GET clients list from conversation-service."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_conversation_service
from app.schemas.conversations import (
    ClientsListResponse,
    ConversationDetailResponse,
    ConversationMetricsResponse,
    UserConversationsResponse,
)
from app.services.conversations import ConversationService

router = APIRouter(tags=["conversations"])


@router.get("/conversations/metrics", response_model=ConversationMetricsResponse)
async def get_conversation_metrics(
    conversation_service: ConversationService = Depends(get_conversation_service),
) -> ConversationMetricsResponse:
    data = await conversation_service.get_metrics()
    return ConversationMetricsResponse(**data)


@router.get("/conversations/count")
async def count_open_conversations(
    conversation_service: ConversationService = Depends(get_conversation_service),
) -> dict[str, int]:
    count = await conversation_service.count_open_conversations()
    return {"count": count}


@router.get("/conversations/users", response_model=ClientsListResponse)
async def list_clients(
    search: str | None = Query(None, description="Filter by username"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    conversation_service: ConversationService = Depends(get_conversation_service),
) -> ClientsListResponse:
    """List all users with their conversation statistics."""
    offset = (page - 1) * limit
    items = await conversation_service.list_clients(
        search=search, offset=offset, limit=limit
    )
    total = await conversation_service.count_clients(search=search)
    return ClientsListResponse(
        items=items,
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get(
    "/conversations/users/{user_id}/conversations",
    response_model=UserConversationsResponse,
)
async def list_user_conversations(
    user_id: str,
    status: str | None = Query(None, description="Filter by status: open or closed"),
    date_from: datetime | None = Query(
        None, description="Filter conversations from this date"
    ),
    date_to: datetime | None = Query(
        None, description="Filter conversations until this date"
    ),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    conversation_service: ConversationService = Depends(get_conversation_service),
) -> UserConversationsResponse:
    offset = (page - 1) * limit
    items = await conversation_service.list_user_conversations(
        user_id=user_id,
        status=status,
        date_from=date_from,
        date_to=date_to,
        offset=offset,
        limit=limit,
    )
    total = await conversation_service.count_user_conversations(
        user_id=user_id,
        status=status,
        date_from=date_from,
        date_to=date_to,
    )
    return UserConversationsResponse(
        items=items,
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get(
    "/conversations/users/{user_id}/sessions/{session_id}",
    response_model=ConversationDetailResponse,
)
async def get_conversation_detail(
    user_id: str,
    session_id: str,
    conversation_service: ConversationService = Depends(get_conversation_service),
) -> ConversationDetailResponse:
    """Return the metadata of a single conversation (session)."""
    data = await conversation_service.get_conversation_detail(session_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return ConversationDetailResponse(**data)
