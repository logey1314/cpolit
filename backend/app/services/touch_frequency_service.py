from datetime import datetime, timedelta

from redis.exceptions import RedisError
from sqlalchemy.orm import Session

from app.core.redis_client import get_redis_client
from app.models.touch_frequency_rule import TouchFrequencyRule
from app.models.touch_strategy_task import TouchStrategyTask


DEFAULT_MAX_COUNT = 2
DEFAULT_WINDOW_HOURS = 24


def build_frequency_targets(
    user_id: int,
    channel: str,
    community_id: str | None = None,
    activity_id: str | None = None,
):
    targets = [
        {
            "dimension": "用户",
            "dimension_id": str(user_id),
            "channel": channel,
            "key": f"freq:user:{user_id}:{channel}",
        },
        {
            "dimension": "渠道",
            "dimension_id": "all",
            "channel": channel,
            "key": f"freq:channel:{channel}",
        },
    ]

    if community_id:
        targets.append({
            "dimension": "社群",
            "dimension_id": str(community_id),
            "channel": channel,
            "key": f"freq:community:{community_id}:{channel}",
        })

    if activity_id:
        targets.append({
            "dimension": "活动",
            "dimension_id": str(activity_id),
            "channel": channel,
            "key": f"freq:activity:{activity_id}:{channel}",
        })

    return targets


def get_frequency_rule(
    db: Session,
    dimension: str,
    dimension_id: str,
    channel: str,
):
    exact_rule = db.query(TouchFrequencyRule).filter(
        TouchFrequencyRule.dimension == dimension,
        TouchFrequencyRule.dimension_id == dimension_id,
        TouchFrequencyRule.channel == channel,
        TouchFrequencyRule.is_active == 1,
    ).first()

    if exact_rule:
        return exact_rule

    global_rule = db.query(TouchFrequencyRule).filter(
        TouchFrequencyRule.dimension == dimension,
        TouchFrequencyRule.dimension_id == "all",
        TouchFrequencyRule.channel == channel,
        TouchFrequencyRule.is_active == 1,
    ).first()

    return global_rule


def get_rule_limits(rule: TouchFrequencyRule | None):
    if not rule:
        return DEFAULT_MAX_COUNT, DEFAULT_WINDOW_HOURS

    return rule.max_count, rule.window_hours


def get_redis_count(key: str):
    redis_client = get_redis_client()
    if not redis_client:
        return None

    try:
        value = redis_client.get(key)
    except RedisError:
        return None

    return int(value or 0)


def count_mysql_fallback(
    db: Session,
    dimension: str,
    dimension_id: str,
    channel: str,
    window_hours: int,
):
    since_time = datetime.now() - timedelta(hours=window_hours)

    query = db.query(TouchStrategyTask).filter(
        TouchStrategyTask.touch_channel == channel,
        TouchStrategyTask.created_at >= since_time,
    )

    if dimension == "用户":
        query = query.filter(TouchStrategyTask.user_id == int(dimension_id))

    # 当前项目还没有社群、活动、任务执行日志字段，先用全渠道统计兜底。
    return query.count()


def check_one_target(db: Session, target: dict):
    rule = get_frequency_rule(
        db=db,
        dimension=target["dimension"],
        dimension_id=target["dimension_id"],
        channel=target["channel"],
    )
    max_count, window_hours = get_rule_limits(rule)

    current_count = get_redis_count(target["key"])
    if current_count is None:
        current_count = count_mysql_fallback(
            db=db,
            dimension=target["dimension"],
            dimension_id=target["dimension_id"],
            channel=target["channel"],
            window_hours=window_hours,
        )

    allowed = current_count < max_count
    reason = None
    if not allowed:
        reason = (
            f"{target['dimension']} {target['dimension_id']} 在 {window_hours} 小时内 "
            f"{target['channel']} 触达 {current_count} 次，已达到限制 {max_count} 次"
        )

    return {
        "dimension": target["dimension"],
        "dimension_id": target["dimension_id"],
        "channel": target["channel"],
        "allowed": allowed,
        "current_count": current_count,
        "max_count": max_count,
        "window_hours": window_hours,
        "reason": reason,
    }


def check_frequency(
    db: Session,
    user_id: int,
    channel: str,
    community_id: str | None = None,
    activity_id: str | None = None,
):
    targets = build_frequency_targets(
        user_id=user_id,
        channel=channel,
        community_id=community_id,
        activity_id=activity_id,
    )

    details = [check_one_target(db, target) for target in targets]
    blocked = [item for item in details if not item["allowed"]]

    if blocked:
        first_blocked = blocked[0]
        return {
            "allowed": False,
            "passed": False,
            "reason": first_blocked["reason"],
            "current_count": first_blocked["current_count"],
            "used_count": first_blocked["current_count"],
            "max_count": first_blocked["max_count"],
            "window_hours": first_blocked["window_hours"],
            "details": details,
        }

    user_detail = details[0]
    return {
        "allowed": True,
        "passed": True,
        "reason": None,
        "current_count": user_detail["current_count"],
        "used_count": user_detail["current_count"],
        "max_count": user_detail["max_count"],
        "window_hours": user_detail["window_hours"],
        "details": details,
    }


def increment_one_target(db: Session, target: dict):
    rule = get_frequency_rule(
        db=db,
        dimension=target["dimension"],
        dimension_id=target["dimension_id"],
        channel=target["channel"],
    )
    _, window_hours = get_rule_limits(rule)

    redis_client = get_redis_client()
    if not redis_client:
        raise ValueError("Redis 不可用，无法写入频控计数")

    try:
        new_count = redis_client.incr(target["key"])
        redis_client.expire(target["key"], window_hours * 3600)
    except RedisError as e:
        raise ValueError(f"Redis 写入频控计数失败：{e}") from e

    return int(new_count)


def increment_frequency(
    db: Session,
    user_id: int,
    channel: str,
    community_id: str | None = None,
    activity_id: str | None = None,
):
    targets = build_frequency_targets(
        user_id=user_id,
        channel=channel,
        community_id=community_id,
        activity_id=activity_id,
    )

    counts = {}
    for target in targets:
        counts[target["key"]] = increment_one_target(db, target)

    return {
        "user_id": user_id,
        "channel": channel,
        "counts": counts,
    }


def build_frequency_rule_out(rule: TouchFrequencyRule):
    return {
        "id": rule.id,
        "dimension": rule.dimension,
        "dimension_id": rule.dimension_id,
        "channel": rule.channel,
        "max_count": rule.max_count,
        "window_hours": rule.window_hours,
        "rule_description": rule.rule_description,
        "is_active": rule.is_active,
    }


def list_frequency_rules(
    db: Session,
    dimension: str | None = None,
    channel: str | None = None,
    page: int = 1,
    page_size: int = 50,
):
    query = db.query(TouchFrequencyRule)

    if dimension:
        query = query.filter(TouchFrequencyRule.dimension == dimension)

    if channel:
        query = query.filter(TouchFrequencyRule.channel == channel)

    total = query.count()
    items = query.order_by(
        TouchFrequencyRule.id.desc()
    ).offset(
        (page - 1) * page_size
    ).limit(
        page_size
    ).all()

    return {
        "total": total,
        "items": [build_frequency_rule_out(item) for item in items],
    }


def update_frequency_rule(
    db: Session,
    rule_id: int,
    max_count: int,
    window_hours: int,
    is_active: int = 1,
    rule_description: str | None = None,
):
    rule = db.query(TouchFrequencyRule).filter(
        TouchFrequencyRule.id == rule_id
    ).first()

    if not rule:
        raise ValueError("频控规则不存在")

    rule.max_count = max_count
    rule.window_hours = window_hours
    rule.is_active = is_active
    rule.rule_description = rule_description

    db.commit()
    db.refresh(rule)

    return build_frequency_rule_out(rule)
