from sqlalchemy import Column, BigInteger, String, DateTime, JSON
from app.core.database import Base

class PrivateUser(Base):
    __tablename__ = "private_users"

    id = Column(BigInteger, primary_key=True, autoincrement=True)

    external_user_id = Column(String(64))
    phone = Column(String(20))
    name = Column(String(64))
    source = Column(String(32))

    tags = Column(JSON)

    purchase_status = Column(String(16), default="未购")
    operation_status = Column(String(16), default="正常")

    merged_user_id = Column(BigInteger)

    created_at = Column(DateTime)
    updated_at = Column(DateTime)