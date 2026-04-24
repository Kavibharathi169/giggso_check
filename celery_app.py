import os

from celery import Celery


def _redis_url() -> str:
    return os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")


celery_app = Celery(
    "gov_file_extract",
    broker=_redis_url(),
    backend=os.getenv("CELERY_RESULT_BACKEND", _redis_url()),
)

celery_app.conf.update(
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=int(os.getenv("CELERY_WORKER_PREFETCH_MULTIPLIER", "1")),
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_time_limit=int(os.getenv("CELERY_TASK_TIME_LIMIT_SEC", "1800")),
    task_soft_time_limit=int(os.getenv("CELERY_TASK_SOFT_TIME_LIMIT_SEC", "1500")),
    broker_connection_retry_on_startup=True,
    worker_send_task_events=False,
    task_send_sent_event=False,
    result_expires=int(os.getenv("CELERY_RESULT_EXPIRES_SEC", "3600")),
    broker_pool_limit=int(os.getenv("CELERY_BROKER_POOL_LIMIT", "20")),
)
