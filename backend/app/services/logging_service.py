from __future__ import annotations

from typing import Optional
from sqlalchemy.orm import Session
from datetime import datetime

from app.db.session import SessionLocal
from app.models.run_log import RunLog


def log_agent_event(
    run_id: int,
    agent_name: str,
    phase: str,
    message: str,
    applicant_id: Optional[int] = None,
) -> None:
    """Persist a log entry for an agent call.

    Uses a short-lived DB session to avoid coupling to request/session scope.
    """
    db: Session = SessionLocal()
    try:
        db.add(RunLog(run_id=run_id, applicant_id=applicant_id, agent_name=agent_name, phase=phase, message=message, created_at=datetime.utcnow()))
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()

