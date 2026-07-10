from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UserSegmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    segment_type: str
    touch_priority: int
    segment_basis: str | None = None
    applicable_strategy: str | None = None
    confidence_score: float
    manual_adjusted: int = 0
    updated_at: datetime | str | None = None


class UserSegmentAdjustRequest(BaseModel):
    segment_type: str
    reason: str