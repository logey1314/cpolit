from sqlalchemy import BigInteger, Column, DateTime, JSON, String, Text

from app.core.database import Base


class CommunityInteraction(Base):
    __tablename__ = "community_interactions"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    community_id = Column(String(32), nullable=False)
    user_id = Column(BigInteger, nullable=False)

    message_content = Column(Text)
    message_type = Column(String(16), default="文本")

    keywords = Column(JSON)
    intent_label = Column(String(16), default="无关")
    sentiment = Column(String(16), default="中性")

    interaction_time = Column(DateTime)