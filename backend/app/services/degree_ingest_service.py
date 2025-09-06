from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models import CountryDegreeEquivalency, SpecialInstitutionRule, DegreeEquivalencySource


def upsert_country_equivalency(db: Session, country_code_iso3: str, country_name: str, uk_class: str, requirement: dict[str, Any], source_url: str | None) -> None:
    cc = (country_code_iso3 or "").upper().strip()[:3]
    ukc = uk_class.upper().strip()
    obj = db.query(CountryDegreeEquivalency).filter_by(country_code=cc, uk_class=ukc).one_or_none()
    if obj:
        obj.country_name = country_name
        obj.requirement = requirement
        obj.source_url = source_url
        db.add(obj)
    else:
        db.add(
            CountryDegreeEquivalency(
                country_code=cc,
                country_name=country_name,
                uk_class=ukc,
                requirement=requirement,
                source_url=source_url,
            )
        )


def upsert_special_institution(db: Session, country_code_iso3: str, institution_name: str, category: str | None, thresholds: dict[str, Any] | None, notes: str | None, source_url: str | None) -> None:
    cc = (country_code_iso3 or "").upper().strip()[:3]
    inst = institution_name.strip()
    obj = db.query(SpecialInstitutionRule).filter_by(country_code=cc, institution_name=inst).one_or_none()
    if obj:
        obj.category = (category or "").strip()
        obj.thresholds = thresholds
        obj.notes = notes
        db.add(obj)
    else:
        db.add(
            SpecialInstitutionRule(
                country_code=cc,
                institution_name=inst,
                category=(category or "").strip(),
                thresholds=thresholds,
                notes=notes,
            )
        )


def ensure_sources(db: Session, base_url: str) -> None:
    for uk_class, note in [
        ("FIRST", "First-class mapping (ingested)"),
        ("UPPER_SECOND", "2:1 mapping (ingested)"),
        ("LOWER_SECOND", "2:2 mapping (ingested)"),
    ]:
        obj = db.query(DegreeEquivalencySource).filter_by(uk_class=uk_class).one_or_none()
        if obj:
            obj.source_url = base_url
            obj.notes = note
            db.add(obj)
        else:
            db.add(DegreeEquivalencySource(uk_class=uk_class, source_url=base_url, notes=note))

