from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class AssessmentRunCreate(BaseModel):
    rule_set_id: int | None = None
    rule_set_url: str | None = None
    custom_requirements: list[str] | None = None
    agent_models: dict[str, str] | None = None


class AssessmentRunRead(BaseModel):
    id: int
    name: str | None
    rule_set_id: int | None
    rule_set_url: str | None
    custom_requirements: list[str] | None
    agent_models: dict[str, str] | None
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ApplicantDocumentRead(BaseModel):
    id: int
    rel_path: str
    original_filename: str
    content_type: str | None
    size_bytes: int | None
    text_preview: str | None
    doc_type: str | None

    class Config:
        from_attributes = True


class ApplicantRead(BaseModel):
    id: int
    display_name: str | None
    email: str | None
    folder_name: str
    documents: list[ApplicantDocumentRead] = []

    class Config:
        from_attributes = True


class AssessmentRunDetail(AssessmentRunRead):
    applicants: list[ApplicantRead] = []
