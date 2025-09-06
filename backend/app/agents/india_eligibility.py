"""
India applicant eligibility evaluation system.
Implements UCL's India-specific admission requirements with deterministic rules + LLM fallback.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Optional, Dict, Set, Any
from pathlib import Path
from difflib import SequenceMatcher

# Get data directory path
DATA_DIR = Path(__file__).parent.parent.parent / "data"

# Official UCL thresholds for India (2024/25 requirements)
INDIA_THRESHOLDS = {
    "category1": {
        "first": {"10": 8.0, "8": 6.5, "7": 6.0, "6": 4.5, "4": 3.3, "percent": 65},
        "2:1":  {"10": 7.5, "8": 6.0, "7": 5.5, "6": 4.0, "4": 3.0, "percent": 60},
        "2:2":  {"10": 6.5, "8": 5.5, "7": 5.0, "6": 3.5, "4": 2.7, "percent": 55},
    },
    "category2": {
        "first": {"10": 8.5, "8": 7.0, "7": 6.5, "6": 5.0, "4": 3.6, "percent": 70},
        "2:1":  {"10": 8.0, "8": 6.5, "7": 6.0, "6": 4.5, "4": 3.3, "percent": 65},
        "2:2":  {"10": 7.0, "8": 6.0, "7": 5.5, "6": 4.0, "4": 3.0, "percent": 60},
    },
}

@dataclass
class IndiaCredential:
    """India applicant credential data."""
    country: str                 # "India"
    degree_years: int            # 3..5
    awarding_body_recognised: bool
    institution_raw: str
    mark_value: float            # e.g. 7.6 or 68
    mark_scale_denominator: Optional[int]  # 10/8/7/6/4; None for percentage
    target_band: str             # "first" / "2:1" / "2:2"

class IndiaEligibilityEvaluator:
    """Evaluates India applicant eligibility based on UCL rules."""
    
    def __init__(self):
        self.institutions_data = self._load_institutions_data()
        self.category1_sets = self._build_category1_sets()
        self.aliases = self.institutions_data.get("aliases", {})
    
    def _load_institutions_data(self) -> Dict[str, Any]:
        """Load India institutions classification data."""
        institutions_path = DATA_DIR / "india_institutions.json"
        with open(institutions_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _build_category1_sets(self) -> Dict[str, Set[str]]:
        """Build sets for Category 1 institution classification."""
        sets = {}
        category1_data = self.institutions_data.get("category1_sets", {})
        
        for key, institution_list in category1_data.items():
            # Convert to lowercase set for case-insensitive matching
            sets[key] = {inst.lower().strip() for inst in institution_list}
        
        return sets
    
    def _normalize_institution_name(self, raw_name: str) -> tuple[str, float]:
        """
        Normalize institution name and return confidence score.
        Returns: (normalized_name, confidence_score)
        """
        if not raw_name:
            return raw_name, 0.0
        
        name_lower = raw_name.lower().strip()
        
        # Check aliases first
        for alias, canonical in self.aliases.items():
            if name_lower == alias.lower().strip():
                return canonical, 0.95
        
        # Check all Category 1 institutions for exact match
        for set_name, institution_set in self.category1_sets.items():
            if name_lower in institution_set:
                # Find the original case version
                for original in self.institutions_data["category1_sets"][set_name]:
                    if original.lower().strip() == name_lower:
                        return original, 0.9
        
        # Fuzzy matching
        best_match = None
        best_score = 0.0
        
        # Check against all known institutions
        all_institutions = set()
        for institution_set in self.category1_sets.values():
            all_institutions.update(institution_set)
        
        for known_name in all_institutions:
            score = SequenceMatcher(None, name_lower, known_name).ratio()
            if score > best_score and score >= 0.8:  # 80% similarity threshold
                best_score = score
                best_match = known_name
        
        if best_match:
            # Find original case version
            for set_name, institution_set in self.category1_sets.items():
                if best_match in institution_set:
                    for original in self.institutions_data["category1_sets"][set_name]:
                        if original.lower().strip() == best_match:
                            return original, best_score * 0.8  # Reduce confidence for fuzzy match
        
        return raw_name, 0.3  # Low confidence for unrecognized institution
    
    def classify_category(self, institution_canonical: str) -> str:
        """
        Classify institution into Category 1 or Category 2.
        """
        name_lower = institution_canonical.lower().strip()
        
        # Check if institution is in any Category 1 set
        for set_name, institution_set in self.category1_sets.items():
            if name_lower in institution_set:
                return "category1"
        
        return "category2"
    
    def to_percent(self, value: float, denom: Optional[int]) -> float:
        """Convert CGPA to percentage if needed."""
        if denom is None:
            return value  # Already percentage
        return (value / denom) * 100.0
    
    def meets_threshold(self, value: float, denom: Optional[int], band: str, category: str) -> tuple[bool, float]:
        """
        Check if mark meets threshold.
        Returns: (meets_requirement, threshold_used)
        """
        thresholds = INDIA_THRESHOLDS[category][band]
        
        # Try to find exact scale match first
        if denom is not None:
            key = str(denom)
            if key in thresholds:
                threshold = thresholds[key]
                return value >= threshold, threshold
        
        # Fall back to percentage comparison
        percent_value = self.to_percent(value, denom)
        percent_threshold = thresholds["percent"]
        return percent_value >= percent_threshold, percent_threshold
    
    def evaluate(self, credential: IndiaCredential) -> Dict[str, Any]:
        """
        Evaluate India applicant eligibility.
        
        Returns:
            Dictionary with evaluation results including:
            - eligible: bool
            - reason: str
            - threshold_used: float
            - category: str
            - institution_canonical: str
            - confidence: float
        """
        # Basic form validation
        if credential.country.lower() not in {"india", "in", "भारत"}:
            return {
                "eligible": False,
                "reason": "not_india",
                "confidence": 1.0
            }
        
        if not (3 <= credential.degree_years <= 5):
            return {
                "eligible": False,
                "reason": "degree_years_not_3to5",
                "confidence": 1.0
            }
        
        if not credential.awarding_body_recognised:
            return {
                "eligible": False,
                "reason": "awarding_body_not_recognised",
                "confidence": 1.0
            }
        
        # Institution normalization and classification
        institution_canonical, name_confidence = self._normalize_institution_name(
            credential.institution_raw
        )
        category = self.classify_category(institution_canonical)
        
        # Threshold comparison
        meets_req, threshold_used = self.meets_threshold(
            credential.mark_value,
            credential.mark_scale_denominator, 
            credential.target_band,
            category
        )
        
        # Calculate overall confidence
        if category == "category1" and name_confidence > 0.8:
            overall_confidence = name_confidence
        elif category == "category1":
            overall_confidence = name_confidence * 0.9
        else:
            overall_confidence = max(0.6, name_confidence)  # Category 2 has baseline confidence
        
        return {
            "eligible": meets_req,
            "reason": "meets_threshold" if meets_req else "below_threshold",
            "threshold_used": threshold_used,
            "category": category,
            "institution_canonical": institution_canonical,
            "institution_raw": credential.institution_raw,
            "mark_value": credential.mark_value,
            "mark_scale": credential.mark_scale_denominator or "percent",
            "target_band": credential.target_band,
            "confidence": overall_confidence,
            "thresholds_reference": INDIA_THRESHOLDS[category][credential.target_band],
            "note": "Meeting minimum requirements does not guarantee admission. Individual departments may require higher grades."
        }

# Convenience function
def evaluate_india_applicant(
    institution: str,
    mark_value: float,
    target_band: str,
    mark_scale_denominator: Optional[int] = None,
    degree_years: int = 4,
    awarding_body_recognised: bool = True
) -> Dict[str, Any]:
    """Convenience function to evaluate an India applicant."""
    evaluator = IndiaEligibilityEvaluator()
    credential = IndiaCredential(
        country="India",
        degree_years=degree_years,
        awarding_body_recognised=awarding_body_recognised,
        institution_raw=institution,
        mark_value=mark_value,
        mark_scale_denominator=mark_scale_denominator,
        target_band=target_band
    )
    return evaluator.evaluate(credential)