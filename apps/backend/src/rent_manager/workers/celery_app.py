from celery import Celery
from celery.schedules import crontab

from rent_manager.config import settings

celery_app = Celery(
    "rent_manager",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "rent_manager.workers.tasks.reminders",
        "rent_manager.workers.tasks.summaries",
        "rent_manager.workers.tasks.leases",
        "rent_manager.workers.tasks.invoices",
        "rent_manager.workers.tasks.webhooks",
    ],
)

celery_app.conf.update(
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    timezone="Asia/Kolkata",
    enable_utc=True,
    task_routes={
        "rent_manager.workers.tasks.reminders.*": {"queue": "notifications"},
        "rent_manager.workers.tasks.summaries.*": {"queue": "notifications"},
        "rent_manager.workers.tasks.leases.*": {"queue": "scheduled"},
        "rent_manager.workers.tasks.invoices.*": {"queue": "scheduled"},
        "rent_manager.workers.tasks.webhooks.*": {"queue": "webhooks"},
    },
    task_default_queue="default",
)

celery_app.conf.beat_schedule = {
    "generate_monthly_invoices": {
        "task": "rent_manager.workers.tasks.invoices.generate_monthly_invoices",
        "schedule": crontab(hour=2, minute=0),
    },
    "mark_overdue_invoices": {
        "task": "rent_manager.workers.tasks.invoices.mark_overdue_invoices",
        "schedule": crontab(hour=2, minute=30),
    },
    "run_reminder_ladder": {
        "task": "rent_manager.workers.tasks.reminders.run_reminder_ladder",
        "schedule": crontab(hour=9, minute=0),
    },
    "send_lease_expiry_alerts": {
        "task": "rent_manager.workers.tasks.leases.send_lease_expiry_alerts",
        "schedule": crontab(hour=9, minute=30),
    },
    "send_weekly_summary": {
        "task": "rent_manager.workers.tasks.summaries.send_weekly_summary",
        "schedule": crontab(day_of_week="fri", hour=11, minute=0),
    },
}
