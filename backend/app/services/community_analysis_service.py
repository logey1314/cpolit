from collections import Counter, defaultdict
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models.community_interaction import CommunityInteraction
from app.models.community_member import CommunityMember
from app.models.private_user import PrivateUser
from app.services.silence_service import check_silence_and_risk


def list_communities(db: Session):
    rows = db.query(
        CommunityMember.community_id,
        CommunityMember.community_name,
    ).distinct().all()

    return [
        {
            "community_id": row.community_id,
            "community_name": row.community_name or row.community_id,
        }
        for row in rows
    ]


def get_recent_interactions(
    db: Session,
    community_id: str | None,
    days: int,
):
    query = db.query(CommunityInteraction)

    if days and days > 0:
        since_time = datetime.now() - timedelta(days=days)
        query = query.filter(
            CommunityInteraction.interaction_time >= since_time
        )

    if community_id:
        query = query.filter(CommunityInteraction.community_id == community_id)

    return query.all()


def get_members(db: Session, community_id: str | None):
    query = db.query(CommunityMember)

    if community_id:
        query = query.filter(CommunityMember.community_id == community_id)

    return query.all()


def get_user_name_map(db: Session, user_ids: list[int]):
    if not user_ids:
        return {}

    users = db.query(PrivateUser).filter(
        PrivateUser.id.in_(user_ids)
    ).all()

    return {user.id: user.name for user in users}


def normalize_label(value: str | None, default: str):
    return value or default


def summarize_user_signals(interactions: list[CommunityInteraction]):
    signals = defaultdict(lambda: {
        "intent_counter": Counter(),
        "sentiment_counter": Counter(),
        "keywords": Counter(),
    })

    for item in interactions:
        bucket = signals[item.user_id]
        bucket["intent_counter"][normalize_label(item.intent_label, "无关")] += 1
        bucket["sentiment_counter"][normalize_label(item.sentiment, "中性")] += 1
        for keyword in item.keywords or []:
            bucket["keywords"][keyword] += 1

    return signals


def most_common_or_default(counter: Counter, default: str):
    if not counter:
        return default

    return counter.most_common(1)[0][0]


def build_recommended_topic(keyword_counter: Counter, intent_counter: Counter):
    top_keywords = [item[0] for item in keyword_counter.most_common(3)]

    if "吐槽" in intent_counter:
        keyword = top_keywords[0] if top_keywords else "使用体验"
        return f"大家最近在用{keyword}时有没有遇到什么问题？可以一起交流下。"

    if "需求" in intent_counter:
        keyword = top_keywords[0] if top_keywords else "产品"
        return f"大家最近更关注{keyword}的哪些信息？价格、使用方法还是搭配建议？"

    if top_keywords:
        return f"大家最近在用什么{top_keywords[0]}呀？欢迎分享真实体验。"

    return "大家最近有什么护肤或活动问题，可以在群里一起交流。"


def analyze_community_interactions(
    db: Session,
    community_id: str | None = None,
    days: int = 7,
):
    members = get_members(db, community_id)
    interactions = get_recent_interactions(db, community_id, days)
    user_ids = list({member.user_id for member in members})
    user_name_map = get_user_name_map(db, user_ids)
    signals = summarize_user_signals(interactions)

    keyword_counter = Counter()
    intent_counter = Counter()
    for item in interactions:
        intent_counter[normalize_label(item.intent_label, "无关")] += 1
        for keyword in item.keywords or []:
            keyword_counter[keyword] += 1

    member_rows = []
    active_count = 0
    silent_count = 0
    risk_count = 0

    for member in members:
        user_signal = signals.get(member.user_id)
        silence = check_silence_and_risk(db, member.user_id)
        silent_days = silence.silent_days if silence else None
        risk_level = silence.risk_level if silence else "低"

        intent_label = "沉默"
        sentiment = "中性"
        if user_signal:
            intent_label = most_common_or_default(user_signal["intent_counter"], "无关")
            sentiment = most_common_or_default(user_signal["sentiment_counter"], "中性")

        if user_signal and intent_label != "沉默":
            active_count += 1

        if silent_days is not None and silent_days >= 14:
            silent_count += 1

        if risk_level == "高":
            risk_count += 1

        member_rows.append({
            "user_id": member.user_id,
            "name": user_name_map.get(member.user_id),
            "join_source": member.join_source,
            "intent_label": intent_label,
            "sentiment": sentiment,
            "silent_days": silent_days,
            "risk_level": risk_level,
        })

    community_name = members[0].community_name if members else None

    return {
        "community_id": community_id,
        "community_name": community_name,
        "days": days,
        "structure": {
            "total_count": len(members),
            "active_count": active_count,
            "silent_count": silent_count,
            "risk_count": risk_count,
        },
        "keywords": [
            {"keyword": keyword, "count": count}
            for keyword, count in keyword_counter.most_common(12)
        ],
        "intent_distribution": [
            {"intent_label": label, "count": count}
            for label, count in intent_counter.most_common()
        ],
        "members": member_rows,
        "recommended_topic": build_recommended_topic(keyword_counter, intent_counter),
    }
