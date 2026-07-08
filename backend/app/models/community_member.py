from sqlalchemy import BigInteger, Column, DateTime, JSON, String

from app.core.database import Base


class CommunityMember(Base):
    __tablename__ = "community_members"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    community_id = Column(String(32), nullable=False)
    community_name = Column(String(64))
    user_id = Column(BigInteger, nullable=False)

    join_source = Column(String(32))
    role = Column(String(16), default="普通成员")
    tags = Column(JSON)

    last_interaction_at = Column(DateTime)
    created_at = Column(DateTime)