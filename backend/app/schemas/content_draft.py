from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class ContentGenerateRequest(BaseModel):
    strategy_task_id: int
    content_type: str | None = None


class MultiChannelContentRequest(BaseModel):
    strategy_task_id: int
    channels: list[str]
    base_draft_id: int | None = None


class ContentDraftOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    draft_id: int
    strategy_task_id: int
    content_type: str
    content_text: str
    reference_sources: list[dict[str, Any]]
    version: int
    brand_tone_score: float
    review_status: str
    created_at: datetime | None = None


class ContentDraftUpdateRequest(BaseModel):
    content_text: str


class MultiChannelContentOut(BaseModel):
    strategy_task_id: int
    drafts: list[ContentDraftOut]


class ContentDraftPageOut(BaseModel):
    total: int
    items: list[ContentDraftOut]
