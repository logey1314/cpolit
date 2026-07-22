from pydantic import BaseModel


class FrequencyCheckRequest(BaseModel):
    user_id: int
    channel: str
    community_id: str | None = None
    activity_id: str | None = None


class FrequencyDimensionResult(BaseModel):
    dimension: str
    dimension_id: str
    channel: str
    allowed: bool
    current_count: int
    max_count: int
    window_hours: int
    reason: str | None = None


class FrequencyCheckOut(BaseModel):
    allowed: bool
    reason: str | None = None
    current_count: int
    max_count: int
    details: list[FrequencyDimensionResult]


class FrequencyIncrementRequest(BaseModel):
    user_id: int
    channel: str
    community_id: str | None = None
    activity_id: str | None = None


class FrequencyIncrementOut(BaseModel):
    user_id: int
    channel: str
    counts: dict[str, int]


class FrequencyRuleOut(BaseModel):
    id: int
    dimension: str
    dimension_id: str | None = None
    channel: str
    max_count: int
    window_hours: int
    rule_description: str | None = None
    is_active: int


class FrequencyRulePageOut(BaseModel):
    total: int
    items: list[FrequencyRuleOut]


class FrequencyRuleUpdateRequest(BaseModel):
    max_count: int
    window_hours: int
    is_active: int = 1
    rule_description: str | None = None
