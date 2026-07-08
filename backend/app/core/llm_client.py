from langchain_openai import ChatOpenAI

from app.core.llm_config import llm_config


def get_chat_model():
    if not llm_config.api_key:
        raise ValueError("LLM_API_KEY 未配置")

    return ChatOpenAI(
        model=llm_config.model,
        api_key=llm_config.api_key,
        base_url=llm_config.base_url,
        temperature=llm_config.temperature,
        timeout=llm_config.timeout_seconds,
        max_tokens=llm_config.max_tokens
    )