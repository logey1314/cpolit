from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.compliance import (
    ComplianceConfirmOut,
    ComplianceConfirmRequest,
    ComplianceLogPageOut,
    ComplianceReviewOut,
    ComplianceReviewRequest,
)
from app.schemas.result import Result
from app.services.compliance_service import (
    auto_compliance_review,
    confirm_compliance_log,
    list_compliance_logs,
)

router = APIRouter()


@router.get("/compliance/logs", response_model=Result[ComplianceLogPageOut])
def query_compliance_logs(
    review_status: str | None = None,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
):
    data = list_compliance_logs(
        db=db,
        review_status=review_status,
        page=page,
        page_size=page_size,
    )

    return Result[ComplianceLogPageOut].success(data)


@router.post("/compliance/review", response_model=Result[ComplianceReviewOut])
def review_content(
    request: ComplianceReviewRequest,
    db: Session = Depends(get_db),
):
    try:
        data = auto_compliance_review(
            db=db,
            content_draft_id=request.content_draft_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return Result[ComplianceReviewOut].success(data)


@router.put("/compliance/{log_id}/confirm", response_model=Result[ComplianceConfirmOut])
def confirm_review(
    log_id: int,
    request: ComplianceConfirmRequest,
    db: Session = Depends(get_db),
):
    try:
        data = confirm_compliance_log(
            db=db,
            log_id=log_id,
            decision=request.decision,
            reviewer=request.reviewer,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return Result[ComplianceConfirmOut].success(data)
