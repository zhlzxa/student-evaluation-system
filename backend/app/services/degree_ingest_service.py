from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models import CountryDegreeEquivalency, DegreeEquivalencySource


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

