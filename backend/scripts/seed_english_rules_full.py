"""
Seed comprehensive English language rules based on UCL guidance.

Usage (PowerShell):
  $env:PYTHONPATH="backend"; python backend/scripts/seed_english_rules_full.py

This script inserts a new EnglishRule row with nationality exemption countries,
degree-obtained exemption countries, and detailed level requirements for accepted tests.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any
import os
import sys

# Ensure 'backend' (script parent) is importable when invoked from repo root
SCRIPT_DIR = os.path.abspath(os.path.dirname(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from sqlalchemy.orm import Session

from app.db.session import SessionLocal, engine, Base
from app.models import EnglishRule


SOURCE_URL = "https://www.ucl.ac.uk/prospective-students/graduate/english-language-requirements"


NATIONALITY_EXEMPT = [
    "Antigua and Barbuda",
    "Australia",
    "The Bahamas",
    "Barbados",
    "Belize",
    "The British overseas territories",
    "Canada",
    "Dominica",
    "Grenada",
    "Guyana",
    "Ireland",
    "Jamaica",
    "Malta",
    "New Zealand",
    "St Kitts and Nevis",
    "St Lucia",
    "St Vincent and the Grenadines",
    "Trinidad and Tobago",
    "United Kingdom",
    "United States of America",
]


DEGREE_EXEMPT = [
    "Antigua and Barbuda",
    "Australia",
    "Barbados",
    "Belize",
    "Botswana",
    "Cameroon",
    "Canada",
    "Caribbean / West Indies (English-speaking Caribbean Commonwealth territories)",
    "Dominica",
    "Fiji",
    "Gambia",
    "Ghana",
    "Grenada",
    "Guyana",
    "Ireland",
    "Jamaica",
    "Kenya",
    "Malawi",
    "Malta",
    "Mauritius",
    "New Zealand",
    "Nigeria",
    "Singapore",
    "South Africa",
    "St Kitts and Nevis",
    "St Lucia",
    "St Vincent and the Grenadines",
    "Swaziland",
    "Tanzania",
    "The Bahamas",
    "Trinidad and Tobago",
    "The Netherlands",
    "Uganda",
    "United Kingdom",
    "United States of America",
    "Zambia",
    "Zimbabwe",
]


DEGREE_EXEMPT_CONDITIONS = {
    "Cameroon": "qualification must be taught in English",
    "Malta": "degree must be taught entirely in English",
    "The Netherlands": "degree must be taught entirely in English",
}


LEVELS: dict[str, Any] = {
    "recency_months": 24,
    "notes": {
        "transnational": "Transnational programmes not fully completed in a majority English-speaking country require a recognised English test.",
    },
    "not_accepted": [
        "IELTS One Skill Retake",
        "TOEFL iBT MyBestScore",
        "Oxford Test of English (non-Advanced versions)",
        "Unofficial test reports, screenshots, or email submissions",
    ],
    "tests": {
        "UCL_Presessional": {
            "level1": {"overall_percent": 65, "min_each_percent": 60},
            "level2": {"overall_percent": 70, "min_each_percent": 65},
            "level3": {"overall_percent": 70, "min_each_percent": 70},
            "level4": {"overall_percent": 75, "min_each_percent": 70},
            "level5": {"overall_percent": 80, "min_each_percent": 80},
        },
        "UCL_International_PreMasters": {
            "level1": {"overall_percent": 65, "min_each_percent": 60},
            "level2": {"overall_percent": 70, "min_each_percent": 65},
            "level3": {"overall_percent": 70, "min_each_percent": 70},
            "level4": {"overall_percent": 75, "min_each_percent": 70},
            "level5": {"overall_percent": 80, "min_each_percent": 80},
        },
        "IELTS_Academic": {
            "notes": "Academic Online accepted; One Skill Retake not accepted",
            "level1": {"overall": 6.5, "min_each": 6.0},
            "level2": {"overall": 7.0, "min_each": 6.5},
            "level3": {"overall": 7.0, "min_each": 7.0},
            "level4": {"overall": 7.5, "min_each": 7.0},
            "level5": {"overall": 8.0, "min_each": 8.0},
        },
        "TOEFL_iBT": {
            "notes": "Special Home Edition accepted; MyBestScore not accepted; institution code 9163",
            "level1": {"overall": 92, "reading": 24, "writing": 24, "speaking": 20, "listening": 20},
            "level2": {"overall": 96, "reading": 24, "writing": 24, "speaking": 22, "listening": 22},
            "level3": {"overall": 100, "reading": 25, "writing": 25, "speaking": 23, "listening": 23},
            "level4": {"overall": 109, "reading": 27, "writing": 27, "speaking": 23, "listening": 23},
            "level5": {"overall": 110, "reading": 29, "writing": 29, "speaking": 23, "listening": 23},
        },
        "Cambridge_C2_Proficiency": {
            "level1": {"overall": 176, "min_each": 169},
            "level2": {"overall": 180, "min_each": 172},
            "level3": {"overall": 185, "min_each": 180},
            "level4": {"overall": 191, "min_each": 180},
            "level5": {"overall": 210, "min_each": 200},
        },
        "Cambridge_C1_Advanced": {
            "level1": {"overall": 176, "min_each": 169},
            "level2": {"overall": 180, "min_each": 172},
            "level3": {"overall": 185, "min_each": 180},
            "level4": {"overall": 191, "min_each": 180},
            "level5": {"overall": 210, "min_each": 200},
        },
        "PTE_Academic": {
            "level1": {"overall": 75, "min_each": 67},
            "level2": {"overall": 76, "min_each": 75},
            "level3": {"overall": 76, "min_each": 76},
            "level4": {"overall": 80, "min_each": 76},
            "level5": {"overall": 88, "min_each": 80},
        },
        "Trinity_ISE_II": {
            "level1": {"all_components": "merit"},
            "level2": {"all_components": "distinction"},
            "level3": None,
            "level4": None,
            "level5": None,
        },
        "Trinity_ISE_III": {
            "level1": {"all_components": "pass"},
            "level2": {"all_components": "pass"},
            "level3": {"all_components": "pass"},
            "level4": {"all_components": "distinction"},
            "level5": None,
        },
        "Trinity_ISE_IV": {
            "level1": {"all_components": "pass"},
            "level2": {"all_components": "pass"},
            "level3": {"all_components": "pass"},
            "level4": {"all_components": "pass"},
            "level5": {"all_components": "pass"},
        },
        "OET": {
            "level1": {"grade": "C+", "overall_numeric": 300, "min_each_numeric": 250},
            "level2": {"grade": "B", "overall_numeric": 350, "min_each_numeric": 300},
            "level3": {"grade": "B", "overall_numeric": 350, "min_each_numeric": 350},
            "level4": {"grade": "B", "overall_numeric": 400, "min_each_numeric": 350},
            "level5": {"grade": "A", "overall_numeric": 450, "min_each_numeric": 450},
        },
        "PASHE": {
            "level1": {"overall_percent": 65, "min_each_percent": 60},
            "level2": {"overall_percent": 70, "min_each_percent": 65},
            "level3": {"overall_percent": 70, "min_each_percent": 70},
            "level4": {"overall_percent": 75, "min_each_percent": 70},
            "level5": {"overall_percent": 80, "min_each_percent": 80},
        },
        "LanguageCert_Academic": {
            "level1": {"overall": 70, "min_each": 65},
            "level2": {"overall": 75, "min_each": 70},
            "level3": {"overall": 75, "min_each": 75},
            "level4": {"overall": 80, "min_each": 75},
            "level5": {"overall": 85, "min_each": 85},
        },
        "Oxford_Test_of_English_Advanced": {
            "notes": "Only Advanced is accepted. Other OTE variants are not acceptable.",
            "level1": {"overall": 140, "speaking": 125, "listening": 125, "reading": 125, "writing": 125},
            "level2": {"overall": 150, "speaking": 140, "listening": 140, "reading": 140, "writing": 140},
            "level3": {"overall": 150, "speaking": 150, "listening": 150, "reading": 150, "writing": 150},
            "level4": {"overall": 160, "speaking": 150, "listening": 150, "reading": 150, "writing": 150},
            "level5": {"overall": 170, "speaking": 170, "listening": 170, "reading": 170, "writing": 170},
        },
    },
    "degree_exempt_conditions": DEGREE_EXEMPT_CONDITIONS,
}


def main() -> None:
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()
    try:
        rule = EnglishRule(
            nationality_exempt_countries=NATIONALITY_EXEMPT,
            degree_obtained_exempt_countries=DEGREE_EXEMPT,
            levels=LEVELS,
            source_url=SOURCE_URL,
            last_verified_at=datetime.utcnow(),
        )
        db.add(rule)
        db.commit()
        db.refresh(rule)
        print(f"Inserted EnglishRule id={rule.id}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
