from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TouchStrategyGenerateRequest(BaseModel):
    user_id: int
    operation_goal: str


class TouchStrategyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    task_id: int
    user_id: int
    user_name: str | None = None
    segment_type: str | None = None
    touch_channel: str
    strategy_reason: str | None = None
    target_crowd: str | None = None
    confirm_status: str | None = None
    assignee: str | None = None
    plan_time: datetime | None = None


class TouchStrategyPageOut(BaseModel):
    total: int
    items: list[TouchStrategyOut]


class TouchStrategyCandidateOut(BaseModel):
    user_id: int
    user_name: str | None = None
    user_source: str | None = None
    tags: list[str] | None = None
    task_id: int | None = None
    segment_type: str | None = None
    touch_channel: str | None = None
    strategy_reason: str | None = None
    target_crowd: str | None = None
    confirm_status: str | None = None
    assignee: str | None = None
    plan_time: datetime | None = None


class TouchStrategyCandidatePageOut(BaseModel):
    total: int
    items: list[TouchStrategyCandidateOut]


class TouchStrategyStatusRequest(BaseModel):
    confirm_status: str
    assignee: str | None = None


class TouchStrategyStatusOut(BaseModel):
    task_id: int
    confirm_status: str
    assignee: str | None = None
