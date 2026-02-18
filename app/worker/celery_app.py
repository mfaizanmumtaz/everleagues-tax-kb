"""Celery application configuration for the document ingestion worker."""

from celery import Celery
from ..config import settings

celery_app = Celery(
    "everleagues_worker",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",

    # Reliability: acknowledge tasks only after completion so a crash
    # causes the broker to re-deliver the message.
    task_acks_late=True,
    task_reject_on_worker_lost=True,

    # Prefetch only one task per worker thread to avoid memory spikes
    # when many large files are queued at once.
    worker_prefetch_multiplier=1,

    # Concurrency (number of parallel worker threads/processes)
    worker_concurrency=settings.worker_concurrency,

    # Task timeouts: kill tasks that hang (e.g. stalled downloads)
    task_soft_time_limit=600,   # 10 min: raises SoftTimeLimitExceeded
    task_time_limit=660,        # 11 min: hard kill if soft limit ignored

    # Track when tasks start executing (not just queued)
    task_track_started=True,

    # Auto-expire results in Redis after 24 hours
    result_expires=86400,

    # Broker resilience
    broker_connection_retry_on_startup=True,
    broker_transport_options={
        "visibility_timeout": 3600,  # Re-deliver if not acked in 1 hour
    },

    # Timezone
    timezone="UTC",
    enable_utc=True,

    # Task discovery
    include=["app.worker.tasks"],
)
