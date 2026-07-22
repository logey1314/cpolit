from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.frequency import (
    FrequencyCheckOut,
    FrequencyCheckRequest,
    FrequencyIncrementOut,
    FrequencyIncrementRequest,
    FrequencyRuleOut,
    FrequencyRulePageOut,
    FrequencyRuleUpdateRequest,
)
from app.schemas.result import Result
from app.services.touch_frequency_service import (
    check_frequency,
    increment_frequency,
    list_frequency_rules,
    update_frequency_rule,
)

router = APIRouter()


@router.get("/frequency/rules", response_model=Result[FrequencyRulePageOut])
def query_frequency_rules(
    dimension: str | None = None,
    channel: str | None = None,
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db),
):
    data = list_frequency_rules(
        db=db,
        dimension=dimension,
        channel=channel,
        page=page,
        page_size=page_size,
    )

    return Result[FrequencyRulePageOut].success(data)


@router.put("/frequency/rules/{rule_id}", response_model=Result[FrequencyRuleOut])
def update_rule(
    rule_id: int,
    request: FrequencyRuleUpdateRequest,
    db: Session = Depends(get_db),
):
    try:
        data = update_frequency_rule(
            db=db,
            rule_id=rule_id,
            max_count=request.max_count,
            window_hours=request.window_hours,
            is_active=request.is_active,
            rule_description=request.rule_description,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return Result[FrequencyRuleOut].success(data)


@router.post("/frequency/check", response_model=Result[FrequencyCheckOut])
def check_touch_frequency(
    request: FrequencyCheckRequest,
    db: Session = Depends(get_db),
):
    data = check_frequency(
        db=db,
        user_id=request.user_id,
        channel=request.channel,
        community_id=request.community_id,
        activity_id=request.activity_id,
    )

    return Result[FrequencyCheckOut].success(data)


@router.post("/frequency/increment", response_model=Result[FrequencyIncrementOut])
def increment_touch_frequency(
    request: FrequencyIncrementRequest,
    db: Session = Depends(get_db),
):
    try:
        data = increment_frequency(
            db=db,
            user_id=request.user_id,
            channel=request.channel,
            community_id=request.community_id,
            activity_id=request.activity_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return Result[FrequencyIncrementOut].success(data)
