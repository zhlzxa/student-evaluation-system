from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Integer, String, DateTime, ForeignKey, JSON, Float, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class ApplicantEvaluation(Base):
    __tablename__ = "applicant_evaluations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    applicant_id: Mapped[int] = mapped_column(ForeignKey("applicants.id", ondelete="CASCADE"), index=True)
    agent_name: Mapped[str] = mapped_column(String(64), index=True)
    score: Mapped[float | None] = mapped_column(Float)
    details: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class ApplicantGating(Base):
    __tablename__ = "applicant_gating"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    applicant_id: Mapped[int] = mapped_column(ForeignKey("applicants.id", ondelete="CASCADE"), unique=True)
    decision: Mapped[str] = mapped_column(String(16), index=True)  # ACCEPT, MIDDLE, REJECT
    reasons: Mapped[list[str] | None] = mapped_column(JSON)
    # Optional manual override set by teacher: ACCEPT, MIDDLE, REJECT
    manual_decision: Mapped[str | None] = mapped_column(String(16), index=True, nullable=True)
    manual_set_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class ApplicantRanking(Base):
    __tablename__ = "applicant_ranking"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    applicant_id: Mapped[int] = mapped_column(ForeignKey("applicants.id", ondelete="CASCADE"), unique=True)
    weighted_score: Mapped[float | None] = mapped_column(Float)
    final_rank: Mapped[int | None] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(Text())
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class PairwiseComparison(Base):
    __tablename__ = "pairwise_comparisons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("assessment_runs.id", ondelete="CASCADE"), index=True)
    applicant_a_id: Mapped[int] = mapped_column(ForeignKey("applicants.id", ondelete="CASCADE"))
    applicant_b_id: Mapped[int] = mapped_column(ForeignKey("applicants.id", ondelete="CASCADE"))
    winner: Mapped[str] = mapped_column(String(4))  # 'A', 'B', 'tie'
    reason: Mapped[str | None] = mapped_column(Text())
    pass_index: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
