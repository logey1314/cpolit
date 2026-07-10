import json
from datetime import datetime, timedelta
from decimal import Decimal

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.llm_client import get_chat_model
from app.core.redis_client import get_redis_client
from app.models.community_interaction import CommunityInteraction
from app.models.private_user import PrivateUser
from app.models.user_segment import UserSegment
from app.services.silence_service import check_silence_and_risk


SEGMENT_CACHE_TTL_SECONDS = 24 * 60 * 60

SEGMENT_TYPES = {
    "新进群",
    "高意向",
    "待培育",
    "沉默",
    "已购",
    "活动关注",
    "暂缓触达"
}

SEGMENT_STRATEGIES = {
    "新进群": "新人欢迎与基础种草",
    "高意向": "优先私聊转化",
    "待培育": "内容种草培育",
    "沉默": "低频唤醒",
    "已购": "复购与售后关怀",
    "活动关注": "活动提醒与福利触达",
    "暂缓触达": "降低频率观察"
}


class SegmentLLMResult(BaseModel):
    segment_type: str
    touch_priority: int
    segment_basis: str
    confidence_score: float


def get_user(db: Session, user_id: int):
    return db.query(PrivateUser).filter(
        PrivateUser.id == user_id
    ).first()


def get_recent_interactions(
    db: Session,
    user_id: int,
    days: int = 30
):
    since_time = datetime.now() - timedelta(days=days)

    return db.query(CommunityInteraction).filter(
        CommunityInteraction.user_id == user_id,
        CommunityInteraction.interaction_time >= since_time
    ).order_by(
        CommunityInteraction.interaction_time.desc()
    ).all()


def summarize_interactions(interactions: list[CommunityInteraction]):
    intent_counts = {}
    sentiment_counts = {}
    keywords = []
    recent_messages = []

    for item in interactions:
        if item.intent_label:
            intent_counts[item.intent_label] = intent_counts.get(item.intent_label, 0) + 1

        if item.sentiment:
            sentiment_counts[item.sentiment] = sentiment_counts.get(item.sentiment, 0) + 1

        if item.keywords:
            keywords.extend(item.keywords)

        if item.message_content and len(recent_messages) < 5:
            recent_messages.append(item.message_content)

    return {
        "total_count": len(interactions),
        "intent_counts": intent_counts,
        "sentiment_counts": sentiment_counts,
        "keywords": list(dict.fromkeys(keywords)),
        "recent_messages": recent_messages
    }


def build_segment_input(db: Session, user_id: int):
    user = get_user(db, user_id)

    if not user:
        return None

    interactions = get_recent_interactions(db, user_id)
    interaction_summary = summarize_interactions(interactions)
    silence_result = check_silence_and_risk(db, user_id)

    return {
        "user": {
            "id": user.id,
            "name": user.name,
            "source": user.source,
            "tags": user.tags or [],
            "purchase_status": user.purchase_status,
            "operation_status": user.operation_status,
            "created_at": str(user.created_at) if user.created_at else None
        },
        "interactions": interaction_summary,
        "silence": silence_result.model_dump() if silence_result else None
    }


def build_segment_messages(segment_input: dict):
    return [
        SystemMessage(content=(
            "你是私域运营用户分层助手。"
            "请根据用户标签、购买状态、互动信号、沉默周期和打扰风险判断用户分层。"
            "你必须只输出 JSON，不要输出解释。"
            "segment_type 只能是：新进群、高意向、待培育、沉默、已购、活动关注、暂缓触达。"
            "touch_priority 必须是 1 到 5 的整数，1 表示最高优先级，5 表示最低优先级。"
            "confidence_score 必须是 0 到 1 的小数。"
        )),
        HumanMessage(content=(
            f"用户数据：{json.dumps(segment_input, ensure_ascii=False)}\n"
            "请输出 JSON，例如："
            '{"segment_type":"高意向","touch_priority":1,'
            '"segment_basis":"近期询问价格和有货情况，且标签包含高意向",'
            '"confidence_score":0.86}'
        ))
    ]


def parse_llm_json(content):
    if isinstance(content, list):
        content = "".join(str(item) for item in content)

    return json.loads(content)


def call_llm_for_segment(segment_input: dict):
    llm = get_chat_model()
    messages = build_segment_messages(segment_input)
    response = llm.invoke(messages)
    data = parse_llm_json(response.content)

    return SegmentLLMResult(**data)


def normalize_segment_result(result: SegmentLLMResult):
    segment_type = result.segment_type
    touch_priority = result.touch_priority
    segment_basis = result.segment_basis or ""
    confidence_score = result.confidence_score

    if segment_type not in SEGMENT_TYPES:
        segment_type = "待培育"

    if touch_priority < 1 or touch_priority > 5:
        touch_priority = 3

    if confidence_score < 0:
        confidence_score = 0

    if confidence_score > 1:
        confidence_score = 1

    if confidence_score < 0.6 and "待人工复核" not in segment_basis:
        segment_basis = f"{segment_basis}（待人工复核）"

    return SegmentLLMResult(
        segment_type=segment_type,
        touch_priority=touch_priority,
        segment_basis=segment_basis,
        confidence_score=confidence_score
    )


def get_applicable_strategy(segment_type: str):
    return SEGMENT_STRATEGIES.get(segment_type, "通用运营跟进")


def save_segment(db: Session, user_id: int, result: SegmentLLMResult):
    segment = db.query(UserSegment).filter(
        UserSegment.user_id == user_id
    ).first()

    if segment and segment.manual_adjusted == 1:
        return segment

    applicable_strategy = get_applicable_strategy(result.segment_type)

    if not segment:
        segment = UserSegment(
            user_id=user_id
        )
        db.add(segment)

    segment.segment_type = result.segment_type
    segment.touch_priority = result.touch_priority
    segment.segment_basis = result.segment_basis
    segment.applicable_strategy = applicable_strategy
    segment.confidence_score = Decimal(str(round(result.confidence_score, 2)))
    segment.updated_at = datetime.now()

    db.commit()
    db.refresh(segment)

    return segment


def segment_to_dict(segment: UserSegment):
    return {
        "user_id": segment.user_id,
        "segment_type": segment.segment_type,
        "touch_priority": segment.touch_priority,
        "segment_basis": segment.segment_basis,
        "applicable_strategy": segment.applicable_strategy,
        "confidence_score": float(segment.confidence_score),
        "manual_adjusted": segment.manual_adjusted,
        "updated_at": segment.updated_at.isoformat() if segment.updated_at else None
    }


def cache_segment(segment: UserSegment):
    try:
        client = get_redis_client()

        if not client:
            return

        key = f"segment:user:{segment.user_id}"
        client.hset(key, mapping=segment_to_dict(segment))
        client.expire(key, SEGMENT_CACHE_TTL_SECONDS)
    except Exception:
        pass


def delete_cached_segment(user_id: int):
    try:
        client = get_redis_client()

        if not client:
            return

        client.delete(f"segment:user:{user_id}")
    except Exception:
        pass


def get_cached_segment(user_id: int):
    try:
        client = get_redis_client()

        if not client:
            return None

        data = client.hgetall(f"segment:user:{user_id}")

        if not data:
            return None

        return {
            "user_id": int(data["user_id"]),
            "segment_type": data["segment_type"],
            "touch_priority": int(data["touch_priority"]),
            "segment_basis": data.get("segment_basis"),
            "applicable_strategy": data.get("applicable_strategy"),
            "confidence_score": float(data["confidence_score"]),
            "manual_adjusted": int(data.get("manual_adjusted", 0)),
            "updated_at": data.get("updated_at")
        }
    except Exception:
        return None


def judge_user_segment(db: Session, user_id: int):
    existing_segment = db.query(UserSegment).filter(
        UserSegment.user_id == user_id
    ).first()

    if existing_segment and existing_segment.manual_adjusted == 1:
        cache_segment(existing_segment)
        return segment_to_dict(existing_segment)

    segment_input = build_segment_input(db, user_id)

    if not segment_input:
        return None

    llm_result = call_llm_for_segment(segment_input)
    llm_result = normalize_segment_result(llm_result)

    segment = save_segment(db, user_id, llm_result)
    cache_segment(segment)

    return segment_to_dict(segment)


def get_user_segment(db: Session, user_id: int):
    cached = get_cached_segment(user_id)

    if cached:
        return cached

    segment = db.query(UserSegment).filter(
        UserSegment.user_id == user_id
    ).first()

    if segment and segment.manual_adjusted == 1:
        cache_segment(segment)
        return segment_to_dict(segment)

    return judge_user_segment(db, user_id)


def manual_adjust_user_segment(
    db: Session,
    user_id: int,
    segment_type: str,
    reason: str
):
    if segment_type not in SEGMENT_TYPES:
        raise ValueError("分层类型不合法")

    user = get_user(db, user_id)

    if not user:
        return None

    delete_cached_segment(user_id)

    segment = db.query(UserSegment).filter(
        UserSegment.user_id == user_id
    ).first()

    if not segment:
        segment = UserSegment(
            user_id=user_id
        )
        db.add(segment)

    segment.segment_type = segment_type
    segment.touch_priority = 3
    segment.segment_basis = reason
    segment.applicable_strategy = get_applicable_strategy(segment_type)
    segment.confidence_score = Decimal("1.00")
    segment.manual_adjusted = 1
    segment.updated_at = datetime.now()

    db.commit()
    db.refresh(segment)

    cache_segment(segment)

    return segment_to_dict(segment)