import json
from datetime import datetime, timedelta
from typing import TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.llm_client import get_chat_model
from app.models.private_user import PrivateUser
from app.models.touch_strategy_task import TouchStrategyTask
from app.models.user_segment import UserSegment
from app.services.touch_frequency_service import check_frequency


ALLOWED_TOUCH_CHANNELS = {"私聊", "群发", "社群话题", "活动邀约", "朋友圈", "短信", "暂缓"}


class TouchStrategyLLMResult(BaseModel):
    touch_channel: str
    strategy_reason: str
    target_crowd: str


class TouchStrategyState(TypedDict, total=False):
    user_id: int
    operation_goal: str
    user: dict
    segment: dict
    route: str
    frequency_passed: bool
    touch_channel: str
    strategy_reason: str
    target_crowd: str
    confirm_status: str
    plan_time: datetime
    task_id: int


def build_user_context(user: PrivateUser):
    return {
        "id": user.id,
        "name": user.name,
        "source": user.source,
        "tags": user.tags or [],
        "purchase_status": user.purchase_status,
        "operation_status": user.operation_status
    }


def build_segment_context(segment: UserSegment):
    return {
        "segment_type": segment.segment_type,
        "touch_priority": segment.touch_priority,
        "segment_basis": segment.segment_basis,
        "confidence_score": float(segment.confidence_score)
    }


def parse_llm_json(content):
    if isinstance(content, list):
        content = "".join(str(item) for item in content)

    return json.loads(content)


def build_strategy_messages(state: TouchStrategyState):
    prompt_data = {
        "operation_goal": state["operation_goal"],
        "user": state["user"],
        "segment": state["segment"]
    }

    return [
        SystemMessage(content=(
            "你是私域运营触达策略助手。"
            "请根据用户分层、用户画像和运营目标生成触达策略。"
            "你必须只输出 JSON，不要输出解释。"
            "touch_channel 只能是：私聊、群发、社群话题、活动邀约、朋友圈、短信、暂缓。"
            "JSON 字段必须包含 touch_channel、strategy_reason、target_crowd。"
        )),
        HumanMessage(content=(
            f"输入数据：{json.dumps(prompt_data, ensure_ascii=False)}\n"
            "请输出 JSON，例如："
            '{"touch_channel":"私聊","strategy_reason":"用户为高意向未购用户，适合私聊跟进",'
            '"target_crowd":"高意向未购用户"}'
        ))
    ]


def normalize_llm_strategy(result: TouchStrategyLLMResult):
    touch_channel = result.touch_channel

    if touch_channel not in ALLOWED_TOUCH_CHANNELS:
        touch_channel = "社群话题"

    return TouchStrategyLLMResult(
        touch_channel=touch_channel,
        strategy_reason=result.strategy_reason,
        target_crowd=result.target_crowd
    )


def load_context_node(db: Session):
    def node(state: TouchStrategyState):
        user = db.query(PrivateUser).filter(
            PrivateUser.id == state["user_id"]
        ).first()

        if not user:
            raise ValueError("用户不存在")

        segment = db.query(UserSegment).filter(
            UserSegment.user_id == state["user_id"]
        ).first()

        if not segment:
            raise ValueError("用户分层不存在，请先执行用户分层判断")

        state["user"] = build_user_context(user)
        state["segment"] = build_segment_context(segment)

        return state

    return node


def route_strategy_node(state: TouchStrategyState):
    segment_type = state["segment"]["segment_type"]

    if segment_type == "暂缓触达":
        state["route"] = "fixed"
        state["touch_channel"] = "暂缓"
        state["strategy_reason"] = "用户处于暂缓触达状态，7天内不主动触达"
        state["target_crowd"] = "暂缓触达用户"
        state["confirm_status"] = "高风险待确认"
        return state

    if segment_type == "沉默":
        state["route"] = "fixed"
        state["touch_channel"] = "社群话题"
        state["strategy_reason"] = "用户处于沉默状态，仅建议低打扰社群话题触达"
        state["target_crowd"] = "沉默用户"
        state["confirm_status"] = "待确认"
        return state

    if segment_type == "高意向":
        state["route"] = "frequency_check"
        return state

    state["route"] = "llm"
    return state


def choose_route(state: TouchStrategyState):
    return state["route"]


def frequency_check_node(db: Session):
    def node(state: TouchStrategyState):
        result = check_frequency(
            db=db,
            user_id=state["user_id"],
            channel="私聊"
        )

        state["frequency_passed"] = result["passed"]

        if result["passed"]:
            state["route"] = "llm"
        else:
            state["route"] = "fixed"
            state["touch_channel"] = "暂缓"
            state["strategy_reason"] = (
                f"用户近期私聊触达次数为 {result['used_count']}，"
                f"已达到 {result['window_hours']} 小时内最多 {result['max_count']} 次的频控限制，暂缓触达"
            )
            state["target_crowd"] = "频控限制用户"
            state["confirm_status"] = "高风险待确认"

        return state

    return node


def choose_after_frequency(state: TouchStrategyState):
    return state["route"]


def llm_strategy_node(state: TouchStrategyState):
    llm = get_chat_model()
    messages = build_strategy_messages(state)
    response = llm.invoke(messages)

    data = parse_llm_json(response.content)
    result = normalize_llm_strategy(TouchStrategyLLMResult(**data))

    if state["segment"]["segment_type"] == "高意向" and result.touch_channel != "私聊":
        result.touch_channel = "私聊"
        result.strategy_reason = f"用户为高意向分层，优先采用私聊触达。{result.strategy_reason}"

    state["touch_channel"] = result.touch_channel
    state["strategy_reason"] = result.strategy_reason
    state["target_crowd"] = result.target_crowd
    state["confirm_status"] = "待确认"

    return state


def save_strategy_task_node(db: Session):
    def node(state: TouchStrategyState):
        task = TouchStrategyTask(
            user_id=state["user_id"],
            segment_type=state["segment"]["segment_type"],
            touch_channel=state["touch_channel"],
            strategy_reason=state["strategy_reason"],
            target_crowd=state["target_crowd"],
            confirm_status=state.get("confirm_status", "待确认"),
            plan_time=datetime.now() + timedelta(hours=1),
            created_at=datetime.now()
        )

        db.add(task)
        db.commit()
        db.refresh(task)

        state["task_id"] = task.id
        state["plan_time"] = task.plan_time

        return state

    return node


def build_touch_strategy_graph(db: Session):
    graph = StateGraph(TouchStrategyState)

    graph.add_node("load_context", load_context_node(db))
    graph.add_node("route_strategy", route_strategy_node)
    graph.add_node("frequency_check", frequency_check_node(db))
    graph.add_node("llm_strategy", llm_strategy_node)
    graph.add_node("save_strategy_task", save_strategy_task_node(db))

    graph.set_entry_point("load_context")
    graph.add_edge("load_context", "route_strategy")

    graph.add_conditional_edges(
        "route_strategy",
        choose_route,
        {
            "fixed": "save_strategy_task",
            "frequency_check": "frequency_check",
            "llm": "llm_strategy"
        }
    )

    graph.add_conditional_edges(
        "frequency_check",
        choose_after_frequency,
        {
            "fixed": "save_strategy_task",
            "llm": "llm_strategy"
        }
    )

    graph.add_edge("llm_strategy", "save_strategy_task")
    graph.add_edge("save_strategy_task", END)

    return graph.compile()


def generate_touch_strategy(db: Session, user_id: int, operation_goal: str):
    graph = build_touch_strategy_graph(db)

    final_state = graph.invoke({
        "user_id": user_id,
        "operation_goal": operation_goal
    })

    return {
        "task_id": final_state["task_id"],
        "user_id": final_state["user_id"],
        "segment_type": final_state["segment"]["segment_type"],
        "touch_channel": final_state["touch_channel"],
        "strategy_reason": final_state["strategy_reason"],
        "target_crowd": final_state["target_crowd"],
        "confirm_status": final_state["confirm_status"],
        "plan_time": final_state["plan_time"]
    }


def build_touch_strategy_out(task: TouchStrategyTask, user_name: str | None = None):
    return {
        "task_id": task.id,
        "user_id": task.user_id,
        "user_name": user_name,
        "segment_type": task.segment_type,
        "touch_channel": task.touch_channel,
        "strategy_reason": task.strategy_reason,
        "target_crowd": task.target_crowd,
        "confirm_status": task.confirm_status,
        "assignee": task.assignee,
        "plan_time": task.plan_time,
    }


def list_touch_strategies(
    db: Session,
    user_id: int | None = None,
    confirm_status: str | None = None,
    keyword: str | None = None,
    segment_type: str | None = None,
    touch_channel: str | None = None,
    page: int = 1,
    page_size: int = 10,
):
    query = db.query(TouchStrategyTask)

    if user_id is not None:
        query = query.filter(TouchStrategyTask.user_id == user_id)

    if confirm_status:
        query = query.filter(TouchStrategyTask.confirm_status == confirm_status)

    if segment_type:
        query = query.filter(TouchStrategyTask.segment_type == segment_type)

    if touch_channel:
        query = query.filter(TouchStrategyTask.touch_channel == touch_channel)

    if keyword:
        matched_users = db.query(PrivateUser.id).filter(
            PrivateUser.name.like(f"%{keyword}%")
        ).all()
        matched_user_ids = [row.id for row in matched_users]
        if not matched_user_ids:
            return {
                "total": 0,
                "items": [],
            }
        query = query.filter(TouchStrategyTask.user_id.in_(matched_user_ids))

    total = query.count()
    items = query.order_by(
        TouchStrategyTask.id.desc()
    ).offset(
        (page - 1) * page_size
    ).limit(
        page_size
    ).all()

    user_ids = [item.user_id for item in items]
    users = db.query(PrivateUser).filter(
        PrivateUser.id.in_(user_ids)
    ).all() if user_ids else []
    user_name_map = {user.id: user.name for user in users}

    return {
        "total": total,
        "items": [
            build_touch_strategy_out(item, user_name_map.get(item.user_id))
            for item in items
        ],
    }


def build_strategy_candidate_out(
    user: PrivateUser,
    segment: UserSegment | None,
    task: TouchStrategyTask | None,
):
    return {
        "user_id": user.id,
        "user_name": user.name,
        "user_source": user.source,
        "tags": user.tags or [],
        "task_id": task.id if task else None,
        "segment_type": task.segment_type if task else (segment.segment_type if segment else None),
        "touch_channel": task.touch_channel if task else None,
        "strategy_reason": task.strategy_reason if task else None,
        "target_crowd": task.target_crowd if task else None,
        "confirm_status": task.confirm_status if task else None,
        "assignee": task.assignee if task else None,
        "plan_time": task.plan_time if task else None,
    }


def list_touch_strategy_candidates(
    db: Session,
    keyword: str | None = None,
    source: str | None = None,
    confirm_status: str | None = None,
    segment_type: str | None = None,
    touch_channel: str | None = None,
    page: int = 1,
    page_size: int = 10,
):
    user_query = db.query(PrivateUser)

    if keyword:
        user_query = user_query.filter(PrivateUser.name.like(f"%{keyword}%"))

    if source:
        user_query = user_query.filter(PrivateUser.source == source)

    if segment_type:
        user_query = user_query.join(
            UserSegment,
            UserSegment.user_id == PrivateUser.id,
        ).filter(
            UserSegment.segment_type == segment_type
        )

    users = user_query.order_by(PrivateUser.id.desc()).all()
    user_ids = [user.id for user in users]

    segments = db.query(UserSegment).filter(
        UserSegment.user_id.in_(user_ids)
    ).all() if user_ids else []
    segment_map = {segment.user_id: segment for segment in segments}

    tasks = db.query(TouchStrategyTask).filter(
        TouchStrategyTask.user_id.in_(user_ids)
    ).order_by(
        TouchStrategyTask.id.desc()
    ).all() if user_ids else []

    latest_task_map = {}
    for task in tasks:
        if task.user_id not in latest_task_map:
            latest_task_map[task.user_id] = task

    rows = []
    for user in users:
        latest_task = latest_task_map.get(user.id)

        if confirm_status == "__none__" and latest_task:
            continue

        if confirm_status and confirm_status != "__none__":
            if not latest_task or latest_task.confirm_status != confirm_status:
                continue

        if touch_channel:
            if not latest_task or latest_task.touch_channel != touch_channel:
                continue

        rows.append(
            build_strategy_candidate_out(
                user=user,
                segment=segment_map.get(user.id),
                task=latest_task,
            )
        )

    total = len(rows)
    start = (page - 1) * page_size
    end = start + page_size

    return {
        "total": total,
        "items": rows[start:end],
    }


def update_touch_strategy_status(
    db: Session,
    task_id: int,
    confirm_status: str,
    assignee: str | None = None,
):
    allowed = {"待确认", "已确认", "高风险待确认", "驳回"}
    if confirm_status not in allowed:
        raise ValueError("confirm_status 只能是：待确认、已确认、高风险待确认、驳回")

    task = db.query(TouchStrategyTask).filter(
        TouchStrategyTask.id == task_id
    ).first()

    if not task:
        raise ValueError("触达策略任务不存在")

    task.confirm_status = confirm_status
    if assignee is not None:
        task.assignee = assignee

    db.commit()
    db.refresh(task)

    return {
        "task_id": task.id,
        "confirm_status": task.confirm_status,
        "assignee": task.assignee,
    }
