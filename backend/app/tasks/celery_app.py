"""Celery application (Phase 1: one no-op task; beat schedule added later)."""

from celery import Celery

from app.config import settings

celery_app = Celery(
    "leadkar",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_track_started=True,
    timezone="UTC",
    enable_utc=True,
    # Tasks defined outside this module are loaded here (avoids import cycles).
    imports=("app.tasks.reconcile",),
    beat_schedule={
        # CLAUDE.md §7: reconcile missed PayPro webhooks every 15 minutes.
        "reconcile-pending-orders": {
            "task": "reconcile_pending_orders",
            "schedule": 15 * 60.0,
        },
    },
)


@celery_app.task(name="noop")
def noop() -> str:
    """No-op task to validate the worker round-trip."""
    return "ok"
