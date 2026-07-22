from datetime import datetime


def create_todo(target_system: str, request_params: dict):
    if not target_system:
        raise ValueError("目标系统不能为空")

    if not request_params.get("content"):
        raise ValueError("待办内容不能为空")

    return {
        "status": "成功",
        "external_task_id": f"mock_{target_system}_{int(datetime.now().timestamp())}",
    }
