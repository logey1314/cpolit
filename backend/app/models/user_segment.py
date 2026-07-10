from sqlalchemy import BigInteger, Column, DateTime, DECIMAL, Integer, String, Text

from app.core.database import Base


class UserSegment(Base):
    __tablename__ = "user_segments"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False)
    segment_type = Column(String(16), nullable=False)
    segment_basis = Column(Text)
    touch_priority = Column(Integer, default=3)
    applicable_strategy = Column(String(64))
    confidence_score = Column(DECIMAL(3, 2), default=0.50)
    manual_adjusted = Column(Integer, default=0)
    updated_at = Column(DateTime)