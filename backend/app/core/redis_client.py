import redis

from app.core.redis_config import redis_config


def get_redis_client():
    if not redis_config.enabled:
        return None

    return redis.Redis(
        host=redis_config.host,
        port=redis_config.port,
        db=redis_config.db,
        password=redis_config.password,
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=5
    )