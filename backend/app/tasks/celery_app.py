"""Celery application (Phase 1: one no-op task; beat schedule added later)."""

from celery import Celery
from celery.schedules import crontab
from celery.signals import beat_init, worker_process_init

from app.config import settings
from app.utils.logging import configure_logging

celery_app = Celery(
    "leadkar",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)


@worker_process_init.connect
def _setup_worker_logging(**_kwargs) -> None:
    configure_logging("worker")


@beat_init.connect
def _setup_beat_logging(**_kwargs) -> None:
    configure_logging("beat")

celery_app.conf.update(
    task_track_started=True,
    timezone="UTC",
    enable_utc=True,
    # Tasks defined outside this module are loaded here (avoids import cycles).
    imports=(
        "app.tasks.reconcile",
        "app.tasks.deliver",
        "app.tasks.scrape",
        "app.tasks.refresh",
    ),
    beat_schedule={
        # CLAUDE.md §7: reconcile missed PayPro webhooks every 15 minutes.
        "reconcile-pending-orders": {
            "task": "reconcile_pending_orders",
            "schedule": 15 * 60.0,
        },
        # CLAUDE.md §5: quarterly catalog refresh (03:00 on day 1 every 3 months).
        # The task itself no-ops unless CATALOG_REFRESH_ENABLED is set (Rule #6).
        "refresh-catalog": {
            "task": "refresh_catalog",
            "schedule": crontab(minute=0, hour=3, day_of_month="1", month_of_year="*/3"),
        },
    },
)


@celery_app.task(name="noop")
def noop() -> str:
    """No-op task to validate the worker round-trip."""
    return "ok"
