from sqlalchemy import BigInteger, Column, DateTime, Integer, JSON, Numeric, String, Text

from app.core.database import Base


class ContentDraft(Base):
    __tablename__ = "content_drafts"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    strategy_task_id = Column(BigInteger, nullable=False)
    content_type = Column(String(16))
    content_text = Column(Text)
    reference_sources = Column(JSON)
    version = Column(Integer, default=1)
    brand_tone_score = Column(Numeric(3, 2), default=0.50)
    created_at = Column(DateTime)
