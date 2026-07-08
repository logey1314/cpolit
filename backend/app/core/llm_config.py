import os

from dotenv import load_dotenv


load_dotenv()


class LLMConfig:
    provider: str = os.getenv("LLM_PROVIDER", "openai_compatible")
    model: str = os.getenv("LLM_MODEL", "deepseek-v4-flash")
    api_key: str | None = os.getenv("LLM_API_KEY")
    base_url: str = os.getenv("LLM_BASE_URL", "https://api.deepseek.com/v1")
    temperature: float = float(os.getenv("LLM_TEMPERATURE", "0.3"))
    timeout_seconds: int = int(os.getenv("LLM_TIMEOUT_SECONDS", "60"))
    max_tokens: int = int(os.getenv("DEFAULT_MAX_TOKENS", "2048"))


llm_config = LLMConfig()