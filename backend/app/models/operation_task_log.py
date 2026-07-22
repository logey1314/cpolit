from sqlalchemy import BigInteger, Column, DateTime, Integer, JSON, String, Text

from app.core.database import Base


class OperationTaskLog(Base):
    __tablename__ = "operation_task_logs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    strategy_task_id = Column(BigInteger, nullable=False)
    target_system = Column(String(16))
    task_type = Column(String(32))
    request_params = Column(JSON)
    response_status = Column(String(16), default="待执行")
    fail_reason = Column(Text)
    retry_count = Column(Integer, default=0)
    assignee = Column(String(32))
    remind_time = Column(DateTime)
    created_at = Column(DateTime)
