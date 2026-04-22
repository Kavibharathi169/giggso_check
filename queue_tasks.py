import os

from celery.utils.log import get_task_logger

from celery_app import celery_app
from ingestion_pipeline import execute_ingestion_pipeline

logger = get_task_logger(__name__)


@celery_app.task(
    bind=True,
    name="ingestion.run_pipeline",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": 3},
)
def run_ingestion_pipeline(self, file_path: str, filename: str, job_id: str, user_id: str = "anonymous") -> dict:
    try:
        return execute_ingestion_pipeline(
            file_path=file_path,
            filename=filename,
            job_id=job_id,
            user_id=user_id,
            task_id=self.request.id,
        )
    except Exception as exc:
        logger.exception("Ingestion failed for job %s", job_id)
        raise
