from __future__ import annotations

from celery import Celery

from app.config import get_settings


settings = get_settings()

celery = Celery(
    settings.APP_NAME,
    broker=settings.celery_broker,
    backend=settings.celery_backend,
)

celery.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
)

# Autodiscover tasks: search for modules named 'tasks' under listed packages
celery.autodiscover_tasks(["app"])


@celery.task(name="tasks.ping")
def ping() -> str:
    return "pong"
