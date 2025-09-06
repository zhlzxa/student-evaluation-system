"""
China applicant eligibility evaluation system.
Implements UCL's China-specific admission requirements with deterministic rules + LLM fallback.
"""
from __future__ import annotations

import json
import yaml
import os
from dataclasses import dataclass
from typing import Optional, Dict, List, Any
from pathlib import Path
from difflib import SequenceMatcher

# Get data directory path
DATA_DIR = Path(__file__).parent.parent.parent / "data"

@dataclass 
class ChinaCredential:
    """China applicant credential data."""
    country: str                    # "China"
    degree_years: int              # Should be 4 for bachelor
    moe_recognized: bool           # Ministry of Education recognized
    institution_raw: str           # Raw institution name as provided
    major_raw: str                 # Raw major/program name
    mark_value: float              # Weighted average mark (e.g. 87.5)
    target_band: str               # "first" / "2:1" / "2:2"

class ChinaEligibilityEvaluator:
    """Evaluates China applicant eligibility based on UCL rules."""
    
    def __init__(self):
        self.universities = self._load_universities()
        self.rules = self._load_rules()
        self.institution_lookup = self._build_institution_lookup()
    
    def _load_universities(self) -> List[Dict[str, Any]]:
        """Load China UCL universities configuration."""
        config_path = DATA_DIR / "china_ucl_universities.json"
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _load_rules(self) -> Dict[str, Any]:
        """Load China program rules configuration."""
        rules_path = DATA_DIR / "china_program_rules.yaml"
        with open(rules_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def _build_institution_lookup(self) -> Dict[str, Dict[str, Any]]:
        """Build lookup table for institution name matching."""
        lookup = {}
        
        for uni in self.universities:
            canonical = uni["canonical"].lower().strip()
            
            # Add canonical name
            lookup[canonical] = uni
            
            # Add all aliases
            for alias in uni.get("aliases", []):
                alias_key = alias.lower().strip()
                if alias_key not in lookup:  # Avoid conflicts
                    lookup[alias_key] = uni
        
        return lookup
    
    def _normalize_institution_name(self, raw_name: str) -> Optional[Dict[str, Any]]:
        """
        Normalize institution name to canonical form.
        Returns: University dict if found, None otherwise.
        """
        if not raw_name:
            return None
        
        name_lower = raw_name.lower().strip()
        
        # Exact match first
        if name_lower in self.institution_lookup:
            return self.institution_lookup[name_lower]
        
        # Fuzzy matching for close matches
        best_match = None
        best_score = 0.0
        
        for known_name, uni_info in self.institution_lookup.items():
            score = SequenceMatcher(None, name_lower, known_name).ratio()
            if score > best_score and score >= 0.8:  # 80% similarity threshold
                best_score = score
                best_match = uni_info
        
        return best_match
    
    def _is_cs_tech_major(self, major: str) -> bool:
        """Check if major is Computer Science and Technology related."""
        if not major:
            return False
        
        major_lower = major.lower().strip()
        cs_majors = [m.lower() for m in self.rules.get("cs_tech_majors", [])]
        
        # Exact match
        if major_lower in cs_majors:
            return True
        
        # Partial match for flexibility
        cs_keywords = ["computer science", "计算机科学", "software engineering", "软件工程"]
        for keyword in cs_keywords:
            if keyword in major_lower:
                return True
        
        return False
    
    def _determine_threshold_category(self, university_info: Dict[str, Any], major: str) -> str:
        """Determine which threshold category applies."""
        flag = university_info.get("flag")
        
        if flag == "star_redirect":
            return "star_redirect"
        elif flag == "double_star":
            if self._is_cs_tech_major(major):
                return "in_ucl_list_double_star_cs"
            else:
                return "in_ucl_list_double_star_non_cs"
        else:
            return "in_ucl_list_default"
    
    def _get_threshold(self, category: str, target_band: str) -> Optional[float]:
        """Get threshold value for given category and band."""
        thresholds = self.rules.get("thresholds", {})
        
        if category == "star_redirect":
            # Should redirect to Hong Kong rules - not handled here
            return None
        elif category == "in_ucl_list_default":
            return thresholds.get("in_ucl_list_default", {}).get(target_band)
        elif category == "in_ucl_list_double_star_cs":
            return thresholds.get("in_ucl_list_double_star", {}).get("cs_tech", {}).get(target_band)
        elif category == "in_ucl_list_double_star_non_cs":
            return thresholds.get("in_ucl_list_double_star", {}).get("non_cs_tech", {}).get(target_band)
        elif category == "outside_ucl_list":
            return thresholds.get("outside_ucl_list", {}).get(target_band)
        
        return None
    
    def evaluate(self, credential: ChinaCredential) -> Dict[str, Any]:
        """
        Evaluate China applicant eligibility.
        
        Returns:
            Dictionary with evaluation results including:
            - eligible: bool
            - reason: str
            - threshold_used: float
            - category: str
            - institution_canonical: str
            - confidence: float
        """
        # Basic validation
        if credential.country.lower() not in {"china", "cn", "中国"}:
            return {
                "eligible": False,
                "reason": "not_china",
                "confidence": 1.0
            }
        
        if credential.degree_years != 4:
            return {
                "eligible": False, 
                "reason": "not_4_year_bachelor",
                "confidence": 1.0
            }
        
        if not credential.moe_recognized:
            return {
                "eligible": False,
                "reason": "not_moe_recognized", 
                "confidence": 1.0
            }
        
        # Institution normalization
        university_info = self._normalize_institution_name(credential.institution_raw)
        
        if university_info is None:
            # Not in UCL list - use general MOE requirements
            category = "outside_ucl_list"
            institution_canonical = credential.institution_raw  # Keep original
            confidence = 0.5  # Lower confidence for unlisted institutions
        else:
            # Check for star redirect
            if university_info.get("flag") == "star_redirect":
                return {
                    "eligible": None,  # Need to redirect
                    "reason": "redirect_to_hong_kong_rules",
                    "institution_canonical": university_info["canonical"],
                    "confidence": 1.0
                }
            
            category = self._determine_threshold_category(university_info, credential.major_raw)
            institution_canonical = university_info["canonical"]
            confidence = 0.9  # High confidence for listed institutions
        
        # Get applicable threshold
        threshold = self._get_threshold(category, credential.target_band)
        
        if threshold is None:
            return {
                "eligible": False,
                "reason": "no_threshold_found",
                "category": category,
                "confidence": 0.3
            }
        
        # Compare with threshold
        meets_requirement = credential.mark_value >= threshold
        
        return {
            "eligible": meets_requirement,
            "reason": "meets_threshold" if meets_requirement else "below_threshold",
            "threshold_used": threshold,
            "category": category, 
            "institution_canonical": institution_canonical,
            "institution_raw": credential.institution_raw,
            "major": credential.major_raw,
            "mark_value": credential.mark_value,
            "target_band": credential.target_band,
            "confidence": confidence,
            "note": "Meeting minimum requirements does not guarantee admission"
        }

# Convenience function
def evaluate_china_applicant(
    institution: str,
    major: str, 
    mark: float,
    target_band: str,
    degree_years: int = 4,
    moe_recognized: bool = True
) -> Dict[str, Any]:
    """Convenience function to evaluate a China applicant."""
    evaluator = ChinaEligibilityEvaluator()
    credential = ChinaCredential(
        country="China",
        degree_years=degree_years,
        moe_recognized=moe_recognized,
        institution_raw=institution,
        major_raw=major,
        mark_value=mark,
        target_band=target_band
    )
    return evaluator.evaluate(credential)