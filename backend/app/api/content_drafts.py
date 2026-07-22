from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.content_draft import (
    ContentDraftPageOut,
    ContentDraftOut,
    ContentDraftUpdateRequest,
    ContentGenerateRequest,
    MultiChannelContentOut,
    MultiChannelContentRequest,
)
from app.schemas.result import Result
from app.services.content_generation_service import (
    generate_content_draft,
    generate_multi_channel_content,
    list_content_drafts,
    update_content_draft,
)

router = APIRouter()


@router.get("/content-drafts", response_model=Result[ContentDraftPageOut])
def query_content_drafts(
    strategy_task_id: int | None = None,
    page: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_db),
):
    data = list_content_drafts(
        db=db,
        strategy_task_id=strategy_task_id,
        page=page,
        page_size=page_size,
    )

    return Result[ContentDraftPageOut].success(data)


@router.put("/content-drafts/{draft_id}", response_model=Result[ContentDraftOut])
def update_draft(
    draft_id: int,
    request: ContentDraftUpdateRequest,
    db: Session = Depends(get_db),
):
    try:
        data = update_content_draft(
            db=db,
            draft_id=draft_id,
            content_text=request.content_text,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return Result[ContentDraftOut].success(data)


@router.post("/content-drafts/generate", response_model=Result[ContentDraftOut])
def generate_content(
    request: ContentGenerateRequest,
    db: Session = Depends(get_db),
):
    try:
        data = generate_content_draft(
            db=db,
            strategy_task_id=request.strategy_task_id,
            request_content_type=request.content_type,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return Result[ContentDraftOut].success(data)


@router.post("/content-drafts/multi-channel", response_model=Result[MultiChannelContentOut])
def generate_multi_channel(
    request: MultiChannelContentRequest,
    db: Session = Depends(get_db),
):
    try:
        data = generate_multi_channel_content(
            db=db,
            strategy_task_id=request.strategy_task_id,
            channels=request.channels,
            base_draft_id=request.base_draft_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return Result[MultiChannelContentOut].success(data)
