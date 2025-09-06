from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    String,
    Integer,
    DateTime,
    JSON,
    ForeignKey,
    UniqueConstraint,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class AdmissionRuleSet(Base):
    __tablename__ = "admission_rule_sets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text())
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    english_rule_id: Mapped[int | None] = mapped_column(ForeignKey("english_rules.id", ondelete="SET NULL"))
    english_rule: Mapped["EnglishRule | None"] = relationship(back_populates="rule_sets")

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<AdmissionRuleSet id={self.id} name={self.name}>"


class DegreeEquivalencySource(Base):
    __tablename__ = "degree_equivalency_sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # FIRST, UPPER_SECOND (2:1), LOWER_SECOND (2:2)
    uk_class: Mapped[str] = mapped_column(String(32), index=True)
    source_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text())
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (UniqueConstraint("uk_class", name="uq_degree_equiv_source_uk_class"),)


class CountryDegreeEquivalency(Base):
    __tablename__ = "country_degree_equivalencies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    country_code: Mapped[str] = mapped_column(String(3), index=True)
    country_name: Mapped[str] = mapped_column(String(128), index=True)
    # FIRST, UPPER_SECOND (2:1), LOWER_SECOND (2:2)
    uk_class: Mapped[str] = mapped_column(String(32), index=True)
    # Store raw requirement structure as JSON (e.g., GPA scales, percentages, narrative text)
    requirement: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    source_url: Mapped[str | None] = mapped_column(String(1000))
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime)

    __table_args__ = (
        UniqueConstraint("country_code", "uk_class", name="uq_country_uk_class"),
    )


class SpecialInstitutionRule(Base):
    __tablename__ = "special_institution_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    country_code: Mapped[str] = mapped_column(String(3), index=True)
    institution_name: Mapped[str] = mapped_column(String(512), index=True)
    category: Mapped[str] = mapped_column(String(256), index=True)
    thresholds: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    notes: Mapped[str | None] = mapped_column(Text())

    __table_args__ = (
        UniqueConstraint("country_code", "institution_name", name="uq_country_institution"),
    )


class EnglishRule(Base):
    __tablename__ = "english_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nationality_exempt_countries: Mapped[list[str] | None] = mapped_column(JSON)
    degree_obtained_exempt_countries: Mapped[list[str] | None] = mapped_column(JSON)
    levels: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    source_url: Mapped[str | None] = mapped_column(String(1000))
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime)

    rule_sets: Mapped[list[AdmissionRuleSet]] = relationship(back_populates="english_rule")
