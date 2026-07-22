from datetime import datetime
from typing import Any

from pydantic import BaseModel


class OperationTaskCreateRequest(BaseModel):
    strategy_task_id: int
    content_draft_id: int


class OperationTaskCreateOut(BaseModel):
    task_id: int
    status: str
    target_system: str | None = None
    task_type: str | None = None


class OperationTaskStatusRequest(BaseModel):
    status: str
    fail_reason: str | None = None


class OperationTaskStatusOut(BaseModel):
    task_id: int
    updated_status: str
    fail_reason: str | None = None


class OperationTaskRetryOut(BaseModel):
    task_id: int
    status: str
    retry_count: int
    fail_reason: str | None = None


class OperationTaskOut(BaseModel):
    task_id: int
    strategy_task_id: int
    user_id: int | None = None
    user_name: str | None = None
    target_system: str | None = None
    task_type: str | None = None
    task_instruction: str | None = None
    content: str | None = None
    request_params: dict[str, Any] | None = None
    response_status: str | None = None
    fail_reason: str | None = None
    retry_count: int
    assignee: str | None = None
    remind_time: datetime | None = None
    created_at: datetime | None = None


class OperationTaskPageOut(BaseModel):
    total: int
    items: list[OperationTaskOut]
