from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.result import Result
from app.schemas.community_interaction import NoiseFilterResult
from app.services.community_interaction_service import filter_noise_interactions

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