from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.operation_task import (
    OperationTaskCreateOut,
    OperationTaskCreateRequest,
    OperationTaskPageOut,
    OperationTaskRetryOut,
    OperationTaskStatusOut,
    OperationTaskStatusRequest,
)
from app.schemas.result import Result
from app.services.operation_task_service import (
    create_operation_task,
    list_operation_tasks,
    retry_operation_task,
    update_operation_task_status,
)

router = APIRouter()


@router.get("/operation-tasks", response_model=Result[OperationTaskPageOut])
def query_tasks(
    assignee: str | None = None,
    response_status: str | None = None,
    status: str | None = None,
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db),
):
    data = list_operation_tasks(
        db=db,
        assignee=assignee,
        response_status=response_status or status,
        page=page,
        page_size=page_size,
    )

    return Result[OperationTaskPageOut].success(data)


@router.post("/operation-tasks/create", response_model=Result[OperationTaskCreateOut])
def create_task(
    request: OperationTaskCreateRequest,
    db: Session = Depends(get_db),
):
    try:
        data = create_operation_task(
            db=db,
            strategy_task_id=request.strategy_task_id,
            content_draft_id=request.content_draft_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return Result[OperationTaskCreateOut].success(data)


@router.put("/operation-tasks/{task_id}/status", response_model=Result[OperationTaskStatusOut])
def update_task_status(
    task_id: int,
    request: OperationTaskStatusRequest,
    db: Session = Depends(get_db),
):
    try:
        data = update_operation_task_status(
            db=db,
            task_id=task_id,
            status=request.status,
            fail_reason=request.fail_reason,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return Result[OperationTaskStatusOut].success(data)


@router.post("/operation-tasks/{task_id}/retry", response_model=Result[OperationTaskRetryOut])
def retry_task(
    task_id: int,
    db: Session = Depends(get_db),
):
    try:
        data = retry_operation_task(
            db=db,
            task_id=task_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return Result[OperationTaskRetryOut].success(data)
