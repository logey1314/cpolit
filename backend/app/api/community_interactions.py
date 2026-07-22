from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.result import Result
from app.schemas.community_interaction import (
    CommunityInteractionMessagePageOut,
    NoiseFilterResult,
)
from app.services.community_interaction_service import (
    filter_noise_interactions,
    list_interaction_messages,
)

router = APIRouter()


@router.post("/community-interactions/filter-noise", response_model=Result[NoiseFilterResult])
def filter_noise(
    community_id: str | None = None,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    data = filter_noise_interactions(
        db=db,
        community_id=community_id,
        limit=limit
    )

    return Result[NoiseFilterResult].success(data)


@router.get("/community-interactions", response_model=Result[CommunityInteractionMessagePageOut])
def query_interaction_messages(
    community_id: str | None = None,
    days: int = 7,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
):
    data = list_interaction_messages(
        db=db,
        community_id=community_id,
        days=days,
        page=page,
        page_size=page_size,
    )

    return Result[CommunityInteractionMessagePageOut].success(data)
