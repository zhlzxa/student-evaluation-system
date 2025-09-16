from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Integer, String, DateTime, ForeignKey, JSON, Text, BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class AssessmentRun(Base):
    __tablename__ = "assessment_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str | None] = mapped_column(String(256))
    # Owner of this assessment run
    owner_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    rule_set_id: Mapped[int | None] = mapped_column(ForeignKey("admission_rule_sets.id", ondelete="SET NULL"))
    rule_set_url: Mapped[str | None] = mapped_column(String(1000))
    custom_requirements: Mapped[list[str] | None] = mapped_column(JSON)
    # Optional per-run override of agent models, e.g., {"english": "gpt-4.1", "degree": "o3-mini"}
    agent_models: Mapped[dict[str, str] | None] = mapped_column("agent_models_json", JSON)
    status: Mapped[str] = mapped_column(String(32), default="created", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    applicants: Mapped[list["Applicant"]] = relationship(back_populates="run", cascade="all, delete-orphan")


class Applicant(Base):
    __tablename__ = "applicants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("assessment_runs.id", ondelete="CASCADE"), index=True)
    display_name: Mapped[str | None] = mapped_column(String(256))
    email: Mapped[str | None] = mapped_column(String(256))
    folder_name: Mapped[str] = mapped_column(String(512))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    run: Mapped[AssessmentRun] = relationship(back_populates="applicants")
    documents: Mapped[list["ApplicantDocument"]] = relationship(back_populates="applicant", cascade="all, delete-orphan")


class ApplicantDocument(Base):
    __tablename__ = "applicant_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    applicant_id: Mapped[int] = mapped_column(ForeignKey("applicants.id", ondelete="CASCADE"), index=True)
    rel_path: Mapped[str] = mapped_column(String(1024))
    original_filename: Mapped[str] = mapped_column(String(512))
    content_type: Mapped[str | None] = mapped_column(String(128))
    size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    text_preview: Mapped[str | None] = mapped_column(Text())
    table_data: Mapped[list[Any] | None] = mapped_column(JSON)
    doc_type: Mapped[str | None] = mapped_column(String(64))

    applicant: Mapped[Applicant] = relationship(back_populates="documents")
