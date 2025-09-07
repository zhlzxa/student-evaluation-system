from __future__ import annotations

from datetime import datetime
from sqlalchemy import Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class RunLog(Base):
    __tablename__ = "run_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("assessment_runs.id", ondelete="CASCADE"), index=True)
    applicant_id: Mapped[int | None] = mapped_column(ForeignKey("applicants.id", ondelete="CASCADE"), index=True, nullable=True)
    agent_name: Mapped[str] = mapped_column(String(64), index=True)
    phase: Mapped[str] = mapped_column(String(16), index=True)  # request | response | tool
    message: Mapped[str] = mapped_column(Text())
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)

