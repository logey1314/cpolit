import json
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.models.private_user import PrivateUser
from app.schemas.user import UserTagUpdateResult


TAG_MAPPING_PATH = Path(__file__).resolve().parents[1] / "config" / "tag_mapping.json"


def load_tag_mapping(source: str | None):
    if not TAG_MAPPING_PATH.exists():
        return {}

    with TAG_MAPPING_PATH.open("r", encoding="utf-8") as f:
        mapping_config = json.load(f)

    if not source:
        return {}

    return mapping_config.get(source, {})


def standardize_tags(raw_tags: list | None, source: str | None):
    raw_tags = raw_tags or []
    mapping = load_tag_mapping(source)

    standardized = []

    for tag in raw_tags:
        if tag in mapping:
            standardized.append(mapping[tag])
        else:
            standardized.append(f"{source}:{tag}")

    return list(dict.fromkeys(standardized))


def standardize_user_tags(db: Session, user_id: int):
    user = db.query(PrivateUser).filter(
        PrivateUser.id == user_id
    ).first()

    if not user:
        return None

    updated_tags = standardize_tags(
        raw_tags=user.tags,
        source=user.source
    )

    user.tags = updated_tags
    user.updated_at = datetime.now()

    db.commit()
    db.refresh(user)

    return UserTagUpdateResult(
        updated_tags=updated_tags
    )