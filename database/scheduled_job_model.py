"""
Market Intelligence Scout — Scheduled Jobs DB Model
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from .session import Base


class ScheduledJob(Base):
    __tablename__ = "scheduled_jobs"

    id           = Column(Integer, primary_key=True, index=True)
    company_name = Column(String, nullable=False)
    email        = Column(String, nullable=False)
    scheduled_at = Column(DateTime(timezone=True), nullable=False)
    status       = Column(String, default="pending")   # pending|running|done|failed
    report_id    = Column(Integer, ForeignKey("reports.id", ondelete="SET NULL"), nullable=True)
    error_msg    = Column(Text, nullable=True)
    created_at   = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    report = relationship("Report", foreign_keys=[report_id])
