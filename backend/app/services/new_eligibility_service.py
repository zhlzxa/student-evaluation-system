"""
New eligibility evaluation service that integrates with the database.
Provides a unified interface for China and India applicant evaluation.
"""
from __future__ import annotations

import json
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from datetime import datetime

from app.models.rules import AdmissionRuleSet, CountryDegreeEquivalency
from app.agents.china_eligibility import evaluate_china_applicant
from app.agents.india_eligibility import evaluate_india_applicant

class NewEligibilityService:
    """Service for evaluating applicant eligibility using the new rule system."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def evaluate_applicant(
        self,
        country_code: str,
        institution_name: str,
        major_field: str,
        degree_years: int,
        mark_value: float,
        mark_scale: Optional[str],  # "10", "8", "7", "6", "4", "percent"
        target_uk_class: str,      # "first", "2:1", "2:2"
        moe_recognized: bool = True
    ) -> Dict[str, Any]:
        """
        Evaluate applicant eligibility using country-specific rules.
        
        Args:
            country_code: ISO country code (e.g., "CHN", "IND")
            institution_name: Name of the institution
            major_field: Academic major/field of study
            degree_years: Number of years for the degree
            mark_value: Numerical grade/mark
            mark_scale: Grading scale ("10", "8", etc. for CGPA, "percent" for percentage)
            target_uk_class: Target UK degree classification
            moe_recognized: Whether the institution is government recognized
            
        Returns:
            Dictionary with evaluation results and database logging info
        """
        
        # Normalize inputs
        country_code = country_code.upper().strip()
        target_uk_class_normalized = self._normalize_uk_class(target_uk_class)
        mark_scale_denominator = None if mark_scale == "percent" else (int(mark_scale) if mark_scale else None)
        
        # Route to appropriate evaluator
        if country_code == "CHN":
            result = evaluate_china_applicant(
                institution=institution_name,
                major=major_field,
                mark=mark_value,
                target_band=target_uk_class_normalized,
                degree_years=degree_years,
                moe_recognized=moe_recognized
            )
        elif country_code == "IND":
            result = evaluate_india_applicant(
                institution=institution_name,
                mark_value=mark_value,
                target_band=target_uk_class_normalized,
                mark_scale_denominator=mark_scale_denominator,
                degree_years=degree_years,
                awarding_body_recognised=moe_recognized
            )
        else:
            # Fall back to legacy system for other countries
            result = self._fallback_evaluation(
                country_code, institution_name, mark_value, target_uk_class_normalized
            )
        
        # Log evaluation to database
        self._log_evaluation_to_database(
            country_code=country_code,
            institution_name=institution_name,
            major_field=major_field,
            evaluation_result=result
        )
        
        # Add metadata
        result["evaluation_timestamp"] = datetime.utcnow().isoformat()
        result["evaluation_system"] = "new_rule_system_v2"
        result["country_code"] = country_code
        
        return result
    
    def _normalize_uk_class(self, target_class: str) -> str:
        """Normalize UK degree class specification."""
        target_lower = target_class.lower().strip()
        if target_lower in ["first", "1st", "first_class"]:
            return "first"
        elif target_lower in ["2:1", "21", "upper_second", "second_upper"]:
            return "2:1"
        elif target_lower in ["2:2", "22", "lower_second", "second_lower"]:
            return "2:2"
        return target_lower
    
    def _fallback_evaluation(
        self,
        country_code: str,
        institution_name: str, 
        mark_value: float,
        target_uk_class: str
    ) -> Dict[str, Any]:
        """Fallback to legacy database-based evaluation for other countries."""
        
        # Look up country degree equivalency
        equivalency = self.db.query(CountryDegreeEquivalency).filter_by(
            country_code=country_code,
            uk_class=target_uk_class.upper().replace(":", "")
        ).first()
        
        if not equivalency:
            return {
                "eligible": False,
                "reason": "no_rules_found",
                "country_code": country_code,
                "confidence": 0.1,
                "note": "No specific rules found for this country"
            }
        
        # Simple threshold-based evaluation (this would need more sophisticated logic)
        requirement = equivalency.requirement or {}
        threshold = None
        
        if "min_percentage" in requirement:
            threshold = requirement["min_percentage"]
        
        if threshold is None:
            return {
                "eligible": False,
                "reason": "no_threshold_found",
                "confidence": 0.2
            }
        
        eligible = mark_value >= threshold
        
        return {
            "eligible": eligible,
            "reason": "meets_threshold" if eligible else "below_threshold", 
            "threshold_used": threshold,
            "category": "legacy_evaluation",
            "institution_canonical": institution_name,
            "confidence": 0.7,
            "note": "Evaluated using legacy database rules"
        }
    
    def _log_evaluation_to_database(
        self,
        country_code: str,
        institution_name: str,
        major_field: str,
        evaluation_result: Dict[str, Any]
    ) -> None:
        """Log evaluation results to database for audit and analysis."""
        
        # Find or create admission rule set for tracking
        rule_set_name = f"Auto_{country_code}_Evaluation_{datetime.utcnow().strftime('%Y%m')}"
        
        rule_set = self.db.query(AdmissionRuleSet).filter_by(name=rule_set_name).first()
        if not rule_set:
            rule_set = AdmissionRuleSet(
                name=rule_set_name,
                description=f"Automated evaluation logs for {country_code} applicants",
                metadata_json={
                    "country_code": country_code,
                    "evaluation_system": "new_rule_system_v2",
                    "created_month": datetime.utcnow().strftime('%Y-%m')
                }
            )
            self.db.add(rule_set)
            self.db.flush()  # Get ID
        
        # Update metadata with evaluation statistics
        if not rule_set.metadata_json:
            rule_set.metadata_json = {}
        
        metadata = rule_set.metadata_json
        metadata.setdefault("evaluation_count", 0)
        metadata["evaluation_count"] += 1
        metadata.setdefault("institutions_evaluated", set())
        metadata["institutions_evaluated"].add(institution_name)
        metadata["last_evaluation"] = datetime.utcnow().isoformat()
        
        # Convert set to list for JSON serialization
        if isinstance(metadata.get("institutions_evaluated"), set):
            metadata["institutions_evaluated"] = list(metadata["institutions_evaluated"])
        
        rule_set.metadata_json = metadata
        self.db.add(rule_set)
        
        try:
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            # Log error but don't fail the evaluation
            print(f"Warning: Failed to log evaluation to database: {e}")

def evaluate_with_database(
    db: Session,
    country_code: str,
    institution_name: str,
    major_field: str = "General",
    degree_years: int = 4,
    mark_value: float = 0.0,
    mark_scale: str = "percent",
    target_uk_class: str = "2:1",
    moe_recognized: bool = True
) -> Dict[str, Any]:
    """
    Convenience function for evaluating applicant eligibility with database integration.
    """
    service = NewEligibilityService(db)
    return service.evaluate_applicant(
        country_code=country_code,
        institution_name=institution_name,
        major_field=major_field,
        degree_years=degree_years,
        mark_value=mark_value,
        mark_scale=mark_scale,
        target_uk_class=target_uk_class,
        moe_recognized=moe_recognized
    )