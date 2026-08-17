import logging
import time
import redis
from fastapi_app.core.config import REDIS_URL

logger = logging.getLogger(__name__)


class RedisClient:
    def __init__(self):
        self.url = REDIS_URL
        self._client = None
        self._is_available = True
        self._last_retry = 0
        self._retry_interval = 60  # Try to reconnect after 60 seconds if Redis goes down
        self._local_cache = {}     # In-memory backup dictionary

    @property
    def client(self):
        now = time.time()
        # If we marked Redis as unavailable, check if enough time has passed to retry connecting
        if not self._is_available and (now - self._last_retry) > self._retry_interval:
            self._is_available = True
            self._client = None
            logger.info("Retrying connection to Redis server...")

        if self._client is None and self._is_available:
            try:
                # Use a short timeout so we don't block requests if Redis is unresponsive
                self._client = redis.from_url(self.url, decode_responses=True, socket_connect_timeout=1)
                self._client.ping()
                logger.info("Connected to Redis successfully")
            except Exception as e:
                logger.warning(f"Could not connect to Redis: {str(e)}. Falling back to local in-memory store.")
                self._client = None
                self._is_available = False
                self._last_retry = now
        return self._client

    def is_available(self) -> bool:
        return self.client is not None

    def get(self, key: str) -> str | None:
        try:
            c = self.client
            if c:
                return c.get(key)
        except Exception as e:
            logger.warning(f"Redis get error: {str(e)}")
            self._client = None
            self._is_available = False
            self._last_retry = time.time()
        return self._local_cache.get(key)

    def set(self, key: str, value: str, ex: int | None = None) -> bool:
        try:
            c = self.client
            if c:
                return bool(c.set(key, value, ex=ex))
        except Exception as e:
            logger.warning(f"Redis set error: {str(e)}")
            self._client = None
            self._is_available = False
            self._last_retry = time.time()
        self._local_cache[key] = value
        return True

    def delete(self, key: str) -> bool:
        try:
            c = self.client
            if c:
                return bool(c.delete(key))
        except Exception as e:
            logger.warning(f"Redis delete error: {str(e)}")
            self._client = None
            self._is_available = False
            self._last_retry = time.time()
        if key in self._local_cache:
            del self._local_cache[key]
            return True
        return False

    def incr(self, key: str) -> int:
        try:
            c = self.client
            if c:
                return c.incr(key)
        except Exception as e:
            logger.warning(f"Redis incr error: {str(e)}")
            self._client = None
            self._is_available = False
            self._last_retry = time.time()
        
        # Fallback counter
        current = self._local_cache.get(key, 0)
        try:
            current = int(current)
        except ValueError:
            current = 0
        new_val = current + 1
        self._local_cache[key] = new_val
        return new_val

    def expire(self, key: str, seconds: int) -> bool:
        try:
            c = self.client
            if c:
                return bool(c.expire(key, seconds))
        except Exception as e:
            logger.warning(f"Redis expire error: {str(e)}")
            self._client = None
            self._is_available = False
            self._last_retry = time.time()
        return True


redis_client = RedisClient()


# ============================================================================
# CACHING DECORATOR
# ============================================================================

from functools import wraps
from fastapi.encoders import jsonable_encoder
import json

def cache_response(expire_seconds: int = 300):
    """
    FastAPI Route Cache Decorator.
    Caches the serializable JSON output of endpoint functions in Redis.
    Falls back gracefully to direct database calls if Redis is unavailable.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not redis_client.is_available():
                return func(*args, **kwargs)

            # Generate unique cache key based on function name & query parameters
            # Exclude db connection and user dependencies
            key_parts = [func.__name__]
            for k, v in sorted(kwargs.items()):
                if k not in ("db", "current_user"):
                    key_parts.append(f"{k}:{v}")
            cache_key = f"cache:{':'.join(key_parts)}"

            try:
                cached = redis_client.get(cache_key)
                if cached:
                    logger.info(f"Redis cache HIT for: {cache_key}")
                    return json.loads(cached)
            except Exception as e:
                logger.warning(f"Failed to read from Redis cache: {str(e)}")

            # Execute database query / service logic
            result = func(*args, **kwargs)

            try:
                # Serialize response (supporting Pydantic models) and write to cache
                serializable = jsonable_encoder(result)
                redis_client.set(cache_key, json.dumps(serializable), ex=expire_seconds)
                logger.info(f"Redis cache SET for: {cache_key} (TTL {expire_seconds}s)")
            except Exception as e:
                logger.warning(f"Failed to write to Redis cache: {str(e)}")

            return result
        return wrapper
    return decorator

