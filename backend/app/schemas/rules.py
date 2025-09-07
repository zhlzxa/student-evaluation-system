from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class DegreeEquivalencySourceBase(BaseModel):
    uk_class: str = Field(description="UK classification: FIRST, UPPER_SECOND, LOWER_SECOND")
    source_url: str
    notes: str | None = None


class DegreeEquivalencySourceCreate(DegreeEquivalencySourceBase):
    pass


class DegreeEquivalencySourceRead(DegreeEquivalencySourceBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class CountryDegreeEquivalencyBase(BaseModel):
    country_code: str
    country_name: str
    uk_class: str
    requirement: dict[str, Any] | None = None
    source_url: str | None = None
    last_verified_at: datetime | None = None


class CountryDegreeEquivalencyCreate(CountryDegreeEquivalencyBase):
    pass


class CountryDegreeEquivalencyRead(CountryDegreeEquivalencyBase):
    id: int

    class Config:
        from_attributes = True


class EnglishRuleBase(BaseModel):
    nationality_exempt_countries: list[str] | None = None
    degree_obtained_exempt_countries: list[str] | None = None
    levels: dict[str, Any] | None = None
    source_url: str | None = None
    last_verified_at: datetime | None = None


class EnglishRuleCreate(EnglishRuleBase):
    pass


class EnglishRuleRead(EnglishRuleBase):
    id: int

    class Config:
        from_attributes = True


class AdmissionRuleSetBase(BaseModel):
    name: str
    description: str | None = None
    metadata_json: dict[str, Any] | None = None
    english_rule_id: int | None = None


class AdmissionRuleSetCreate(AdmissionRuleSetBase):
    pass


class AdmissionRuleSetRead(AdmissionRuleSetBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

