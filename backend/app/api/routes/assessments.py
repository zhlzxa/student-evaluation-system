from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import select
from pathlib import Path

from app.db.session import get_db
from app.models.assessment import AssessmentRun, Applicant, ApplicantDocument
from app.models import AdmissionRuleSet
from app.schemas.assessments import (
    AssessmentRunCreate,
    AssessmentRunRead,
    AssessmentRunDetail,
)
from app.services.storage import save_zip, extract_zip, iter_applicant_folders, guess_content_type, read_text_preview
import logging


router = APIRouter(prefix="/assessments", tags=["assessments"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/runs", response_model=AssessmentRunRead)
def create_run(data: AssessmentRunCreate, db: Session = Depends(get_db)):
    if not data.rule_set_id and not data.source_url:
        raise HTTPException(status_code=400, detail="Either rule_set_id or source_url must be provided")
    if data.rule_set_id:
        rs = db.get(AdmissionRuleSet, data.rule_set_id)
        if not rs:
            raise HTTPException(status_code=404, detail="Rule set not found")
    run = AssessmentRun(
        rule_set_id=data.rule_set_id,
        source_url=data.source_url,
        custom_requirements=data.custom_requirements or [],
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
