from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.result import Result
from app.schemas.community_interaction import IntentRecognizeResult
from app.services.intent_service import recognize_interaction_intent

router = APIRouter()


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