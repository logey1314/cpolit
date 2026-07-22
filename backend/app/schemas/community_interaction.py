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


class CommunityInteractionMessageOut(BaseModel):
    id: int
    community_id: str
    user_id: int
    user_name: str | None = None
    message_content: str | None = None
    message_type: str | None = None
    keywords: list[str] | None = None
    intent_label: str | None = None
    sentiment: str | None = None
    interaction_time: datetime | None = None


class CommunityInteractionMessagePageOut(BaseModel):
    total: int
    items: list[CommunityInteractionMessageOut]

class IntentRecognizeResult(BaseModel):
    message_id: int
    intent_label: str
    sentiment: str
    keywords: list[str]

class SilenceRiskResult(BaseModel):
    user_id: int
    silent_days: int | None = None
    silence_label: str
    risk_level: str
    risk_reason: str | None = None


class CommunityOptionOut(BaseModel):
    community_id: str
    community_name: str | None = None


class CommunityAnalyzeRequest(BaseModel):
    community_id: str | None = None
    days: int = 7


class CommunityStructureOut(BaseModel):
    total_count: int
    active_count: int
    silent_count: int
    risk_count: int


class KeywordHeatOut(BaseModel):
    keyword: str
    count: int


class IntentDistributionOut(BaseModel):
    intent_label: str
    count: int


class CommunityMemberAnalysisOut(BaseModel):
    user_id: int
    name: str | None = None
    join_source: str | None = None
    intent_label: str | None = None
    sentiment: str | None = None
    silent_days: int | None = None
    risk_level: str | None = None


class CommunityAnalysisOut(BaseModel):
    community_id: str | None = None
    community_name: str | None = None
    days: int
    structure: CommunityStructureOut
    keywords: list[KeywordHeatOut]
    intent_distribution: list[IntentDistributionOut]
    members: list[CommunityMemberAnalysisOut]
    recommended_topic: str
