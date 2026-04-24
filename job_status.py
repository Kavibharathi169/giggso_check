import json
import os
import logging
import time
from collections import OrderedDict
from threading import Lock
from typing import Any, Dict, Optional

import redis

logger = logging.getLogger(__name__)
LOCAL_JOB_STATUS: "OrderedDict[str, Dict[str, Any]]" = OrderedDict()
_LOCAL_STATUS_LOCK = Lock()
_REDIS_CLIENT: Optional[redis.Redis] = None
_REDIS_LOCK = Lock()


def _local_status_ttl_sec() -> int:
    return int(os.getenv("LOCAL_JOB_STATUS_TTL_SEC", "3600"))


def _local_status_max_items() -> int:
    return int(os.getenv("LOCAL_JOB_STATUS_MAX_ITEMS", "2000"))


def _prune_local_status_locked(now_ts: Optional[float] = None) -> None:
    now = now_ts if now_ts is not None else time.time()
    ttl = _local_status_ttl_sec()
    max_items = _local_status_max_items()

    # Drop expired entries first.
    expired = [job_id for job_id, payload in LOCAL_JOB_STATUS.items() if now - payload.get("_updated_at", now) > ttl]
    for job_id in expired:
        LOCAL_JOB_STATUS.pop(job_id, None)

    # Enforce bounded memory with FIFO eviction.
    while len(LOCAL_JOB_STATUS) > max_items:
        LOCAL_JOB_STATUS.popitem(last=False)


def _redis_client() -> redis.Redis:
    global _REDIS_CLIENT
    if _REDIS_CLIENT is not None:
        return _REDIS_CLIENT

    with _REDIS_LOCK:
        if _REDIS_CLIENT is not None:
            return _REDIS_CLIENT
        redis_url = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")
        _REDIS_CLIENT = redis.Redis.from_url(
            redis_url,
            decode_responses=True,
            socket_timeout=float(os.getenv("REDIS_SOCKET_TIMEOUT_SEC", "1.0")),
            socket_connect_timeout=float(os.getenv("REDIS_CONNECT_TIMEOUT_SEC", "1.0")),
            health_check_interval=int(os.getenv("REDIS_HEALTH_CHECK_INTERVAL_SEC", "30")),
        )
        return _REDIS_CLIENT


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
        local_payload = dict(payload)
        local_payload["_updated_at"] = time.time()
        with _LOCAL_STATUS_LOCK:
            LOCAL_JOB_STATUS[job_id] = local_payload
            LOCAL_JOB_STATUS.move_to_end(job_id, last=True)
            _prune_local_status_locked(local_payload["_updated_at"])


def get_job_status(job_id: str) -> Optional[Dict[str, Any]]:
    try:
        client = _redis_client()
        raw = client.get(_key(job_id))
        if not raw:
            return None
        return json.loads(raw)
    except redis.RedisError:
        logger.warning("Redis unavailable, reading local status for %s", job_id)
        with _LOCAL_STATUS_LOCK:
            _prune_local_status_locked()
            payload = LOCAL_JOB_STATUS.get(job_id)
            if not payload:
                return None
            # Keep frequently queried jobs warm while preserving bounds.
            LOCAL_JOB_STATUS.move_to_end(job_id, last=True)
            cleaned = dict(payload)
            cleaned.pop("_updated_at", None)
            return cleaned
