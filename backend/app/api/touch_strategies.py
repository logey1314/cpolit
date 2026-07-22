from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.result import Result
from app.schemas.touch_strategy import (
    TouchStrategyCandidatePageOut,
    TouchStrategyGenerateRequest,
    TouchStrategyOut,
    TouchStrategyPageOut,
    TouchStrategyStatusOut,
    TouchStrategyStatusRequest,
)
from app.services.touch_strategy_service import (
    generate_touch_strategy,
    list_touch_strategy_candidates,
    list_touch_strategies,
    update_touch_strategy_status,
)

router = APIRouter()


@router.post("/touch-strategies/generate", response_model=Result[TouchStrategyOut])
def generate_strategy(
    request: TouchStrategyGenerateRequest,
    db: Session = Depends(get_db)
):
    try:
        data = generate_touch_strategy(
            db=db,
            user_id=request.user_id,
            operation_goal=request.operation_goal
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return Result[TouchStrategyOut].success(data)


@router.get("/touch-strategies/candidates", response_model=Result[TouchStrategyCandidatePageOut])
def list_strategy_candidates(
    keyword: str | None = None,
    source: str | None = None,
    confirm_status: str | None = None,
    segment_type: str | None = None,
    touch_channel: str | None = None,
    page: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_db),
):
    data = list_touch_strategy_candidates(
        db=db,
        keyword=keyword,
        source=source,
        confirm_status=confirm_status,
        segment_type=segment_type,
        touch_channel=touch_channel,
        page=page,
        page_size=page_size,
    )

    return Result[TouchStrategyCandidatePageOut].success(data)


@router.get("/touch-strategies", response_model=Result[TouchStrategyPageOut])
def list_strategies(
    user_id: int | None = None,
    confirm_status: str | None = None,
    keyword: str | None = None,
    segment_type: str | None = None,
    touch_channel: str | None = None,
    page: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_db),
):
    data = list_touch_strategies(
        db=db,
        user_id=user_id,
        confirm_status=confirm_status,
        keyword=keyword,
        segment_type=segment_type,
        touch_channel=touch_channel,
        page=page,
        page_size=page_size,
    )

    return Result[TouchStrategyPageOut].success(data)


@router.put("/touch-strategies/{task_id}/status", response_model=Result[TouchStrategyStatusOut])
def update_strategy_status(
    task_id: int,
    request: TouchStrategyStatusRequest,
    db: Session = Depends(get_db),
):
    try:
        data = update_touch_strategy_status(
            db=db,
            task_id=task_id,
            confirm_status=request.confirm_status,
            assignee=request.assignee,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return Result[TouchStrategyStatusOut].success(data)
