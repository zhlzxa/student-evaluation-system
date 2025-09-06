"""
Seed China and India degree equivalency rules from text files.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from app.db.session import SessionLocal
from app.models.rules import CountryDegreeEquivalency
from app.services.degree_ingest_service import upsert_country_equivalency

def seed_china_rules():
    """Seed China degree equivalency rules."""
    db = SessionLocal()
    try:
        # For top-tier universities (85% for 2:1, 80% for 2:2)
        tier1_85_requirement = {
            "type": "percentage",
            "upper_second": {"min_percentage": 85},
            "lower_second": {"min_percentage": 80},
            "first_class": {"min_percentage": 90},
            "note": "For universities in the approved list including Project 211, 985, and Double First-Class universities"
        }
        
        # For other universities (90% for 2:1, 85% for 2:2)  
        other_90_requirement = {
            "type": "percentage", 
            "upper_second": {"min_percentage": 90},
            "lower_second": {"min_percentage": 85},
            "first_class": {"min_percentage": 95},
            "note": "For all other universities recognised by the Chinese Ministry of Education"
        }
        
        upsert_country_equivalency(db, "CHN", "China", "UPPER_SECOND", tier1_85_requirement, "https://www.ucl.ac.uk/prospective-students/international/graduate-equivalent-international-qualifications-202425")
        upsert_country_equivalency(db, "CHN", "China", "LOWER_SECOND", tier1_85_requirement, "https://www.ucl.ac.uk/prospective-students/international/graduate-equivalent-international-qualifications-202425")
        upsert_country_equivalency(db, "CHN", "China", "FIRST", tier1_85_requirement, "https://www.ucl.ac.uk/prospective-students/international/graduate-equivalent-international-qualifications-202425")
        
        db.commit()
        print("China degree equivalency rules seeded successfully")
        
    except Exception as e:
        db.rollback()
        print(f"Error seeding China rules: {e}")
    finally:
        db.close()

def seed_india_rules():
    """Seed India degree equivalency rules."""
    db = SessionLocal()
    try:
        # Category 1 institutions
        category1_requirement = {
            "type": "gpa_percentage",
            "first_class": {
                "cgpa_10": 8.0,
                "cgpa_8": 6.5, 
                "cgpa_7": 6.0,
                "cgpa_6": 4.5,
                "cgpa_4": 3.3,
                "percentage": 65
            },
            "upper_second": {
                "cgpa_10": 7.5,
                "cgpa_8": 6.0,
                "cgpa_7": 5.5, 
                "cgpa_6": 4.0,
                "cgpa_4": 3.0,
                "percentage": 60
            },
            "lower_second": {
                "cgpa_10": 6.5,
                "cgpa_8": 5.5,
                "cgpa_7": 5.0,
                "cgpa_6": 3.5,
                "cgpa_4": 2.7, 
                "percentage": 55
            },
            "category": "category1",
            "note": "For Category 1 institutions: Institutes of National Importance, Institute of Eminence, NIRF Top 100, NLUs, and specified autonomous institutions"
        }
        
        # Category 2 institutions  
        category2_requirement = {
            "type": "gpa_percentage",
            "first_class": {
                "cgpa_10": 8.5,
                "cgpa_8": 7.0,
                "cgpa_7": 6.5,
                "cgpa_6": 5.0,
                "cgpa_4": 3.6,
                "percentage": 70
            },
            "upper_second": {
                "cgpa_10": 8.0,
                "cgpa_8": 6.5,
                "cgpa_7": 6.0,
                "cgpa_6": 4.5,
                "cgpa_4": 3.3,
                "percentage": 65
            },
            "lower_second": {
                "cgpa_10": 7.0,
                "cgpa_8": 6.0,
                "cgpa_7": 5.5,
                "cgpa_6": 4.0,
                "cgpa_4": 3.0,
                "percentage": 60
            },
            "category": "category2", 
            "note": "For Category 2 institutions: All universities and colleges not featured in Category 1"
        }
        
        upsert_country_equivalency(db, "IND", "India", "FIRST", category1_requirement, "https://www.ucl.ac.uk/prospective-students/international/graduate-equivalent-international-qualifications-202425")
        upsert_country_equivalency(db, "IND", "India", "UPPER_SECOND", category1_requirement, "https://www.ucl.ac.uk/prospective-students/international/graduate-equivalent-international-qualifications-202425")
        upsert_country_equivalency(db, "IND", "India", "LOWER_SECOND", category1_requirement, "https://www.ucl.ac.uk/prospective-students/international/graduate-equivalent-international-qualifications-202425")
        
        db.commit()
        print("India degree equivalency rules seeded successfully")
        
    except Exception as e:
        db.rollback()
        print(f"Error seeding India rules: {e}")
    finally:
        db.close()

def main():
    """Main function to seed both China and India rules."""
    print("Seeding China and India degree equivalency rules...")
    seed_china_rules()
    seed_india_rules()
    print("All rules seeded successfully!")

if __name__ == "__main__":
    main()