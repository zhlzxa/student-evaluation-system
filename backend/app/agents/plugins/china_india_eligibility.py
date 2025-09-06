"""
Semantic Kernel plugin for China and India applicant eligibility evaluation.
Provides LLM-callable functions for the new rule system.
"""
from __future__ import annotations

import json
from typing import Annotated

from semantic_kernel.functions import kernel_function

from app.agents.china_eligibility import evaluate_china_applicant
from app.agents.india_eligibility import evaluate_india_applicant


class ChinaIndiaEligibilityPlugin:
    """
    Plugin for evaluating China and India applicant eligibility using the new rule system.
    
    This plugin provides LLM-accessible functions for evaluating applicants from China and India
    based on UCL's official admission requirements with deterministic rules.
    """

    @kernel_function(description="Evaluate a Chinese applicant's eligibility for UCL admission based on official UCL requirements.")
    def evaluate_china_applicant(
        self,
        institution_name: Annotated[str, "Name of the Chinese university (e.g., 'Tsinghua University', 'THU', '清华大学')"],
        major_field: Annotated[str, "Academic major/field of study (e.g., 'Computer Science and Technology', 'Mechanical Engineering')"],
        weighted_average_mark: Annotated[float, "Weighted average mark as percentage (e.g., 87.5)"],
        target_uk_class: Annotated[str, "Target UK degree class: 'first', '2:1', or '2:2'"],
        degree_years: Annotated[int, "Number of years for the degree (should be 4 for Chinese bachelor)"] = 4,
        moe_recognized: Annotated[bool, "Whether institution is recognized by Chinese Ministry of Education"] = True
    ) -> Annotated[str, "JSON string with evaluation result including eligibility, threshold, category, and confidence"]:
        """
        Evaluate Chinese applicant eligibility using UCL's China-specific rules.
        
        Handles:
        - UCL approved university list matching (including aliases)
        - Double star (**) rules for specific universities  
        - Computer Science major special treatment
        - Hong Kong redirect institutions (UIC, CUHKSZ)
        - Fallback to general MOE requirements
        """
        try:
            result = evaluate_china_applicant(
                institution=institution_name,
                major=major_field,
                mark=weighted_average_mark,
                target_band=target_uk_class,
                degree_years=degree_years,
                moe_recognized=moe_recognized
            )
            return json.dumps(result, ensure_ascii=False, indent=2)
        except Exception as e:
            return json.dumps({
                "eligible": False,
                "reason": "evaluation_error",
                "error": str(e),
                "confidence": 0.0
            })

    @kernel_function(description="Evaluate an Indian applicant's eligibility for UCL admission based on official UCL requirements.")
    def evaluate_india_applicant(
        self,
        institution_name: Annotated[str, "Name of the Indian institution (e.g., 'IIT Bombay', 'IITB', 'Indian Institute of Technology Bombay')"],
        mark_value: Annotated[float, "Grade/mark value (e.g., 7.8 for CGPA or 68.0 for percentage)"],
        mark_scale: Annotated[str, "Grading scale: '10', '8', '7', '6', '4' for CGPA or 'percent' for percentage"],
        target_uk_class: Annotated[str, "Target UK degree class: 'first', '2:1', or '2:2'"],
        degree_years: Annotated[int, "Number of years for the degree (3-5 for Indian bachelor)"] = 4,
        govt_recognized: Annotated[bool, "Whether institution is recognized by Government of India"] = True
    ) -> Annotated[str, "JSON string with evaluation result including eligibility, category, threshold, and confidence"]:
        """
        Evaluate Indian applicant eligibility using UCL's India-specific Category 1/2 system.
        
        Handles:
        - Category 1: INI, IoE, NIRF Top 100, NLUs, specified autonomous institutions
        - Category 2: All other recognized institutions  
        - Multi-scale CGPA support (10/8/7/6/4 point scales)
        - Percentage grade support
        - Institution name normalization and alias matching
        """
        try:
            # Convert mark_scale parameter
            mark_scale_denominator = None if mark_scale == "percent" else int(mark_scale)
            
            result = evaluate_india_applicant(
                institution=institution_name,
                mark_value=mark_value,
                target_band=target_uk_class,
                mark_scale_denominator=mark_scale_denominator,
                degree_years=degree_years,
                awarding_body_recognised=govt_recognized
            )
            return json.dumps(result, ensure_ascii=False, indent=2)
        except Exception as e:
            return json.dumps({
                "eligible": False,
                "reason": "evaluation_error", 
                "error": str(e),
                "confidence": 0.0
            })

    @kernel_function(description="Check if a country is supported by the new China/India eligibility system.")
    def is_country_supported(
        self,
        country: Annotated[str, "Country name or ISO code (e.g., 'China', 'CHN', 'India', 'IND')"]
    ) -> Annotated[str, "JSON string indicating if country is supported and which function to use"]:
        """
        Check if a country is supported by the new eligibility system.
        
        Returns guidance on which evaluation function to use for supported countries.
        """
        country_lower = country.lower().strip()
        
        if country_lower in ["china", "chn", "中国"]:
            return json.dumps({
                "supported": True,
                "country": "China",
                "country_code": "CHN", 
                "function_to_use": "evaluate_china_applicant",
                "note": "Use evaluate_china_applicant for Chinese applicants"
            })
        elif country_lower in ["india", "ind", "भारत"]:
            return json.dumps({
                "supported": True,
                "country": "India", 
                "country_code": "IND",
                "function_to_use": "evaluate_india_applicant",
                "note": "Use evaluate_india_applicant for Indian applicants"
            })
        else:
            return json.dumps({
                "supported": False,
                "country": country,
                "note": "Use general degree policy plugin for other countries"
            })

    @kernel_function(description="Get detailed information about UCL's China university list and special rules.")
    def get_china_university_info(
        self,
        institution_name: Annotated[str, "Chinese university name to look up"]
    ) -> Annotated[str, "JSON string with university information including UCL list status and special flags"]:
        """
        Get detailed information about a Chinese university's status in UCL's approved list.
        
        Useful for understanding why certain thresholds apply to specific institutions.
        """
        try:
            # Use the China evaluator to get institution info
            from app.agents.china_eligibility import ChinaEligibilityEvaluator
            
            evaluator = ChinaEligibilityEvaluator()
            university_info = evaluator._normalize_institution_name(institution_name)
            
            if university_info is None:
                return json.dumps({
                    "found": False,
                    "institution_name": institution_name,
                    "ucl_list_status": "not_in_list",
                    "note": "University not found in UCL approved list - would use general MOE requirements"
                })
            
            flag = university_info.get("flag")
            status_info = {
                "found": True,
                "canonical_name": university_info["canonical"],
                "aliases": university_info.get("aliases", []),
                "ucl_list_status": "approved",
                "special_flag": flag,
                "thresholds": {}
            }
            
            if flag == "double_star":
                status_info["thresholds"] = {
                    "cs_majors": "2:1=85%, 2:2=80%",
                    "non_cs_majors": "2:1=90%, 2:2=85%",
                    "note": "Different thresholds for Computer Science vs other majors"
                }
            elif flag == "star_redirect":
                status_info["thresholds"] = {
                    "note": "Redirects to Hong Kong (SAR) requirements"
                }
            else:
                status_info["thresholds"] = {
                    "standard": "2:1=85%, 2:2=80%",
                    "note": "Standard UCL list thresholds"
                }
            
            return json.dumps(status_info, ensure_ascii=False, indent=2)
            
        except Exception as e:
            return json.dumps({
                "found": False,
                "error": str(e),
                "institution_name": institution_name
            })

    @kernel_function(description="Get detailed information about Indian institution categories and requirements.")
    def get_india_institution_info(
        self,
        institution_name: Annotated[str, "Indian institution name to look up"]
    ) -> Annotated[str, "JSON string with institution category and threshold information"]:
        """
        Get detailed information about an Indian institution's category and requirements.
        
        Useful for understanding Category 1 vs Category 2 classification and thresholds.
        """
        try:
            from app.agents.india_eligibility import IndiaEligibilityEvaluator
            
            evaluator = IndiaEligibilityEvaluator()
            canonical_name, confidence = evaluator._normalize_institution_name(institution_name)
            category = evaluator.classify_category(canonical_name)
            
            # Get threshold information
            from app.agents.india_eligibility import INDIA_THRESHOLDS
            thresholds = INDIA_THRESHOLDS[category]
            
            return json.dumps({
                "institution_name": institution_name,
                "canonical_name": canonical_name,
                "category": category,
                "confidence": confidence,
                "thresholds": {
                    "first_class": thresholds["first"],
                    "upper_second_21": thresholds["2:1"],
                    "lower_second_22": thresholds["2:2"]
                },
                "category_description": {
                    "category1": "INI, IoE, NIRF Top 100, NLUs, specified autonomous institutions",
                    "category2": "All other universities and colleges recognized by Government of India"
                }[category]
            }, ensure_ascii=False, indent=2)
            
        except Exception as e:
            return json.dumps({
                "institution_name": institution_name,
                "error": str(e),
                "category": "unknown"
            })