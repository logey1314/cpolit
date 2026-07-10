from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.result import Result
from app.schemas.user_segment import UserSegmentAdjustRequest, UserSegmentOut
from app.services.segment_service import (
    get_user_segment,
    judge_user_segment,
    manual_adjust_user_segment,
)

router = APIRouter()


@router.post("/user-segments/judge", response_model=Result[UserSegmentOut])
def judge_segment(
    user_id: int,
    db: Session = Depends(get_db)
):
    data = judge_user_segment(
        db=db,
        user_id=user_id
    )

    if not data:
        raise HTTPException(status_code=404, detail="用户不存在")

    return Result[UserSegmentOut].success(data)


@router.get("/user-segments", response_model=Result[UserSegmentOut])
def query_segment(
    user_id: int,
    db: Session = Depends(get_db)
):
    data = get_user_segment(
        db=db,
        user_id=user_id
    )

    if not data:
        raise HTTPException(status_code=404, detail="用户不存在或分层结果不存在")

    return Result[UserSegmentOut].success(data)


@router.put("/user-segments/{user_id}/adjust", response_model=Result[UserSegmentOut])
def adjust_segment(
    user_id: int,
    request: UserSegmentAdjustRequest,
    db: Session = Depends(get_db)
):
    try:
        data = manual_adjust_user_segment(
            db=db,
            user_id=user_id,
            segment_type=request.segment_type,
            reason=request.reason
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not data:
        raise HTTPException(status_code=404, detail="用户不存在")

    return Result[UserSegmentOut].success(data)