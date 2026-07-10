import os

from dotenv import load_dotenv


load_dotenv()


class RedisConfig:
    enabled: bool = os.getenv("REDIS_ENABLED", "true").lower() == "true"
    host: str = os.getenv("REDIS_HOST", "82.156.215.91")
    port: int = int(os.getenv("REDIS_PORT", "63368"))
    db: int = int(os.getenv("REDIS_DB", "0"))
    password: str | None = os.getenv("REDIS_PASSWORD") or None


redis_config = RedisConfig()