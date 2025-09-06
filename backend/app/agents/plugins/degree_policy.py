from __future__ import annotations

from typing import Annotated, Dict, Any

from semantic_kernel.functions import kernel_function

from app.db.session import SessionLocal
from app.models import CountryDegreeEquivalency, SpecialInstitutionRule


class DegreePolicyPlugin:
    """DB-backed helper to fetch degree equivalency policy for a country.

    The LLM decides the country name (or ISO3) from applicant materials, then
    calls this tool to fetch the relevant requirement text for a target UK class.
    """

    @kernel_function(description="Fetch degree equivalency policy for a country and target class.")
    def get_policy_for_country(
        self,
        country: Annotated[str, "Country name or ISO3 code (e.g., China or CHN)"],
        target_class: Annotated[str, "UK class: FIRST, UPPER_SECOND, LOWER_SECOND"],
    ) -> Annotated[str, "JSON string with fields: country_name, country_code_iso3, target_class, requirement, source_url, all_classes (optional)"]:
        db = SessionLocal()
        try:
            q = country.strip()
            tc = (target_class or "").upper().strip()
            # Try ISO3 code direct match first
            rows = []
            if len(q) == 3 and q.upper() == q:
                rows = (
                    db.query(CountryDegreeEquivalency)
                    .filter(CountryDegreeEquivalency.country_code == q.upper())
                    .all()
                )
            if not rows:
                rows = (
                    db.query(CountryDegreeEquivalency)
                    .filter(CountryDegreeEquivalency.country_name.ilike(q))
                    .all()
                )
            if not rows:
                rows = (
                    db.query(CountryDegreeEquivalency)
                    .filter(CountryDegreeEquivalency.country_name.ilike(f"%{q}%"))
                    .all()
                )

            if not rows:
                return "{}"

            by_class: Dict[str, Any] = {}
            meta = {"country_name": rows[0].country_name, "country_code_iso3": rows[0].country_code}
            for r in rows:
                by_class[r.uk_class] = {
                    "requirement": r.requirement,
                    "source_url": r.source_url,
                }

            req = by_class.get(tc, {})
            import json

            return json.dumps({
                **meta,
                "target_class": tc,
                "requirement": req.get("requirement"),
                "source_url": req.get("source_url"),
                "all_classes": by_class,
            })
        finally:
            db.close()

    @kernel_function(description="List special institution rules for a country (e.g., CHN, IND).")
    def list_special_institutions(
        self,
        country_code_iso3: Annotated[str, "ISO3 code, e.g., CHN"],
    ) -> Annotated[str, "JSON string: array of items {institution_name, category, thresholds, notes}"]:
        db = SessionLocal()
        try:
            code = country_code_iso3.strip().upper()
            rows = (
                db.query(SpecialInstitutionRule)
                .filter(SpecialInstitutionRule.country_code == code)
                .all()
            )
            items = []
            for r in rows:
                items.append({
                    "institution_name": r.institution_name,
                    "category": r.category,
                    "thresholds": r.thresholds,
                    "notes": r.notes,
                })
            import json

            return json.dumps(items)
        finally:
            db.close()

