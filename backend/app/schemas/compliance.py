from pydantic import BaseModel


class ComplianceReviewRequest(BaseModel):
    content_draft_id: int


class ComplianceRiskOut(BaseModel):
    log_id: int | None = None
    risk_type: str | None = None
    risk_detail: str
    suggestion: str | None = None


class ComplianceReviewOut(BaseModel):
    content_draft_id: int
    review_status: str
    risks: list[ComplianceRiskOut]


class ComplianceConfirmRequest(BaseModel):
    decision: str
    reviewer: str | None = None


class ComplianceConfirmOut(BaseModel):
    log_id: int
    review_status: str
    reviewer: str | None = None


class ComplianceLogOut(BaseModel):
    log_id: int
    content_draft_id: int
    strategy_task_id: int | None = None
    user_id: int | None = None
    user_name: str | None = None
    user_source: str | None = None
    touch_channel: str | None = None
    segment_type: str | None = None
    content_text: str | None = None
    risk_type: str | None = None
    risk_detail: str | None = None
    suggestion: str | None = None
    review_status: str
    reviewer: str | None = None
    reviewed_at: str | None = None


class ComplianceLogPageOut(BaseModel):
    total: int
    items: list[ComplianceLogOut]
