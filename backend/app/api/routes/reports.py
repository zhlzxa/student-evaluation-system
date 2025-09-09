from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.session import get_db
from app.models.assessment import AssessmentRun, Applicant
from app.models.evaluation import ApplicantEvaluation, ApplicantGating, ApplicantRanking, PairwiseComparison


router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/runs/{run_id}")
def get_run_report(run_id: int, db: Session = Depends(get_db)):
    run = db.get(AssessmentRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    applicants = db.execute(select(Applicant).where(Applicant.run_id == run_id)).scalars().all()
    items = []
    # sort applicants by ranking.final_rank if available, otherwise by id
    ranks = {r.applicant_id: (r.final_rank if r.final_rank is not None else 10**9) for r in db.execute(select(ApplicantRanking)).scalars().all()}
    applicants_sorted = sorted(applicants, key=lambda x: (ranks.get(x.id, 10**9), x.id))

    for a in applicants_sorted:
        evs = db.execute(select(ApplicantEvaluation).where(ApplicantEvaluation.applicant_id == a.id)).scalars().all()
        g = db.execute(select(ApplicantGating).where(ApplicantGating.applicant_id == a.id)).scalar_one_or_none()
        r = db.execute(select(ApplicantRanking).where(ApplicantRanking.applicant_id == a.id)).scalar_one_or_none()
        items.append({
            "applicant_id": a.id,
            "display_name": a.display_name,
            "folder": a.folder_name,
            "evaluations": [
                {"agent": e.agent_name, "score": e.score, "details": e.details} for e in evs
            ],
            "gating": {"decision": g.decision if g else None, "reasons": g.reasons if g else []},
            "ranking": {"weighted_score": r.weighted_score if r else None, "final_rank": r.final_rank if r else None, "notes": r.notes if r else None},
        })
    return {
        "run": {"id": run.id, "status": run.status, "created_at": str(run.created_at)},
        "items": items,
        "pairwise": [
            {
                "a": p.applicant_a_id,
                "b": p.applicant_b_id,
                "winner": p.winner,
                "reason": p.reason,
                "pass": p.pass_index,
            }
            for p in db.execute(select(PairwiseComparison).where(PairwiseComparison.run_id == run_id)).scalars().all()
        ],
    }
