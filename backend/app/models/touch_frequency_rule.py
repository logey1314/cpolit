from sqlalchemy import BigInteger, Column, Integer, String

from app.core.database import Base


class TouchFrequencyRule(Base):
    __tablename__ = "touch_frequency_rules"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    dimension = Column(String(16), nullable=False)
    dimension_id = Column(String(64))
    channel = Column(String(16), nullable=False)
    max_count = Column(Integer, default=2)
    window_hours = Column(Integer, default=24)
    rule_description = Column(String(128))
    is_active = Column(Integer, default=1)