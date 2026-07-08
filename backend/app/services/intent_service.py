import json

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.llm_client import get_chat_model
from app.models.community_interaction import CommunityInteraction
from app.services.keyword_service import extract_rule_keywords
ALLOWED_INTENT_LABELS = {"需求", "兴趣", "吐槽", "沉默", "无关"}
ALLOWED_SENTIMENTS = {"正面", "中性", "负面"}


class IntentLLMResult(BaseModel):
    intent_label: str
    sentiment: str
    keywords: list[str]

def build_intent_messages(message_content: str, rule_keywords: list[str]):
    return [
        SystemMessage(content=(
            "你是私域社群运营分析助手。"
            "请分析一条已通过噪声过滤的群聊消息。"
            "你必须只输出 JSON，不要输出解释。"
            "JSON 字段必须包含 intent_label、sentiment、keywords。"
            "intent_label 只能是：需求、兴趣、吐槽、沉默、无关。"
            "sentiment 只能是：正面、中性、负面。"
        )),
        HumanMessage(content=(
            f"消息内容：{message_content}\n"
            f"规则抽取关键词：{rule_keywords}\n"
            "请输出 JSON，例如："
            '{"intent_label":"需求","sentiment":"中性","keywords":["价格","活动"]}'
        ))
    ]

def parse_llm_json(content):
    if isinstance(content, list):
        content = "".join(str(item) for item in content)

    return json.loads(content)

def call_llm_for_intent(message_content: str, rule_keywords: list[str]):
    llm = get_chat_model()
    messages = build_intent_messages(message_content, rule_keywords)

    response = llm.invoke(messages)
    data = parse_llm_json(response.content)

    return IntentLLMResult(**data)

def normalize_llm_result(result: IntentLLMResult):
    intent_label = result.intent_label
    sentiment = result.sentiment
    keywords = result.keywords

    if intent_label not in ALLOWED_INTENT_LABELS:
        intent_label = "兴趣"

    if sentiment not in ALLOWED_SENTIMENTS:
        sentiment = "中性"

    if not isinstance(keywords, list):
        keywords = []

    return IntentLLMResult(
        intent_label=intent_label,
        sentiment=sentiment,
        keywords=keywords
    )

def merge_keywords(rule_keywords: list[str], llm_keywords: list[str]):
    return list(dict.fromkeys(rule_keywords + llm_keywords))

def recognize_interaction_intent(db: Session, message_id: int):
    interaction = db.query(CommunityInteraction).filter(
        CommunityInteraction.id == message_id
    ).first()

    if not interaction:
        return None

    if interaction.intent_label != "有效":
        raise ValueError("当前消息不是有效消息，无需进行意向识别")

    message_content = interaction.message_content or ""

    rule_keywords = extract_rule_keywords(message_content)
    llm_result = call_llm_for_intent(message_content, rule_keywords)
    llm_result = normalize_llm_result(llm_result)

    final_keywords = merge_keywords(rule_keywords, llm_result.keywords)

    interaction.keywords = final_keywords
    interaction.intent_label = llm_result.intent_label
    interaction.sentiment = llm_result.sentiment

    db.commit()
    db.refresh(interaction)

    return {
        "message_id": interaction.id,
        "intent_label": interaction.intent_label,
        "sentiment": interaction.sentiment,
        "keywords": interaction.keywords
    }