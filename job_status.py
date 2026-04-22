import json
import os
import logging
from typing import Any, Dict, Optional

import redis

logger = logging.getLogger(__name__)
LOCAL_JOB_STATUS: Dict[str, Dict[str, Any]] = {}


def _redis_client() -> redis.Redis:
    redis_url = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")
    return redis.Redis.from_url(redis_url, decode_responses=True)


def _key(job_id: str) -> str:
    return f"ingestion:job:{job_id}"


def set_job_status(job_id: str, status: str, progress: int, message: str, task_id: Optional[str] = None) -> None:
    payload = {
        "status": status,
        "progress": int(progress),
        "message": message,
    }
    if task_id:
        payload["task_id"] = task_id

    try:
        client = _redis_client()
        client.set(_key(job_id), json.dumps(payload), ex=int(os.getenv("JOB_STATUS_TTL_SEC", "86400")))
    except redis.RedisError:
        logger.warning("Redis unavailable, storing job status locally for %s", job_id)
        LOCAL_JOB_STATUS[job_id] = payload


def get_job_status(job_id: str) -> Optional[Dict[str, Any]]:
    try:
        client = _redis_client()
        raw = client.get(_key(job_id))
        if not raw:
            return None
        return json.loads(raw)
    except redis.RedisError:
        logger.warning("Redis unavailable, reading local status for %s", job_id)
        return LOCAL_JOB_STATUS.get(job_id)
