import json
import re
from datetime import datetime

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.llm_client import get_chat_model
from app.models.compliance_review_log import ComplianceReviewLog
from app.models.content_draft import ContentDraft
from app.models.private_user import PrivateUser
from app.models.touch_strategy_task import TouchStrategyTask
from app.services.knowledge_retrieval_service import search_knowledge_collection, get_milvus_client


FORBIDDEN_WORDS = [
    "全网最低价",
    "全网最便宜",
    "保证有效",
    "百分百有效",
    "永久修复",
    "彻底根治",
    "无条件退款",
    "随便退",
]

EXAGGERATION_WORDS = [
    "一定会好",
    "立刻见效",
    "根治",
    "永久",
    "保证",
    "最后机会",
    "错过没有了",
]

COMPETITOR_PATTERNS = [
    r"比.{1,20}好",
    r"吊打",
    r"完胜",
    r"秒杀",
    r"竞品",
]

PHONE_PATTERN = re.compile(r"1[3-9]\d{9}")
ID_CARD_PATTERN = re.compile(r"\d{17}[\dXx]")
PRICE_PATTERN = re.compile(r"(\d+(?:\.\d+)?)\s*元")
BENEFIT_PATTERN = re.compile(r"满\s*\d+\s*减\s*\d+")


class ComplianceLLMResult(BaseModel):
    has_exaggeration: bool = False
    exaggeration_detail: str | None = None
    exaggeration_suggestion: str | None = None
    brand_tone_score: float = 0.80
    tone_detail: str | None = None
    tone_suggestion: str | None = None


def add_risk(risks: list[dict], risk_type: str, detail: str, suggestion: str | None = None):
    risks.append({
        "risk_type": risk_type,
        "risk_detail": detail,
        "suggestion": suggestion,
    })


def check_forbidden_words(content: str, risks: list[dict]):
    for word in FORBIDDEN_WORDS:
        if word in content:
            add_risk(
                risks,
                "禁用词",
                f"命中禁用词：{word}",
                "删除禁用词，改为更准确、克制的表达。",
            )


def check_competitor_expression(content: str, risks: list[dict]):
    for pattern in COMPETITOR_PATTERNS:
        if re.search(pattern, content):
            add_risk(
                risks,
                "竞品表达",
                f"命中竞品或攻击性表达规则：{pattern}",
                "避免点名或贬低竞品，改为客观描述自身产品特点。",
            )


def check_privacy_leak(content: str, risks: list[dict]):
    if PHONE_PATTERN.search(content):
        add_risk(
            risks,
            "隐私泄露",
            "内容中疑似包含手机号。",
            "删除手机号等个人敏感信息。",
        )

    if ID_CARD_PATTERN.search(content):
        add_risk(
            risks,
            "隐私泄露",
            "内容中疑似包含身份证号。",
            "删除身份证号等个人敏感信息。",
        )

    if "购买记录" in content or "订单号" in content:
        add_risk(
            risks,
            "隐私泄露",
            "内容中疑似公开用户购买记录或订单信息。",
            "不要在公开渠道暴露用户购买记录、订单号等信息。",
        )


def collect_price_and_benefit_terms(content: str):
    terms = []
    terms.extend(match.group(0) for match in PRICE_PATTERN.finditer(content))
    terms.extend(match.group(0) for match in BENEFIT_PATTERN.finditer(content))
    return list(dict.fromkeys(terms))


def check_price_benefit(content: str, risks: list[dict]):
    terms = collect_price_and_benefit_terms(content)
    if not terms:
        return

    client = get_milvus_client()
    try:
        for term in terms:
            query = f"价格权益 活动规则 产品手册 {term}"
            rows = []
            rows.extend(search_knowledge_collection(client, "product_knowledge", query, limit=3))
            rows.extend(search_knowledge_collection(client, "activity_rules", query, limit=3))

            evidence_text = "\n".join(row.get("content") or "" for row in rows)
            normalized_term = term.replace(" ", "")
            normalized_evidence = evidence_text.replace(" ", "")

            if normalized_term not in normalized_evidence:
                add_risk(
                    risks,
                    "价格权益",
                    f"内容中出现价格或权益：{term}，但未在当前产品资料或活动规则中找到明确依据。",
                    "请核对当前版本产品手册或活动规则；无依据时删除该价格/权益表达。",
                )
    finally:
        client.close()


def check_exaggeration_by_rules(content: str, risks: list[dict]):
    for word in EXAGGERATION_WORDS:
        if word in content:
            add_risk(
                risks,
                "夸大承诺",
                f"命中夸大或强承诺表达：{word}",
                "改为基于资料依据的客观描述，避免保证式承诺。",
            )


def parse_llm_json(content):
    if isinstance(content, list):
        content = "".join(str(item) for item in content)

    text = str(content).strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:].strip()

    return json.loads(text)


def call_llm_for_compliance(content: str):
    client = get_milvus_client()
    try:
        brand_rows = search_knowledge_collection(
            client=client,
            collection_name="brand_guidelines",
            query=f"品牌语气 禁用词 夸大承诺 合规边界 {content}",
            limit=3,
        )
    finally:
        client.close()

    llm = get_chat_model()
    messages = [
        SystemMessage(content=(
            "你是品牌合规审核助手。"
            "请检查内容是否存在夸大承诺、饥饿营销、品牌语气不一致。"
            "必须只输出 JSON，不要输出解释。"
            "JSON 字段包含：has_exaggeration、exaggeration_detail、exaggeration_suggestion、"
            "brand_tone_score、tone_detail、tone_suggestion。"
            "brand_tone_score 是 0 到 1 的数字，越高代表越符合品牌语气。"
        )),
        HumanMessage(content=(
            f"品牌规范片段：{json.dumps(brand_rows, ensure_ascii=False)}\n"
            f"待审核内容：{content}\n"
            "请输出 JSON。"
        )),
    ]

    response = llm.invoke(messages)
    data = parse_llm_json(response.content)
    result = ComplianceLLMResult(**data)
    result.brand_tone_score = min(max(result.brand_tone_score, 0), 1)
    return result


def check_llm_risks(content: str, risks: list[dict]):
    result = call_llm_for_compliance(content)

    if result.has_exaggeration:
        add_risk(
            risks,
            "夸大承诺",
            result.exaggeration_detail or "LLM 判断存在夸大承诺风险。",
            result.exaggeration_suggestion or "删减强承诺表达，改为客观描述。",
        )

    if result.brand_tone_score < 0.60:
        add_risk(
            risks,
            "语气不一致",
            result.tone_detail or f"品牌语气评分偏低：{result.brand_tone_score}",
            result.tone_suggestion or "调整为专业、温和、真诚的品牌语气。",
        )


def decide_review_status(risks: list[dict]):
    if not risks:
        return "通过"

    block_types = {"禁用词", "竞品表达", "隐私泄露"}
    high_risk_types = {"价格权益", "夸大承诺", "语气不一致"}

    if any(risk["risk_type"] in block_types for risk in risks):
        return "拦截"

    if any(risk["risk_type"] in high_risk_types for risk in risks):
        return "高风险待确认"

    return "拦截"


def clear_pending_logs(db: Session, content_draft_id: int):
    pending_logs = db.query(ComplianceReviewLog).filter(
        ComplianceReviewLog.content_draft_id == content_draft_id,
        ComplianceReviewLog.review_status == "待审核",
    ).all()

    for log in pending_logs:
        db.delete(log)

    db.commit()


def save_review_logs(db: Session, content_draft_id: int, review_status: str, risks: list[dict]):
    clear_pending_logs(db, content_draft_id)

    if not risks:
        risks = [{
            "risk_type": None,
            "risk_detail": "未发现明显合规风险",
            "suggestion": None,
        }]

    saved_risks = []
    for risk in risks:
        log = ComplianceReviewLog(
            content_draft_id=content_draft_id,
            risk_type=risk.get("risk_type"),
            risk_detail=risk.get("risk_detail"),
            suggestion=risk.get("suggestion"),
            review_status=review_status,
            reviewed_at=datetime.now(),
        )
        db.add(log)
        db.flush()

        saved_risks.append({
            "log_id": log.id,
            "risk_type": log.risk_type,
            "risk_detail": log.risk_detail,
            "suggestion": log.suggestion,
        })

    db.commit()
    return saved_risks


def auto_compliance_review(db: Session, content_draft_id: int):
    draft = db.query(ContentDraft).filter(
        ContentDraft.id == content_draft_id
    ).first()

    if not draft:
        raise ValueError("内容草稿不存在")

    content = draft.content_text or ""
    risks = []

    check_forbidden_words(content, risks)
    check_price_benefit(content, risks)
    check_exaggeration_by_rules(content, risks)
    check_competitor_expression(content, risks)
    check_privacy_leak(content, risks)
    check_llm_risks(content, risks)

    review_status = decide_review_status(risks)
    saved_risks = save_review_logs(db, content_draft_id, review_status, risks)

    return {
        "content_draft_id": content_draft_id,
        "review_status": review_status,
        "risks": saved_risks,
    }


def confirm_compliance_log(
    db: Session,
    log_id: int,
    decision: str,
    reviewer: str | None = None,
):
    allowed = {"通过", "拦截", "已修改"}
    if decision not in allowed:
        raise ValueError("decision 只能是：通过、拦截、已修改")

    log = db.query(ComplianceReviewLog).filter(
        ComplianceReviewLog.id == log_id
    ).first()

    if not log:
        raise ValueError("合规审核日志不存在")

    log.review_status = decision
    log.reviewer = reviewer
    log.reviewed_at = datetime.now()

    db.commit()
    db.refresh(log)

    return {
        "log_id": log.id,
        "review_status": log.review_status,
        "reviewer": log.reviewer,
    }


def list_compliance_logs(
    db: Session,
    review_status: str | None = None,
    page: int = 1,
    page_size: int = 20,
):
    query = db.query(
        ComplianceReviewLog,
        ContentDraft,
        TouchStrategyTask,
        PrivateUser,
    ).join(
        ContentDraft,
        ContentDraft.id == ComplianceReviewLog.content_draft_id,
    ).join(
        TouchStrategyTask,
        TouchStrategyTask.id == ContentDraft.strategy_task_id,
    ).join(
        PrivateUser,
        PrivateUser.id == TouchStrategyTask.user_id,
    )

    if review_status:
        query = query.filter(ComplianceReviewLog.review_status == review_status)

    total = query.count()
    rows = query.order_by(
        ComplianceReviewLog.id.desc()
    ).offset(
        (page - 1) * page_size
    ).limit(
        page_size
    ).all()

    return {
        "total": total,
        "items": [
            {
                "log_id": log.id,
                "content_draft_id": log.content_draft_id,
                "strategy_task_id": draft.strategy_task_id,
                "user_id": task.user_id,
                "user_name": user.name,
                "user_source": user.source,
                "touch_channel": task.touch_channel,
                "segment_type": task.segment_type,
                "content_text": draft.content_text,
                "risk_type": log.risk_type,
                "risk_detail": log.risk_detail,
                "suggestion": log.suggestion,
                "review_status": log.review_status,
                "reviewer": log.reviewer,
                "reviewed_at": log.reviewed_at.isoformat() if log.reviewed_at else None,
            }
            for log, draft, task, user in rows
        ],
    }
