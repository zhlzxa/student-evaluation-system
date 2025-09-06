"""
Clear all database tables except the rules tables that we just seeded.

Usage (PowerShell):
  $env:PYTHONPATH="backend"; python backend/scripts/clear_non_rules_tables.py
"""
from __future__ import annotations

import os
import sys

# Ensure 'backend' (script parent) is importable when invoked from repo root
SCRIPT_DIR = os.path.abspath(os.path.dirname(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from sqlalchemy.orm import Session
from app.db.session import SessionLocal, engine, Base
from app.models.assessment import AssessmentRun, Applicant, ApplicantDocument
from app.models.evaluation import ApplicantEvaluation, ApplicantGating, ApplicantRanking, PairwiseComparison
from app.models.rules import AdmissionRuleSet


def main() -> None:
    """Clear all non-rules tables while preserving rules data."""
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()
    
    try:
        print("Clearing non-rules database tables...")
        
        # Clear tables in the right order to respect foreign key constraints
        # Start with the most dependent tables first
        
        print("- Clearing pairwise_comparisons...")
        db.query(PairwiseComparison).delete()
        
        print("- Clearing applicant_evaluations...")
        db.query(ApplicantEvaluation).delete()
        
        print("- Clearing applicant_gating...")
        db.query(ApplicantGating).delete()
        
        print("- Clearing applicant_ranking...")
        db.query(ApplicantRanking).delete()
        
        print("- Clearing applicant_documents...")
        db.query(ApplicantDocument).delete()
        
        print("- Clearing applicants...")
        db.query(Applicant).delete()
        
        print("- Clearing assessment_runs...")
        db.query(AssessmentRun).delete()
        
        print("- Clearing admission_rule_sets (but keeping rules data)...")
        db.query(AdmissionRuleSet).delete()
        
        db.commit()
        print("Successfully cleared all non-rules tables!")
        
        # Keep the following tables with their data:
        # - degree_equivalency_sources
        # - country_degree_equivalencies  
        # - special_institution_rules
        # - english_rules
        
    except Exception as e:
        db.rollback()
        print(f"Error clearing tables: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()