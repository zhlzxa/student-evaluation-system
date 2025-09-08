from __future__ import annotations

from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import select
from pathlib import Path

from app.db.session import get_db
from app.api.dependencies import get_current_active_user
from app.models.user import User
from app.models.assessment import AssessmentRun, Applicant, ApplicantDocument
from app.models import AdmissionRuleSet
from app.schemas.assessments import (
    AssessmentRunCreate,
    AssessmentRunRead,
    AssessmentRunDetail,
)
from app.agents.model_config import get_supported_models, get_agent_types
from app.services.storage import save_zip, extract_zip, iter_applicant_folders, guess_content_type, read_text_preview
import logging
from app.models.run_log import RunLog


router = APIRouter(prefix="/assessments", tags=["assessments"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/runs", response_model=AssessmentRunRead)
def create_run(
    data: AssessmentRunCreate, 
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    if not data.rule_set_id and not data.rule_set_url:
        raise HTTPException(status_code=400, detail="Either rule_set_id or rule_set_url must be provided")
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
        rule_set_id=data.rule_set_id,
        rule_set_url=data.rule_set_url,
        custom_requirements=data.custom_requirements or [],
        agent_models=agent_models,
        status="created",
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


@router.get("/runs", response_model=list[AssessmentRunRead])
def list_runs(
    visible_only: bool = True,
    db: Session = Depends(get_db),
):
    stmt = select(AssessmentRun).order_by(AssessmentRun.created_at.desc())
    if visible_only:
        # Hide preliminary runs that have not been started
        stmt = stmt.where(AssessmentRun.status.in_(["processing", "completed", "failed"]))
    runs = db.execute(stmt).scalars().all()
    return list(runs)


@router.get("/runs/{run_id}", response_model=AssessmentRunDetail)
def get_run(run_id: int, db: Session = Depends(get_db)):
    run = db.get(AssessmentRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Not found")
    # eager load applicants and documents
    _ = run.applicants  # relationships will be included via from_attributes
    return run


@router.delete("/runs/{run_id}")
def delete_run(run_id: int, db: Session = Depends(get_db)) -> dict[str, int]:
    run = db.get(AssessmentRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    db.delete(run)
    db.commit()
    return {"deleted": run_id}


@router.delete("/runs")
def delete_runs(
    status: str | None = None,
    db: Session = Depends(get_db),
) -> dict[str, int]:
    # Danger: bulk delete. Intended for cleanup of preliminary runs.
    stmt = select(AssessmentRun)
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
async def upload_zip(run_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    run = db.get(AssessmentRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

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
        applicant = Applicant(run_id=run.id, folder_name=folder.name)
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


@router.post("/runs/{run_id}/start", response_model=AssessmentRunRead)
def start_run(run_id: int, db: Session = Depends(get_db)):
    run = db.get(AssessmentRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
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

    Body: { "english": "gpt-4o", "degree": "o3-mini", ... }
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
    limit: int = 200,
    applicant_id: int | None = None,
    agent: str | None = None,
    db: Session = Depends(get_db),
):
    """Return recent agent call logs for a run. No streaming; polling-friendly."""
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
