from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.result import Result
from app.schemas.user import UserImportRequest, UserImportResult, UserPageOut, UserIdentityGroupOut
from app.services.user_service import get_users, import_mock_users, get_user_identity_group

router = APIRouter()


@router.get("/users", response_model=Result[UserPageOut])
def list_users(
    source: str = None,
    page: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_db)
):
    skip = (page - 1) * page_size

    data = get_users(
        db=db,
        source=source,
        skip=skip,
        limit=page_size
    )

    return Result[UserPageOut].success(data)


@router.post("/users/import", response_model=Result[UserImportResult])
def import_users(
    request: UserImportRequest,
    db: Session = Depends(get_db)
):
    data = import_mock_users(
        db=db,
        source=request.source,
        users=request.users
    )

    return Result[UserImportResult].success(data)

@router.get("/users/{user_id}/identities", response_model=Result[UserIdentityGroupOut])
def get_user_identities(
    user_id: int,
    db: Session = Depends(get_db)
):
    data = get_user_identity_group(
        db=db,
        user_id=user_id
    )

    if not data:
        raise HTTPException(status_code=404, detail="用户不存在")

    return Result[UserIdentityGroupOut].success(data)