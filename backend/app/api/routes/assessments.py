from __future__ import annotations

from typing import Annotated, Literal
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import select
from pathlib import Path
from datetime import datetime

from app.db.session import get_db
from app.api.dependencies import get_current_active_user
from app.models.user import User
from app.models.assessment import AssessmentRun, Applicant, ApplicantDocument
from app.models.evaluation import ApplicantGating
from app.models import AdmissionRuleSet
from app.schemas.assessments import (
    AssessmentRunCreate,
    AssessmentRunRead,
    AssessmentRunDetail,
)
from app.services.rule_import_service import RuleImportService
from app.agents.model_config import get_supported_models, get_agent_types
from app.services.storage import save_zip, extract_zip, iter_applicant_folders, guess_content_type, read_text_preview
import logging
from app.models.run_log import RunLog
import re


router = APIRouter(prefix="/assessments", tags=["assessments"])
def _generate_run_name(rule_set_name: str) -> str:
    """Create a human-friendly run name: "Major-YYYY-MM".

    The major/program name is taken from the bound rule set's name.
    """
    return f"{rule_set_name}-{datetime.utcnow().strftime('%Y-%m')}"


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/runs", response_model=AssessmentRunRead)
def create_run(
    data: AssessmentRunCreate, 
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    # Allow creating an empty run (rule_set can be bound later)
    if data.rule_set_id:
        rs = db.get(AdmissionRuleSet, data.rule_set_id)
        if not rs:
            raise HTTPException(status_code=404, detail="Rule set not found")
    # Validate optional agent_models mapping
    agent_models: dict[str, str] | None = None
    if data.agent_models:
        supported = set(get_supported_models())
        valid_agents = set(get_agent_types())
        invalid_agents = [k for k in data.agent_models.keys() if k not in valid_agents]
        invalid_models = [m for m in data.agent_models.values() if m not in supported]
        if invalid_agents:
            raise HTTPException(status_code=400, detail=f"Invalid agent types: {invalid_agents}")
        if invalid_models:
            raise HTTPException(status_code=400, detail=f"Unsupported models: {invalid_models}")
        agent_models = dict(data.agent_models)

    run = AssessmentRun(
        owner_user_id=current_user.id,
        rule_set_id=data.rule_set_id,
        rule_set_url=data.rule_set_url,
        custom_requirements=data.custom_requirements or [],
        agent_models=agent_models,
        status="created",
    )
    # If rule_set_id provided at creation time, set a generated name
    if data.rule_set_id:
        rs = db.get(AdmissionRuleSet, data.rule_set_id)
        if rs:
            run.name = _generate_run_name(rs.name)
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


@router.post("/runs/create-with-url", response_model=AssessmentRunRead)
async def create_run_with_url_import(
    data: AssessmentRunCreate, 
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    """Create assessment run and immediately import rules from URL if provided.
    
    This endpoint performs URL rule extraction before creating the run,
    ensuring the rule set is available before concurrent agents start.
    """
    if not data.rule_set_url:
        raise HTTPException(status_code=400, detail="rule_set_url is required for this endpoint")
    
    # Validate optional agent_models mapping
    agent_models: dict[str, str] | None = None
    if data.agent_models:
        supported = set(get_supported_models())
        valid_agents = set(get_agent_types())
        invalid_agents = [k for k in data.agent_models.keys() if k not in valid_agents]
        invalid_models = [m for m in data.agent_models.values() if m not in supported]
        if invalid_agents:
            raise HTTPException(status_code=400, detail=f"Invalid agent types: {invalid_agents}")
        if invalid_models:
            raise HTTPException(status_code=400, detail=f"Unsupported models: {invalid_models}")
        agent_models = dict(data.agent_models)
    
    # Import rules from URL first
    try:
        logging.info(f"Creating assessment run with URL import: {data.rule_set_url}")
        
        rule_set, url_result = await RuleImportService.import_rules_from_url(
            db=db,
            url=data.rule_set_url,
            custom_requirements=data.custom_requirements,
            temporary=True,  # Mark as temporary for assessment runs
            model_override=agent_models.get("url_rules_extractor") if agent_models else None,
        )
        
        # Create assessment run with the imported rule set
        run = AssessmentRun(
            owner_user_id=current_user.id,
            rule_set_id=rule_set.id,
            rule_set_url=data.rule_set_url,
            custom_requirements=data.custom_requirements or [],
            agent_models=agent_models,
            status="created",
        )
        run.name = _generate_run_name(rule_set.name)
        
        db.add(run)
        db.commit()
        db.refresh(run)
        
        logging.info(f"Created assessment run {run.id} with imported rule set {rule_set.id}")
        return run
        
    except Exception as e:
        logging.exception(f"Failed to create assessment run with URL import: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to import rules from URL: {str(e)}")


@router.get("/runs", response_model=list[AssessmentRunRead])
def list_runs(
    current_user: Annotated[User, Depends(get_current_active_user)],
    visible_only: bool = True,
    db: Session = Depends(get_db),
):
    stmt = select(AssessmentRun).order_by(AssessmentRun.created_at.desc())
    # Default: restrict to current user's runs unless caller is superuser
    if current_user and not current_user.is_superuser:
        stmt = stmt.where(AssessmentRun.owner_user_id == current_user.id)
    if visible_only:
        # Hide preliminary runs that have not been started
        stmt = stmt.where(AssessmentRun.status.in_(["processing", "completed", "failed"]))
    runs = db.execute(stmt).scalars().all()
    return list(runs)


@router.get("/runs/{run_id}", response_model=AssessmentRunDetail)
def get_run(
    run_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Session = Depends(get_db),
):
    run = db.get(AssessmentRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Not found")
    if (not current_user.is_superuser) and (run.owner_user_id != current_user.id):
        raise HTTPException(status_code=403, detail="Forbidden")
    # eager load applicants and documents
    _ = run.applicants  # relationships will be included via from_attributes
    return run


@router.delete("/runs/{run_id}")
def delete_run(
    run_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Session = Depends(get_db),
) -> dict[str, int]:
    run = db.get(AssessmentRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    if (not current_user.is_superuser) and (run.owner_user_id != current_user.id):
        raise HTTPException(status_code=403, detail="Forbidden")
    db.delete(run)
    db.commit()
    return {"deleted": run_id}


@router.delete("/runs")
def delete_runs(
    current_user: Annotated[User, Depends(get_current_active_user)],
    status: str | None = None,
    db: Session = Depends(get_db),
) -> dict[str, int]:
    # Danger: bulk delete. Intended for cleanup of preliminary runs.
    stmt = select(AssessmentRun)
    if not current_user.is_superuser:
        stmt = stmt.where(AssessmentRun.owner_user_id == current_user.id)
    if status:
        stmt = stmt.where(AssessmentRun.status == status)
    items = db.execute(stmt).scalars().all()
    count = 0
    for r in items:
        db.delete(r)
        count += 1
    db.commit()
    return {"deleted": count}


@router.post("/runs/{run_id}/upload", response_model=AssessmentRunRead)
async def upload_zip(
    run_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    run = db.get(AssessmentRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    if (not current_user.is_superuser) and (run.owner_user_id != current_user.id):
        raise HTTPException(status_code=403, detail="Forbidden")

    # Clear any previously uploaded applicants/documents for this run
    # so that a new upload replaces the dataset instead of appending.
    existing = db.query(Applicant).filter(Applicant.run_id == run.id).all()
    for a in existing:
        db.delete(a)
    db.flush()

    content = await file.read()
    zip_path = save_zip(content, run_id)
    extract_root = extract_zip(zip_path, run_id)

    # Build applicants and documents based on top-level folders
    for folder in iter_applicant_folders(extract_root):
        # Try to parse display name and email from folder name patterns like
        # "First_Last_email@example.com" or "First Last (email@example.com)".
        display_name: str | None = None
        email: str | None = None
        # Pattern 1: name_email@example.com (underscores allowed in name)
        m1 = re.match(r"^([A-Za-z]+[A-Za-z_\- ]*[A-Za-z])[_-]+([A-Za-z0-9_.+-]+@[A-Za-z0-9.-]+)$", folder.name)
        if m1:
            display_name = m1.group(1).replace('_', ' ').strip()
            email = m1.group(2)
        # Pattern 2: Name (email@example.com)
        if not email:
            m2 = re.match(r"^(.+?)\s*\(([^\)]+@[^\)]+)\)$", folder.name)
            if m2:
                display_name = m2.group(1).strip()
                email = m2.group(2).strip()
        # Fallback: try to split by last underscore
        if not email and '_' in folder.name:
            parts = folder.name.rsplit('_', 1)
            if len(parts) == 2 and '@' in parts[1]:
                display_name = parts[0].replace('_', ' ').strip()
                email = parts[1]

        applicant = Applicant(run_id=run.id, folder_name=folder.name, display_name=display_name, email=email)
        db.add(applicant)
        db.flush()
        for p in folder.rglob("*"):
            if p.is_file():
                rel = p.relative_to(extract_root).as_posix()
                content_type = guess_content_type(p)
                preview = read_text_preview(p)
                doc = ApplicantDocument(
                    applicant_id=applicant.id,
                    rel_path=rel,
                    original_filename=p.name,
                    content_type=content_type,
                    size_bytes=p.stat().st_size,
                    text_preview=preview,
                )
                db.add(doc)
    run.status = "uploaded"
    db.commit()
    db.refresh(run)
    return run


class RunRuleSetUpdate(BaseModel):
    rule_set_id: int | None = None
    rule_set_url: str | None = None
    custom_requirements: list[str] | None = None


@router.put("/runs/{run_id}/rule-set", response_model=AssessmentRunRead)
async def update_run_rule_set(
    run_id: int,
    payload: RunRuleSetUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    run = db.get(AssessmentRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    if (not current_user.is_superuser) and (run.owner_user_id != current_user.id):
        raise HTTPException(status_code=403, detail="Forbidden")
    if not payload.rule_set_id and not payload.rule_set_url:
        raise HTTPException(status_code=400, detail="Either rule_set_id or rule_set_url must be provided")

    if payload.rule_set_id:
        rs = db.get(AdmissionRuleSet, payload.rule_set_id)
        if not rs:
            raise HTTPException(status_code=404, detail="Rule set not found")
        run.rule_set_id = rs.id
        run.rule_set_url = None
        run.name = _generate_run_name(rs.name)
    else:
        # Import from URL, then bind to run
        rule_set, _ = await RuleImportService.import_rules_from_url(
            db=db,
            url=payload.rule_set_url,  # type: ignore[arg-type]
            custom_requirements=payload.custom_requirements,
            temporary=True,
            model_override=None,
        )
        run.rule_set_id = rule_set.id
        run.rule_set_url = payload.rule_set_url
        run.name = _generate_run_name(rule_set.name)

    if payload.custom_requirements is not None:
        run.custom_requirements = payload.custom_requirements

    db.add(run)
    db.commit()
    db.refresh(run)
    return run


@router.post("/runs/{run_id}/start", response_model=AssessmentRunRead)
def start_run(
    run_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Session = Depends(get_db),
):
    run = db.get(AssessmentRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    if (not current_user.is_superuser) and (run.owner_user_id != current_user.id):
        raise HTTPException(status_code=403, detail="Forbidden")
    if not run.rule_set_id:
        raise HTTPException(status_code=400, detail="Rule set not set for this run")
    # For now, set to processing and rely on Celery pipeline stub
    run.status = "processing"
    db.add(run)
    db.commit()

    try:
        from app.tasks.assessment_pipeline import orchestrate_run

        orchestrate_run.delay(run_id)
    except Exception as e:
        # If Celery not running, mark failed gracefully
        logging.exception("Failed to enqueue orchestrate_run: %s", e)
        run.status = "failed"
        db.add(run)
        db.commit()
    db.refresh(run)
    return run


@router.put("/runs/{run_id}/models", response_model=AssessmentRunRead)
def set_run_agent_models(
    run_id: int,
    payload: dict[str, str],
    db: Session = Depends(get_db),
):
    """Set or update per-run agent model mapping.

    Body: { "english": "gpt-4.1", "degree": "o3-mini", ... }
    """
    run = db.get(AssessmentRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Body must be a JSON object of agent->model")
    supported = set(get_supported_models())
    valid_agents = set(get_agent_types())
    invalid_agents = [k for k in payload.keys() if k not in valid_agents]
    invalid_models = [m for m in payload.values() if m not in supported]
    if invalid_agents:
        raise HTTPException(status_code=400, detail=f"Invalid agent types: {invalid_agents}")
    if invalid_models:
        raise HTTPException(status_code=400, detail=f"Unsupported models: {invalid_models}")

    run.agent_models = dict(payload)
    db.add(run)
    db.commit()
    db.refresh(run)
    return run
@router.get("/runs/{run_id}/logs")
def get_run_logs(
    run_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    limit: int = 200,
    applicant_id: int | None = None,
    agent: str | None = None,
    db: Session = Depends(get_db),
):
    """Return recent agent call logs for a run. No streaming; polling-friendly."""
    run = db.get(AssessmentRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    if (not current_user.is_superuser) and (run.owner_user_id != current_user.id):
        raise HTTPException(status_code=403, detail="Forbidden")
    q = db.query(RunLog).filter(RunLog.run_id == run_id)
    if applicant_id:
        q = q.filter(RunLog.applicant_id == applicant_id)
    if agent:
        q = q.filter(RunLog.agent_name == agent)
    q = q.order_by(RunLog.created_at.desc())
    items = q.limit(max(10, min(1000, limit))).all()
    return [
        {
            "id": it.id,
            "run_id": it.run_id,
            "applicant_id": it.applicant_id,
            "agent": it.agent_name,
            "phase": it.phase,
            "message": it.message,
            "created_at": it.created_at.isoformat(),
        }
        for it in items
    ]


class ManualDecisionUpdate(BaseModel):
    decision: Literal["ACCEPT", "MIDDLE", "REJECT", "accept", "middle", "reject", None] | None


@router.put("/applicants/{applicant_id}/manual-decision")
def set_manual_decision(
    applicant_id: int,
    payload: ManualDecisionUpdate,
    db: Session = Depends(get_db),
    current_user: Annotated[User, Depends(get_current_active_user)] = None,
):
    applicant = db.get(Applicant, applicant_id)
    if not applicant:
        raise HTTPException(status_code=404, detail="Applicant not found")
    # Ownership check via applicant -> run
    run = db.get(AssessmentRun, applicant.run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    if current_user and (not current_user.is_superuser) and (run.owner_user_id != current_user.id):
        raise HTTPException(status_code=403, detail="Forbidden")

    gating = db.query(ApplicantGating).filter_by(applicant_id=applicant_id).one_or_none()
    if not gating:
        gating = ApplicantGating(applicant_id=applicant_id, decision="MIDDLE", reasons=[])
        db.add(gating)
        db.flush()

    # Normalize decision and apply/clear
    normalized: str | None
    if payload.decision is None:
        normalized = None
    else:
        val = str(payload.decision).strip().upper()
        if val not in {"ACCEPT", "MIDDLE", "REJECT"}:
            raise HTTPException(status_code=400, detail="Invalid decision. Use ACCEPT, MIDDLE, or REJECT, or null to clear.")
        normalized = val

    gating.manual_decision = normalized
    gating.manual_set_at = datetime.utcnow() if normalized else None
    db.add(gating)
    db.commit()
    db.refresh(gating)

    return {
        "applicant_id": applicant_id,
        "manual_decision": gating.manual_decision,
        "manual_set_at": gating.manual_set_at.isoformat() if gating.manual_set_at else None,
    }
