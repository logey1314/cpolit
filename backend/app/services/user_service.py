from sqlalchemy.orm import Session
from app.models.private_user import PrivateUser


def get_users(db: Session, source=None, skip=0, limit=10):

    query = db.query(PrivateUser)

    # 来源筛选
    if source:
        query = query.filter(PrivateUser.source == source)

    total = query.count()
    items = query.offset(skip).limit(limit).all()

    return {
        "total": total,
        "items": items
    }