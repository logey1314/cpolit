import json
from datetime import datetime, timedelta

from redis.exceptions import RedisError
from sqlalchemy.orm import Session

from app.core.redis_client import get_redis_client
from app.models.compliance_review_log import ComplianceReviewLog
from app.models.content_draft import ContentDraft
from app.models.operation_task_log import OperationTaskLog
from app.models.private_user import PrivateUser
from app.models.touch_strategy_task import TouchStrategyTask
from app.services.mcp_mock_adapter import create_todo


MAX_RETRY_COUNT = 3

CHANNEL_TARGET_SYSTEM = {
    "私聊": "企微",
    "群发": "企微",
    "社群话题": "社群",
    "群公告": "社群",
    "活动邀约": "企微",
    "朋友圈": "企微",
    "短信": "短信",
    "暂缓": "CRM",
}

CHANNEL_TASK_TYPE = {
    "私聊": "私聊发送",
    "群发": "群发发送",
    "社群话题": "社群话题发布",
    "群公告": "群公告发布",
    "活动邀约": "活动邀约",
    "朋友圈": "朋友圈发布",
    "短信": "短信发送",
    "暂缓": "客户备注",
}


def get_latest_review_status(db: Session, content_draft_id: int):
    latest_log = db.query(ComplianceReviewLog).filter(
        ComplianceReviewLog.content_draft_id == content_draft_id,
    ).order_by(
        ComplianceReviewLog.reviewed_at.desc(),
        ComplianceReviewLog.id.desc(),
    ).first()

    return latest_log.review_status if latest_log else None


def ensure_can_create_task(
    strategy: TouchStrategyTask,
    content: ContentDraft,
    review_status: str | None,
):
    if strategy.confirm_status != "已确认":
        raise ValueError("触达策略未确认，不能生成运营任务")

    if content.strategy_task_id != strategy.id:
        raise ValueError("内容草稿不属于当前触达策略任务")

    if review_status != "通过":
        raise ValueError("内容未通过合规审核，不能生成运营任务")


def map_channel_to_system(channel: str | None):
    return CHANNEL_TARGET_SYSTEM.get(channel or "", "CRM")


def map_channel_to_task_type(channel: str | None):
    return CHANNEL_TASK_TYPE.get(channel or "", "客户备注")


def build_request_params(strategy: TouchStrategyTask, content: ContentDraft):
    return {
        "user_id": strategy.user_id,
        "strategy_task_id": strategy.id,
        "content_draft_id": content.id,
        "touch_channel": strategy.touch_channel,
        "content_type": content.content_type,
        "content": content.content_text,
    }


def push_remind_queue(task: OperationTaskLog):
    redis_client = get_redis_client()
    if not redis_client:
        return False

    assignee = task.assignee or "default"
    key = f"queue:remind:{assignee}"
    payload = {
        "task_id": task.id,
        "strategy_task_id": task.strategy_task_id,
        "target_system": task.target_system,
        "task_type": task.task_type,
        "assignee": task.assignee,
        "remind_time": task.remind_time.isoformat() if task.remind_time else None,
    }

    try:
        redis_client.lpush(key, json.dumps(payload, ensure_ascii=False))
    except RedisError:
        return False

    return True


def execute_external_todo(task: OperationTaskLog):
    result = create_todo(
        target_system=task.target_system,
        request_params=task.request_params or {},
    )
    return result


def create_operation_task(
    db: Session,
    strategy_task_id: int,
    content_draft_id: int,
):
    strategy = db.query(TouchStrategyTask).filter(
        TouchStrategyTask.id == strategy_task_id
    ).first()

    if not strategy:
        raise ValueError("触达策略任务不存在")

    content = db.query(ContentDraft).filter(
        ContentDraft.id == content_draft_id
    ).first()

    if not content:
        raise ValueError("内容草稿不存在")

    review_status = get_latest_review_status(db, content_draft_id)
    ensure_can_create_task(strategy, content, review_status)

    task = OperationTaskLog(
        strategy_task_id=strategy.id,
        target_system=map_channel_to_system(strategy.touch_channel),
        task_type=map_channel_to_task_type(strategy.touch_channel),
        request_params=build_request_params(strategy, content),
        response_status="待执行",
        retry_count=0,
        assignee=strategy.assignee or "默认负责人",
        remind_time=strategy.plan_time or datetime.now() + timedelta(hours=1),
        created_at=datetime.now(),
    )

    db.add(task)
    db.commit()
    db.refresh(task)

    push_remind_queue(task)

    return {
        "task_id": task.id,
        "status": task.response_status,
        "target_system": task.target_system,
        "task_type": task.task_type,
    }


def update_operation_task_status(
    db: Session,
    task_id: int,
    status: str,
    fail_reason: str | None = None,
):
    allowed = {"待执行", "成功", "失败"}
    if status not in allowed:
        raise ValueError("status 只能是：待执行、成功、失败")

    task = db.query(OperationTaskLog).filter(
        OperationTaskLog.id == task_id
    ).first()

    if not task:
        raise ValueError("运营任务不存在")

    task.response_status = status
    task.fail_reason = fail_reason

    db.commit()
    db.refresh(task)

    return {
        "task_id": task.id,
        "updated_status": task.response_status,
        "fail_reason": task.fail_reason,
    }


def retry_operation_task(db: Session, task_id: int):
    task = db.query(OperationTaskLog).filter(
        OperationTaskLog.id == task_id
    ).first()

    if not task:
        raise ValueError("运营任务不存在")

    if task.response_status != "失败":
        raise ValueError("只有失败任务可以重试")

    if task.retry_count >= MAX_RETRY_COUNT:
        raise ValueError("任务重试次数已达到上限")

    task.retry_count += 1

    try:
        execute_external_todo(task)
        task.response_status = "成功"
        task.fail_reason = None
    except Exception as e:
        task.response_status = "失败"
        task.fail_reason = str(e)

    db.commit()
    db.refresh(task)

    if task.response_status == "成功":
        push_remind_queue(task)

    return {
        "task_id": task.id,
        "status": task.response_status,
        "retry_count": task.retry_count,
        "fail_reason": task.fail_reason,
    }


def build_operation_task_out(task: OperationTaskLog, user_name: str | None = None):
    request_params = task.request_params or {}
    task_instruction = (
        f"在{task.target_system or '目标系统'}执行「{task.task_type or '运营任务'}」，"
        f"使用下方内容触达{user_name or '目标用户'}。"
    )

    return {
        "task_id": task.id,
        "strategy_task_id": task.strategy_task_id,
        "user_id": request_params.get("user_id"),
        "user_name": user_name,
        "target_system": task.target_system,
        "task_type": task.task_type,
        "task_instruction": task_instruction,
        "content": request_params.get("content"),
        "request_params": task.request_params,
        "response_status": task.response_status,
        "fail_reason": task.fail_reason,
        "retry_count": task.retry_count,
        "assignee": task.assignee,
        "remind_time": task.remind_time,
        "created_at": task.created_at,
    }


def list_operation_tasks(
    db: Session,
    assignee: str | None = None,
    response_status: str | None = None,
    page: int = 1,
    page_size: int = 50,
):
    query = db.query(OperationTaskLog)

    if assignee:
        query = query.filter(OperationTaskLog.assignee == assignee)

    if response_status:
        query = query.filter(OperationTaskLog.response_status == response_status)

    total = query.count()
    items = query.order_by(
        OperationTaskLog.id.desc()
    ).offset(
        (page - 1) * page_size
    ).limit(
        page_size
    ).all()

    user_ids = []
    for item in items:
        request_params = item.request_params or {}
        if request_params.get("user_id"):
            user_ids.append(request_params["user_id"])

    users = db.query(PrivateUser).filter(
        PrivateUser.id.in_(user_ids)
    ).all() if user_ids else []
    user_name_map = {user.id: user.name for user in users}

    return {
        "total": total,
        "items": [
            build_operation_task_out(
                item,
                user_name_map.get((item.request_params or {}).get("user_id")),
            )
            for item in items
        ],
    }
