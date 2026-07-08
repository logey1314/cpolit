from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models.community_interaction import CommunityInteraction
from app.models.community_member import CommunityMember
from app.schemas.community_interaction import SilenceRiskResult


RISK_KEYWORDS = ["烦", "太多", "退群"]


def get_community_member(db: Session, user_id: int):
    return db.query(CommunityMember).filter(
        CommunityMember.user_id == user_id
    ).first()


def calculate_silent_days(last_interaction_at):
    if not last_interaction_at:
        return None

    return (datetime.now() - last_interaction_at).days


def get_silence_label(silent_days: int | None):
    if silent_days is None:
        return "未知"

    if silent_days >= 30:
        return "深度沉默"

    if silent_days >= 14:
        return "沉默"

    return "正常"


def get_recent_messages(
    db: Session,
    user_id: int,
    days: int = 7
):
    since_time = datetime.now() - timedelta(days=days)

    return db.query(CommunityInteraction).filter(
        CommunityInteraction.user_id == user_id,
        CommunityInteraction.interaction_time >= since_time
    ).all()


def has_risk_keyword(content: str | None):
    content = content or ""

    return any(keyword in content for keyword in RISK_KEYWORDS)


def judge_risk_level(recent_messages: list[CommunityInteraction]):
    for message in recent_messages:
        if message.sentiment == "负面" and has_risk_keyword(message.message_content):
            return "高", message.message_content

    return "低", None


def check_silence_and_risk(db: Session, user_id: int):
    member = get_community_member(db, user_id)

    if not member:
        return None

    silent_days = calculate_silent_days(member.last_interaction_at)
    silence_label = get_silence_label(silent_days)

    recent_messages = get_recent_messages(
        db=db,
        user_id=user_id,
        days=7
    )

    risk_level, risk_reason = judge_risk_level(recent_messages)

    return SilenceRiskResult(
        user_id=user_id,
        silent_days=silent_days,
        silence_label=silence_label,
        risk_level=risk_level,
        risk_reason=risk_reason
    )