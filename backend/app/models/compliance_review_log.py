from sqlalchemy import BigInteger, Column, DateTime, String, Text

from app.core.database import Base


class ComplianceReviewLog(Base):
    __tablename__ = "compliance_review_logs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    content_draft_id = Column(BigInteger, nullable=False)
    risk_type = Column(String(32))
    risk_detail = Column(Text)
    suggestion = Column(Text)
    review_status = Column(String(16), default="待审核")
    reviewer = Column(String(32))
    reviewed_at = Column(DateTime)
