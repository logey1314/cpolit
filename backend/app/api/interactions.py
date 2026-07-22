from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.result import Result
from app.schemas.community_interaction import (
    CommunityAnalysisOut,
    CommunityAnalyzeRequest,
    CommunityOptionOut,
    IntentRecognizeResult,
    SilenceRiskResult,
)
from app.services.community_analysis_service import (
    analyze_community_interactions,
    list_communities,
)
from app.services.intent_service import recognize_interaction_intent
from app.services.silence_service import check_silence_and_risk

router = APIRouter()


@router.get("/communities", response_model=Result[list[CommunityOptionOut]])
def query_communities(
    db: Session = Depends(get_db)
):
    data = list_communities(db=db)
    return Result[list[CommunityOptionOut]].success(data)


@router.post("/interactions/analyze", response_model=Result[CommunityAnalysisOut])
def analyze_interactions(
    request: CommunityAnalyzeRequest,
    db: Session = Depends(get_db)
):
    data = analyze_community_interactions(
        db=db,
        community_id=request.community_id,
        days=request.days,
    )
    return Result[CommunityAnalysisOut].success(data)


@router.post("/interactions/intent", response_model=Result[IntentRecognizeResult])
def recognize_intent(
    message_id: int,
    db: Session = Depends(get_db)
):
    try:
        data = recognize_interaction_intent(
            db=db,
            message_id=message_id
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not data:
        raise HTTPException(status_code=404, detail="消息不存在")

    return Result[IntentRecognizeResult].success(data)

@router.get("/interactions/silence", response_model=Result[SilenceRiskResult])
def get_silence_and_risk(
    user_id: int,
    db: Session = Depends(get_db)
):
    data = check_silence_and_risk(
        db=db,
        user_id=user_id
    )

    if not data:
        raise HTTPException(status_code=404, detail="社群成员不存在")

    return Result[SilenceRiskResult].success(data)


@router.get("/interactions/silence/{user_id}", response_model=Result[SilenceRiskResult])
def get_silence_and_risk_by_path(
    user_id: int,
    db: Session = Depends(get_db)
):
    data = check_silence_and_risk(
        db=db,
        user_id=user_id
    )

    if not data:
        raise HTTPException(status_code=404, detail="用户不存在或社群成员不存在")

    return Result[SilenceRiskResult].success(data)
