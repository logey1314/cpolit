from datetime import datetime

from sqlalchemy.orm import Session

from app.models.private_user import PrivateUser
from app.schemas.user import UserImportIn, UserImportResult, UserPageOut


def get_users(
    db: Session,
    source: str | None = None,
    skip: int = 0,
    limit: int = 10
):
    query = db.query(PrivateUser)

    if source:
        query = query.filter(PrivateUser.source == source)

    total = query.count()
    items = query.offset(skip).limit(limit).all()

    return UserPageOut(
        total=total,
        items=items
    )


def find_main_user_by_phone(db: Session, phone: str | None):
    if not phone:
        return None

    return db.query(PrivateUser).filter(
        PrivateUser.phone == phone,
        PrivateUser.merged_user_id.is_(None)
    ).first()


def create_user_record(
    db: Session,
    source: str | None,
    user_data: UserImportIn,
    merged_user_id: int | None = None
):
    user = PrivateUser(
        external_user_id=user_data.external_user_id,
        phone=user_data.phone,
        name=user_data.name,
        source=user_data.source or source,
        tags=user_data.tags or [],
        purchase_status=user_data.purchase_status or "未购",
        operation_status=user_data.operation_status or "正常",
        merged_user_id=merged_user_id,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )

    db.add(user)
    db.flush()

    return user


def import_mock_users(
    db: Session,
    source: str | None,
    users: list[UserImportIn]
):
    imported_count = 0
    errors = []

    for index, user_data in enumerate(users):
        try:
            if not user_data.phone:
                errors.append({
                    "index": index,
                    "message": "phone 不能为空，无法进行用户归并"
                })
                continue

            main_user = find_main_user_by_phone(
                db=db,
                phone=user_data.phone
            )

            if main_user:
                create_user_record(
                    db=db,
                    source=source,
                    user_data=user_data,
                    merged_user_id=main_user.id
                )
            else:
                create_user_record(
                    db=db,
                    source=source,
                    user_data=user_data,
                    merged_user_id=None
                )

            imported_count += 1

        except Exception as e:
            errors.append({
                "index": index,
                "message": str(e)
            })

    db.commit()

    return UserImportResult(
        imported_count=imported_count,
        errors=errors
    )

def get_user_identity_group(db: Session, user_id: int):
    main_user = db.query(PrivateUser).filter(
        PrivateUser.id == user_id
    ).first()

    if not main_user:
        return None

    main_user_id = main_user.merged_user_id or main_user.id

    records = db.query(PrivateUser).filter(
        (PrivateUser.id == main_user_id) |
        (PrivateUser.merged_user_id == main_user_id)
    ).all()

    main_user = db.query(PrivateUser).filter(
        PrivateUser.id == main_user_id
    ).first()

    return {
        "main_user": main_user,
        "records": records
    }

