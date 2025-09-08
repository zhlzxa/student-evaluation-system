from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Optional


class RuleImportFromUrlCreate(BaseModel):
    """Schema for importing rules from URL"""
    url: str = Field(..., description="URL to extract rules from")
    custom_requirements: list[str] | None = Field(None, description="Additional custom requirements")
    name: str | None = Field(None, description="Custom name for the rule set (auto-generated if not provided)")
    temporary: bool = Field(False, description="Whether to create a temporary rule set (for assessment runs)")
    

class RuleImportFromUrlResponse(BaseModel):
    """Response schema for rule import"""
    rule_set_id: int = Field(..., description="ID of the created rule set")
    name: str = Field(..., description="Name of the rule set")
    url: str = Field(..., description="Source URL")
    programme_title: str | None = Field(None, description="Extracted programme title")
    english_level: str | None = Field(None, description="Extracted English level requirement")
    degree_requirement_class: str | None = Field(None, description="Extracted degree requirement class")
    text_length: int = Field(..., description="Length of extracted text")
    checklists: dict[str, list[str]] = Field(..., description="Extracted agent checklists")
    temporary: bool = Field(..., description="Whether this is a temporary rule set")
    extraction_method: str = Field(..., description="Method used for extraction (azure_ai or heuristic)")


class RuleImportPreviewResponse(BaseModel):
    """Preview schema for rule import without creating rule set"""
    url: str = Field(..., description="Source URL")
    programme_title: str | None = Field(None, description="Extracted programme title")
    english_level: str | None = Field(None, description="Extracted English level requirement")
    degree_requirement_class: str | None = Field(None, description="Extracted degree requirement class")
    text_length: int = Field(..., description="Length of extracted text")
    text_preview: str = Field(..., description="First 500 characters of extracted text")
    checklists: dict[str, list[str]] = Field(..., description="Extracted agent checklists")
    extraction_method: str = Field(..., description="Method used for extraction (azure_ai or heuristic)")