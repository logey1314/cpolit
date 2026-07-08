from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CommunityInteractionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    community_id: str
    user_id: int
    message_content: str | None = None
    message_type: str | None = None
    keywords: list[str] | None = None
    intent_label: str | None = None
    sentiment: str | None = None
    interaction_time: datetime | None = None


class NoiseFilterResult(BaseModel):
    valid_count: int
    noise_count: int

class IntentRecognizeResult(BaseModel):
    message_id: int
    intent_label: str
    sentiment: str
    keywords: list[str]