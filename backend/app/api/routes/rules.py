from __future__ import annotations

from datetime import datetime
from typing import Sequence

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import (
    DegreeEquivalencySource,
    CountryDegreeEquivalency,
    SpecialInstitutionRule,
    EnglishRule,
    AdmissionRuleSet,
)
from app.schemas import (
    DegreeEquivalencySourceCreate,
    DegreeEquivalencySourceRead,
    CountryDegreeEquivalencyCreate,
    CountryDegreeEquivalencyRead,
    SpecialInstitutionRuleCreate,
    SpecialInstitutionRuleRead,
    EnglishRuleCreate,
    EnglishRuleRead,
    AdmissionRuleSetCreate,
    AdmissionRuleSetRead,
)
from app.services.rules_service import preview_page_text, extract_programme_basics, extract_programme_name_from_url_and_text
import logging
from app.agents.rules_parser import generate_checklists, generate_checklists_debug
from app.agents.degree_ingest import ingest_equivalency_from_text
from app.services.degree_ingest_service import (
    upsert_country_equivalency,
    upsert_special_institution,
    ensure_sources,
)
from app.services.degree_bs4 import parse_country_requirements
from datetime import datetime
from app.services.degree_bs4 import parse_all_tables


router = APIRouter(prefix="/rules", tags=["rules"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/azure/ping")
async def azure_ping() -> dict[str, str]:
    """Lightweight connectivity test for Azure AI Agent.

    Returns status and a short echo reply when Azure is reachable.
    """
    try:
        from app.agents.azure_client import run_single_turn

        reply = await run_single_turn(
            name="PingAgent",
            instructions="Reply with 'pong' only.",
            message="ping",
            with_bing_grounding=False,
        )
        return {"status": "ok", "reply": str(reply)[:200]}
    except Exception as e:
        logging.exception("azure_ping failed: %s", e)
        return {"status": "error", "error": str(e)}


# Degree sources
@router.post("/degree/sources", response_model=DegreeEquivalencySourceRead)
def create_degree_source(data: DegreeEquivalencySourceCreate, db: Session = Depends(get_db)):
    obj = DegreeEquivalencySource(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.post("/degree/ingest")
async def ingest_degree_equivalency(payload: dict | None = None, db: Session = Depends(get_db)):
    """Ingest degree equivalency rules from the official UCL page using BeautifulSoup text + agent parsing.

    Body: { "url": "..." } optional. Defaults to the known URL.
    Returns: { countries: n, specials: n }
    """
    url = (payload or {}).get(
        "url",
        "https://www.ucl.ac.uk/prospective-students/international/graduate-equivalent-international-qualifications-202425",
    )
    import httpx
    from bs4 import BeautifulSoup

    async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
        r = await client.get(url)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        text = soup.get_text("\n", strip=True)

    data = ingest_equivalency_from_text(text, url)
    countries = data.get("countries", [])
    specials = data.get("special_institutions", [])

    for item in countries:
        name = item.get("country_name") or ""
        code = item.get("country_code_iso3") or ""
        classes = item.get("classes") or {}
        for uk_class in ("FIRST", "UPPER_SECOND", "LOWER_SECOND"):
            cls = classes.get(uk_class)
            if not cls:
                continue
            requirement = cls.get("requirement") or {"text": cls.get("text")}
            source_url = cls.get("source_url") or url
            if not code or len(code) < 3:
                continue
            upsert_country_equivalency(db, code, name, uk_class, requirement, source_url)
    db.commit()

    for s in specials:
        code = s.get("country_code_iso3") or ""
        inst = s.get("institution_name") or ""
        cat = s.get("category")
        thr = s.get("thresholds")
        notes = s.get("notes")
        src = s.get("source_url") or url
        if not code or len(code) < 3 or not inst:
            continue
        upsert_special_institution(db, code, inst, cat, thr, notes, src)
    db.commit()

    ensure_sources(db, url)
    db.commit()

    return {"countries": len(countries), "specials": len(specials)}


@router.post("/degree/ingest_bs4_country")
async def ingest_bs4_country(
    payload: dict,
    db: Session = Depends(get_db),
):
    """Ingest a single country page via BeautifulSoup heuristics.

    Body example:
      {
        "country_name": "China",
        "country_code_iso3": "CHN",
        "url": "<country page url>"
      }
    """
    country_name = payload.get("country_name")
    country_code_iso3 = payload.get("country_code_iso3")
    url = payload.get("url")
    if not country_name or not country_code_iso3 or not url:
        raise HTTPException(status_code=400, detail="country_name, country_code_iso3, url are required")

    classes_text = parse_country_requirements(url, country_name=country_name)
    if not classes_text:
        return {"inserted": 0, "message": "no class-specific text found"}

    inserted = 0
    for uk_class, text in classes_text.items():
        upsert_country_equivalency(
            db,
            country_code_iso3,
            country_name,
            uk_class,
            requirement={"text": text},
            source_url=url,
        )
        inserted += 1
    db.commit()
    return {"inserted": inserted, "classes": list(classes_text.keys())}


@router.post("/degree/ingest_bs4_all")
async def ingest_bs4_all(payload: dict | None = None, db: Session = Depends(get_db)):
    """Parse all three tables (Second Higher, Second Lower, Above Honours) and ingest.

    Body: { "url": "..." } optional, defaults to the official URL.
    """
    url = (payload or {}).get(
        "url",
        "https://www.ucl.ac.uk/prospective-students/international/graduate-equivalent-international-qualifications-202425",
    )
    items = parse_all_tables(url)
    inserted = 0
    for it in items:
        name = it.get("country_name") or ""
        code = it.get("country_code_iso3") or ""
        classes = it.get("classes") or {}
        for uk_class, val in classes.items():
            if not code or len(code) < 3:
                continue
            requirement = val if isinstance(val, dict) else {"text": str(val)}
            upsert_country_equivalency(db, code, name, uk_class, requirement, url)
            inserted += 1
    db.commit()
    ensure_sources(db, url)
    db.commit()
    return {"countries": len(items), "class_rows_inserted": inserted}


@router.get("/degree/sources", response_model=list[DegreeEquivalencySourceRead])
def list_degree_sources(db: Session = Depends(get_db)):
    objs: Sequence[DegreeEquivalencySource] = db.execute(select(DegreeEquivalencySource)).scalars().all()
    return list(objs)


@router.get("/preview")
async def preview(url: str) -> dict[str, str]:
    text = await preview_page_text(url)
    return {"url": url, "preview": text}


@router.post("/generate-set", response_model=AdmissionRuleSetRead)
async def generate_rule_set(
    payload: dict,
    debug: bool = False,
    db: Session = Depends(get_db),
):
    """Generate a rule set by fetching a programme page URL and optional custom requirements,
    deriving agent checklists via AzureAIAgent, and storing the result.
    """
    name = payload.get("name")
    url = payload.get("url")
    custom: list[str] | None = payload.get("custom_requirements")
    if not url and not custom:
        raise HTTPException(status_code=400, detail="Provide url or custom_requirements")

    text = ""
    if url:
        text = await preview_page_text(url)
    
    # Extract meaningful program name if not provided or if it's generic
    if not name or name.strip().lower() in ["auto-generated", ""]:
        if url and text:
            name = extract_programme_name_from_url_and_text(url, text)
        else:
            name = f"Custom Rules {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"

    raw_output: str | None = None
    candidate_used: str | None = None
    try:
        if debug:
            parsed, raw_output, candidate_used = await generate_checklists_debug(text, custom)
        else:
            parsed = await generate_checklists(text, custom)
    except Exception as e:
        logging.exception("generate_checklists failed: %s", e)
        parsed = {}

    checklists = parsed.get("checklists", {}) if isinstance(parsed, dict) else {}
    if not isinstance(checklists, dict) or not checklists:
        checklists = {
            "english_agent": [],
            "degree_agent": [],
            "experience_agent": [],
            "ps_rl_agent": [],
            "academic_agent": [],
        }
    english_level = parsed.get("english_level") if isinstance(parsed, dict) else None
    degree_requirement_class = parsed.get("degree_requirement_class") if isinstance(parsed, dict) else None

    # Heuristic fill if agent failed or returned empty
    if english_level is None or degree_requirement_class is None:
        basics = extract_programme_basics(text)
        english_level = english_level or basics.get("english_level")
        degree_requirement_class = degree_requirement_class or basics.get("degree_requirement_class")
    # Try to attach the latest EnglishRule as default policy
    from sqlalchemy import select
    from app.models import EnglishRule
    english_rule = db.execute(select(EnglishRule).order_by(EnglishRule.last_verified_at.desc().nullslast(), EnglishRule.id.desc())).scalars().first()

    # Build metadata JSON and include optional debug info
    metadata: dict = {
        "checklists": checklists,
        "english_level": english_level,
        "degree_requirement_class": degree_requirement_class,
    }
    if debug:
        metadata["_debug"] = {
            "raw_first_800": (raw_output or "")[:800],
            "candidate_first_800": (candidate_used or "")[:800],
            "page_text_first_800": (text or "")[:800],
        }

    obj = AdmissionRuleSet(
        name=name,
        description=f"Generated from {url}" if url else None,
        metadata_json=metadata,
        english_rule_id=english_rule.id if english_rule else None,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


# Country mappings
@router.post("/degree/countries", response_model=CountryDegreeEquivalencyRead)
def upsert_country_equivalency(data: CountryDegreeEquivalencyCreate, db: Session = Depends(get_db)):
    stmt = select(CountryDegreeEquivalency).where(
        CountryDegreeEquivalency.country_code == data.country_code,
        CountryDegreeEquivalency.uk_class == data.uk_class,
    )
    existing = db.execute(stmt).scalar_one_or_none()
    if existing:
        for k, v in data.model_dump().items():
            setattr(existing, k, v)
        existing.last_verified_at = existing.last_verified_at or datetime.utcnow()
        db.add(existing)
        db.commit()
        db.refresh(existing)
        return existing
    obj = CountryDegreeEquivalency(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/degree/countries", response_model=list[CountryDegreeEquivalencyRead])
def list_country_equivalencies(
    uk_class: str | None = Query(None, description="Filter by UK class: FIRST, UPPER_SECOND, LOWER_SECOND"),
    db: Session = Depends(get_db),
):
    stmt = select(CountryDegreeEquivalency)
    if uk_class:
        stmt = stmt.where(CountryDegreeEquivalency.uk_class == uk_class)
    objs = db.execute(stmt).scalars().all()
    return list(objs)


# Special institutions
@router.post("/degree/special", response_model=SpecialInstitutionRuleRead)
def upsert_special_institution(data: SpecialInstitutionRuleCreate, db: Session = Depends(get_db)):
    stmt = select(SpecialInstitutionRule).where(
        SpecialInstitutionRule.country_code == data.country_code,
        SpecialInstitutionRule.institution_name == data.institution_name,
    )
    existing = db.execute(stmt).scalar_one_or_none()
    if existing:
        for k, v in data.model_dump().items():
            setattr(existing, k, v)
        db.add(existing)
        db.commit()
        db.refresh(existing)
        return existing
    obj = SpecialInstitutionRule(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/degree/special", response_model=list[SpecialInstitutionRuleRead])
def list_special_institutions(country_code: str | None = None, db: Session = Depends(get_db)):
    stmt = select(SpecialInstitutionRule)
    if country_code:
        code = country_code.strip().upper()
        if len(code) == 2:
            try:
                import pycountry  # type: ignore

                code = pycountry.countries.lookup(code).alpha_3
            except Exception:
                pass
        stmt = stmt.where(SpecialInstitutionRule.country_code == code)
    objs = db.execute(stmt).scalars().all()
    return list(objs)


# English rules
@router.post("/english", response_model=EnglishRuleRead)
def create_english_rule(data: EnglishRuleCreate, db: Session = Depends(get_db)):
    obj = EnglishRule(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/english", response_model=list[EnglishRuleRead])
def list_english_rules(db: Session = Depends(get_db)):
    objs = db.execute(select(EnglishRule)).scalars().all()
    return list(objs)


# Rule sets
@router.post("/sets", response_model=AdmissionRuleSetRead)
def create_rule_set(data: AdmissionRuleSetCreate, db: Session = Depends(get_db)):
    obj = AdmissionRuleSet(**data.model_dump())
    db.add(obj)
    try:
        db.commit()
    except Exception as e:  # pragma: no cover - simple error mapping
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    db.refresh(obj)
    return obj


@router.get("/sets", response_model=list[AdmissionRuleSetRead])
def list_rule_sets(db: Session = Depends(get_db)):
    objs = db.execute(select(AdmissionRuleSet)).scalars().all()
    return list(objs)


@router.get("/sets/{set_id}", response_model=AdmissionRuleSetRead)
def get_rule_set(set_id: int, db: Session = Depends(get_db)):
    obj = db.get(AdmissionRuleSet, set_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Rule set not found")
    return obj


@router.delete("/sets/{set_id}")
def delete_rule_set(set_id: int, db: Session = Depends(get_db)) -> dict[str, int]:
    obj = db.get(AdmissionRuleSet, set_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Rule set not found")
    db.delete(obj)
    db.commit()
    return {"deleted": set_id}
