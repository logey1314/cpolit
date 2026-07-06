from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.result import Result
from app.schemas.user import UserPageOut
from app.services.user_service import get_users

router = APIRouter()


@router.get("/users",response_model=Result[UserPageOut])
def list_users(
    source: str = None,
    page: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_db)
):

    skip = (page - 1) * page_size

    data= get_users(
        db=db,
        source=source,
        skip=skip,
        limit=page_size
    )
    return Result[UserPageOut].success(data)