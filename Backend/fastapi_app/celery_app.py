import logging
from celery import Celery
import redis
from fastapi_app.core.config import CELERY_BROKER_URL, CELERY_RESULT_BACKEND, USE_CELERY

logger = logging.getLogger(__name__)

# Initialize Celery app
celery_app = Celery(
    "demand_forecast",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC"
)

# Graceful fallback: If USE_CELERY is False or Redis server is not reachable,
# configure Celery to run tasks in eager (synchronous) mode on the calling thread.
is_redis_up = False
if USE_CELERY:
    try:
        r = redis.from_url(CELERY_BROKER_URL, socket_connect_timeout=1)
        r.ping()
        is_redis_up = True
    except Exception as e:
        logger.warning(
            f"Redis broker at {CELERY_BROKER_URL} is unreachable ({str(e)}). "
            "Celery will fall back to eager (synchronous) execution mode."
        )

if not USE_CELERY or not is_redis_up:
    celery_app.conf.update(
        task_always_eager=True,
        task_eager_propagates=True
    )
    logger.info("Celery initialized in EAGER (synchronous fallback) mode.")
else:
    logger.info("Celery initialized in ASYNCHRONOUS mode.")

# Discover tasks under fastapi_app/tasks/
celery_app.autodiscover_tasks(["fastapi_app.tasks"])
