from sqlalchemy import BigInteger, Column, DateTime, String, Text

from app.core.database import Base


class TouchStrategyTask(Base):
    __tablename__ = "touch_strategy_tasks"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False)
    segment_type = Column(String(16))
    touch_channel = Column(String(16))
    strategy_reason = Column(Text)
    target_crowd = Column(String(64))
    assignee = Column(String(32))
    plan_time = Column(DateTime)
    confirm_status = Column(String(16), default="待确认")
    created_at = Column(DateTime)