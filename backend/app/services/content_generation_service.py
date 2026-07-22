import json
from datetime import datetime

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.llm_client import get_chat_model
from app.models.compliance_review_log import ComplianceReviewLog
from app.models.content_draft import ContentDraft
from app.models.private_user import PrivateUser
from app.models.touch_strategy_task import TouchStrategyTask
from app.models.user_segment import UserSegment
from app.services.knowledge_retrieval_service import (
    search_all_knowledge,
    search_content_examples,
)


class ContentLLMResult(BaseModel):
    content_text: str
    brand_tone_score: float = 0.50


TOUCH_CHANNEL_CONTENT_TYPE = {
    "私聊": "私聊话术",
    "群发": "群公告",
    "社群话题": "社群话题",
    "活动邀约": "活动提醒",
    "朋友圈": "朋友圈文案",
    "短信": "短信短句",
    "暂缓": "私聊话术",
}

CHANNEL_TONE = {
    "私聊": "轻松自然，像朋友推荐，避免强推",
    "群公告": "正式友好，信息清晰，适合群内公开发布",
    "朋友圈": "软性种草，生活化，避免硬广感",
    "短信": "简洁直接，重点突出，控制字数",
}

CHANNEL_CONTENT_TYPE = {
    "私聊": "私聊话术",
    "群公告": "群公告",
    "朋友圈": "朋友圈文案",
    "短信": "短信短句",
}


def decide_content_type(task: TouchStrategyTask, request_content_type: str | None):
    if request_content_type:
        return request_content_type

    return TOUCH_CHANNEL_CONTENT_TYPE.get(task.touch_channel, "私聊话术")


def load_generation_context(db: Session, strategy_task_id: int):
    task = db.query(TouchStrategyTask).filter(
        TouchStrategyTask.id == strategy_task_id
    ).first()

    if not task:
        raise ValueError("触达策略任务不存在")

    user = db.query(PrivateUser).filter(
        PrivateUser.id == task.user_id
    ).first()

    if not user:
        raise ValueError("用户不存在")

    segment = db.query(UserSegment).filter(
        UserSegment.user_id == task.user_id
    ).first()

    if not segment:
        raise ValueError("用户分层不存在，请先执行用户分层判断")

    return task, user, segment


def build_user_context(user: PrivateUser):
    return {
        "id": user.id,
        "name": user.name,
        "source": user.source,
        "tags": user.tags or [],
        "purchase_status": user.purchase_status,
        "operation_status": user.operation_status,
    }


def build_retrieval_query(
    task: TouchStrategyTask,
    user: PrivateUser,
    segment: UserSegment,
    content_type: str,
):
    return (
        f"用户名称：{user.name}\n"
        f"用户标签：{user.tags or []}\n"
        f"购买状态：{user.purchase_status}\n"
        f"运营状态：{user.operation_status}\n"
        f"用户来源：{user.source}\n"
        f"用户分层：{segment.segment_type}\n"
        f"触达渠道：{task.touch_channel}\n"
        f"内容类型：{content_type}\n"
        f"策略理由：{task.strategy_reason}\n"
        f"目标人群：{task.target_crowd}\n"
        "请检索相关产品资料、活动规则、品牌规范和运营SOP。"
    )


def build_reference_sources(knowledge: dict):
    references = []

    for collection_name, rows in knowledge.items():
        for row in rows:
            references.append({
                "collection": collection_name,
                "doc_name": row.get("doc_name"),
                "knowledge_type": row.get("knowledge_type"),
                "chunk_title": row.get("chunk_title"),
                "version": row.get("version"),
                "source_path": row.get("source_path"),
            })

    return references


def build_common_prompt_data(
    task: TouchStrategyTask,
    user: PrivateUser,
    segment: UserSegment,
    content_type: str,
    knowledge: dict,
    examples: list[dict],
):
    return {
        "strategy_task": {
            "id": task.id,
            "user_id": task.user_id,
            "segment_type": task.segment_type,
            "touch_channel": task.touch_channel,
            "strategy_reason": task.strategy_reason,
            "target_crowd": task.target_crowd,
        },
        "user": build_user_context(user),
        "user_segment": {
            "segment_type": segment.segment_type,
            "touch_priority": segment.touch_priority,
            "segment_basis": segment.segment_basis,
            "confidence_score": float(segment.confidence_score),
        },
        "content_type": content_type,
        "knowledge": knowledge,
        "content_examples": examples,
    }


def build_content_messages(
    task: TouchStrategyTask,
    user: PrivateUser,
    segment: UserSegment,
    content_type: str,
    knowledge: dict,
    examples: list[dict],
):
    prompt_data = build_common_prompt_data(
        task=task,
        user=user,
        segment=segment,
        content_type=content_type,
        knowledge=knowledge,
        examples=examples,
    )

    return [
        SystemMessage(content=(
            "你是私域运营内容生成助手。"
            "你必须根据用户画像、用户分层、触达策略、产品资料、活动规则、品牌规范、运营SOP和历史话术案例生成内容。"
            "不得编造资料中没有的价格、权益、活动时间和承诺。"
            "不得使用绝对化、夸大、违规表达。"
            "你必须只输出 JSON，不要输出解释。"
            "JSON 字段必须包含 content_text、brand_tone_score。"
            "brand_tone_score 是 0 到 1 的数字。"
        )),
        HumanMessage(content=(
            f"输入数据：{json.dumps(prompt_data, ensure_ascii=False)}\n"
            "请生成对应内容。输出示例："
            '{"content_text":"您好，看到您最近关注护肤活动，我帮您整理了当前适合了解的信息。","brand_tone_score":0.82}'
        )),
    ]


def build_channel_adapt_messages(
    task: TouchStrategyTask,
    user: PrivateUser,
    segment: UserSegment,
    channel: str,
    content_type: str,
    base_content: str,
    knowledge: dict,
    examples: list[dict],
):
    prompt_data = build_common_prompt_data(
        task=task,
        user=user,
        segment=segment,
        content_type=content_type,
        knowledge=knowledge,
        examples=examples,
    )
    prompt_data["target_channel"] = channel
    prompt_data["channel_tone"] = CHANNEL_TONE.get(channel, "通用，清晰自然")
    prompt_data["base_content"] = base_content

    return [
        SystemMessage(content=(
            "你是私域运营多渠道内容适配助手。"
            "如果 base_content 有内容，你要把基础内容改写为目标渠道版本。"
            "如果 base_content 为空，你要直接根据输入资料生成目标渠道内容。"
            "必须保留产品、活动、价格、权益等事实依据，不得新增资料中没有的信息。"
            "必须符合目标渠道语气和格式。"
            "你必须只输出 JSON，不要输出解释。"
            "JSON 字段必须包含 content_text、brand_tone_score。"
        )),
        HumanMessage(content=(
            f"输入数据：{json.dumps(prompt_data, ensure_ascii=False)}\n"
            "请输出适配后的渠道内容。"
        )),
    ]


def parse_llm_json(content):
    if isinstance(content, list):
        content = "".join(str(item) for item in content)

    text = str(content).strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:].strip()

    return json.loads(text)


def normalize_llm_result(result: ContentLLMResult):
    result.brand_tone_score = min(max(result.brand_tone_score, 0), 1)
    return result


def call_llm_for_content(
    task: TouchStrategyTask,
    user: PrivateUser,
    segment: UserSegment,
    content_type: str,
    knowledge: dict,
    examples: list[dict],
):
    llm = get_chat_model()
    messages = build_content_messages(
        task=task,
        user=user,
        segment=segment,
        content_type=content_type,
        knowledge=knowledge,
        examples=examples,
    )

    response = llm.invoke(messages)
    data = parse_llm_json(response.content)
    return normalize_llm_result(ContentLLMResult(**data))


def call_llm_for_channel_adapt(
    task: TouchStrategyTask,
    user: PrivateUser,
    segment: UserSegment,
    channel: str,
    content_type: str,
    base_content: str,
    knowledge: dict,
    examples: list[dict],
):
    llm = get_chat_model()
    messages = build_channel_adapt_messages(
        task=task,
        user=user,
        segment=segment,
        channel=channel,
        content_type=content_type,
        base_content=base_content,
        knowledge=knowledge,
        examples=examples,
    )

    response = llm.invoke(messages)
    data = parse_llm_json(response.content)
    return normalize_llm_result(ContentLLMResult(**data))


def get_next_version(db: Session, strategy_task_id: int, content_type: str):
    latest = db.query(ContentDraft).filter(
        ContentDraft.strategy_task_id == strategy_task_id,
        ContentDraft.content_type == content_type,
    ).order_by(
        ContentDraft.version.desc()
    ).first()

    if not latest:
        return 1

    return latest.version + 1


def create_draft_with_review(
    db: Session,
    strategy_task_id: int,
    content_type: str,
    content_text: str,
    reference_sources: list[dict],
    brand_tone_score: float,
):
    draft = ContentDraft(
        strategy_task_id=strategy_task_id,
        content_type=content_type,
        content_text=content_text,
        reference_sources=reference_sources,
        version=get_next_version(db, strategy_task_id, content_type),
        brand_tone_score=brand_tone_score,
        created_at=datetime.now(),
    )

    db.add(draft)
    db.commit()
    db.refresh(draft)

    review_log = ComplianceReviewLog(
        content_draft_id=draft.id,
        review_status="待审核",
    )

    db.add(review_log)
    db.commit()

    return {
        "draft_id": draft.id,
        "strategy_task_id": draft.strategy_task_id,
        "content_type": draft.content_type,
        "content_text": draft.content_text,
        "reference_sources": draft.reference_sources or [],
        "version": draft.version,
        "brand_tone_score": float(draft.brand_tone_score),
        "review_status": review_log.review_status,
        "created_at": draft.created_at,
    }


def prepare_generation_materials(
    task: TouchStrategyTask,
    user: PrivateUser,
    segment: UserSegment,
    content_type: str,
):
    query = build_retrieval_query(task, user, segment, content_type)
    knowledge = search_all_knowledge(query)
    examples = search_content_examples(
        query=query,
        content_type=content_type,
        limit=3,
    )
    references = build_reference_sources(knowledge)
    return knowledge, examples, references


def generate_content_draft(
    db: Session,
    strategy_task_id: int,
    request_content_type: str | None = None,
):
    task, user, segment = load_generation_context(db, strategy_task_id)
    content_type = decide_content_type(task, request_content_type)
    knowledge, examples, references = prepare_generation_materials(
        task=task,
        user=user,
        segment=segment,
        content_type=content_type,
    )

    llm_result = call_llm_for_content(
        task=task,
        user=user,
        segment=segment,
        content_type=content_type,
        knowledge=knowledge,
        examples=examples,
    )

    return create_draft_with_review(
        db=db,
        strategy_task_id=task.id,
        content_type=content_type,
        content_text=llm_result.content_text,
        reference_sources=references,
        brand_tone_score=llm_result.brand_tone_score,
    )


def generate_multi_channel_content(
    db: Session,
    strategy_task_id: int,
    channels: list[str],
    base_draft_id: int | None = None,
):
    task, user, segment = load_generation_context(db, strategy_task_id)

    base_content = ""
    if base_draft_id:
        base_draft = db.query(ContentDraft).filter(
            ContentDraft.id == base_draft_id,
            ContentDraft.strategy_task_id == strategy_task_id,
        ).first()

        if not base_draft:
            raise ValueError("基础内容草稿不存在")

        base_content = base_draft.content_text or ""

    drafts = []
    for channel in channels:
        content_type = CHANNEL_CONTENT_TYPE.get(channel)
        if not content_type:
            raise ValueError(f"不支持的渠道：{channel}")

        knowledge, examples, references = prepare_generation_materials(
            task=task,
            user=user,
            segment=segment,
            content_type=content_type,
        )

        llm_result = call_llm_for_channel_adapt(
            task=task,
            user=user,
            segment=segment,
            channel=channel,
            content_type=content_type,
            base_content=base_content,
            knowledge=knowledge,
            examples=examples,
        )

        draft = create_draft_with_review(
            db=db,
            strategy_task_id=task.id,
            content_type=content_type,
            content_text=llm_result.content_text,
            reference_sources=references,
            brand_tone_score=llm_result.brand_tone_score,
        )
        drafts.append(draft)

    return {
        "strategy_task_id": strategy_task_id,
        "drafts": drafts,
    }


def get_latest_review_status(db: Session, content_draft_id: int):
    latest_log = db.query(ComplianceReviewLog).filter(
        ComplianceReviewLog.content_draft_id == content_draft_id,
    ).order_by(
        ComplianceReviewLog.reviewed_at.desc(),
        ComplianceReviewLog.id.desc(),
    ).first()

    return latest_log.review_status if latest_log else "待审核"


def build_content_draft_out(db: Session, draft: ContentDraft):
    return {
        "draft_id": draft.id,
        "strategy_task_id": draft.strategy_task_id,
        "content_type": draft.content_type,
        "content_text": draft.content_text,
        "reference_sources": draft.reference_sources or [],
        "version": draft.version,
        "brand_tone_score": float(draft.brand_tone_score),
        "review_status": get_latest_review_status(db, draft.id),
        "created_at": draft.created_at,
    }


def list_content_drafts(
    db: Session,
    strategy_task_id: int | None = None,
    page: int = 1,
    page_size: int = 10,
):
    query = db.query(ContentDraft)

    if strategy_task_id is not None:
        query = query.filter(ContentDraft.strategy_task_id == strategy_task_id)

    total = query.count()
    items = query.order_by(
        ContentDraft.id.desc()
    ).offset(
        (page - 1) * page_size
    ).limit(
        page_size
    ).all()

    return {
        "total": total,
        "items": [build_content_draft_out(db, item) for item in items],
    }


def update_content_draft(
    db: Session,
    draft_id: int,
    content_text: str,
):
    draft = db.query(ContentDraft).filter(
        ContentDraft.id == draft_id
    ).first()

    if not draft:
        raise ValueError("内容草稿不存在")

    draft.content_text = content_text
    draft.version = get_next_version(db, draft.strategy_task_id, draft.content_type)
    draft.created_at = datetime.now()

    db.add(ComplianceReviewLog(
        content_draft_id=draft.id,
        review_status="待审核",
    ))

    db.commit()
    db.refresh(draft)

    return build_content_draft_out(db, draft)
