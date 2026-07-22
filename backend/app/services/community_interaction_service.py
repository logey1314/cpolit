import re
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models.community_interaction import CommunityInteraction
from app.models.private_user import PrivateUser
from app.schemas.community_interaction import NoiseFilterResult


URL_PATTERN = re.compile(r"(https?://|www\.)\S+", re.IGNORECASE)
SILENT_REPLIES = {"嗯", "啊", "哦", "好", "收到", "好的", "可以", "行", "ok", "OK"}


def normalize_text(value: str | None):
    return (value or "").strip()


def has_url(content: str):
    return bool(URL_PATTERN.search(content))


def is_emoji_char(char: str):
    code = ord(char)

    return (
        0x1F300 <= code <= 0x1FAFF
        or 0x2600 <= code <= 0x27BF
    )


def is_emoji_content(content: str):
    text = normalize_text(content)

    if not text:
        return False

    if len(text) > 8:
        return False

    return all(is_emoji_char(char) for char in text if not char.isspace())


def is_silent_reply(content: str):
    text = normalize_text(content)

    if not text:
        return False

    if text in SILENT_REPLIES:
        return True

    return len(text) <= 2


def is_filter_message(content: str):
    text = normalize_text(content)

    if not text:
        return True

    return has_url(text) or is_emoji_content(text)


def query_interactions(
    db: Session,
    community_id: str | None = None,
    limit: int = 100
):
    query = db.query(CommunityInteraction)

    if community_id:
        query = query.filter(
            CommunityInteraction.community_id == community_id
        )

    return query.order_by(
        CommunityInteraction.interaction_time.asc()
    ).limit(limit).all()


def filter_noise_interactions(
    db: Session,
    community_id: str | None = None,
    limit: int = 100
):
    messages = query_interactions(
        db=db,
        community_id=community_id,
        limit=limit
    )

    valid_count = 0
    noise_count = 0

    for message in messages:
        content = normalize_text(message.message_content)

        if is_filter_message(content):
            message.intent_label = "无关"
            noise_count += 1
        elif is_silent_reply(content):
            message.intent_label = "沉默"
            noise_count += 1
        else:
            message.intent_label = "有效"
            valid_count += 1

    db.commit()

    return NoiseFilterResult(
        valid_count=valid_count,
        noise_count=noise_count
    )


def list_interaction_messages(
    db: Session,
    community_id: str | None = None,
    days: int = 7,
    page: int = 1,
    page_size: int = 20,
):
    query = db.query(CommunityInteraction)

    if days and days > 0:
        since_time = datetime.now() - timedelta(days=days)
        query = query.filter(
            CommunityInteraction.interaction_time >= since_time
        )

    if community_id:
        query = query.filter(
            CommunityInteraction.community_id == community_id
        )

    total = query.count()
    items = query.order_by(
        CommunityInteraction.interaction_time.desc()
    ).offset(
        (page - 1) * page_size
    ).limit(
        page_size
    ).all()

    user_ids = list({item.user_id for item in items})
    users = db.query(PrivateUser).filter(
        PrivateUser.id.in_(user_ids)
    ).all() if user_ids else []
    user_name_map = {user.id: user.name for user in users}

    return {
        "total": total,
        "items": [
            {
                "id": item.id,
                "community_id": item.community_id,
                "user_id": item.user_id,
                "user_name": user_name_map.get(item.user_id),
                "message_content": item.message_content,
                "message_type": item.message_type,
                "keywords": item.keywords or [],
                "intent_label": item.intent_label,
                "sentiment": item.sentiment,
                "interaction_time": item.interaction_time,
            }
            for item in items
        ],
    }
