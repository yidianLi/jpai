"""Optional Redis cache with bounded in-process fallback."""
import json, time
from threading import Lock
from ..config import settings
_memory, _lock, _redis = {}, Lock(), None
try:
    if settings.REDIS_URL:
        import redis
        _redis = redis.from_url(settings.REDIS_URL, decode_responses=True)
except Exception: _redis = None
def get(key):
    if _redis:
        try:
            value = _redis.get(key); return json.loads(value) if value else None
        except Exception: pass
    with _lock:
        item = _memory.get(key)
        if not item or item[0] <= time.time(): _memory.pop(key, None); return None
        return item[1]
def set(key, value, ttl=30):
    if _redis:
        try: _redis.setex(key, ttl, json.dumps(value, ensure_ascii=False, default=str)); return
        except Exception: pass
    with _lock: _memory[key] = (time.time() + ttl, value)

def increment(key, ttl=60):
    """Atomically increment a short-lived counter."""
    if _redis:
        try:
            value = _redis.incr(key)
            if value == 1: _redis.expire(key, ttl)
            return int(value)
        except Exception: pass
    with _lock:
        now = time.time(); item = _memory.get(key)
        value = int(item[1]) + 1 if item and item[0] > now else 1
        _memory[key] = (now + ttl, value)
        return value

def delete(key):
    if _redis:
        try: _redis.delete(key); return
        except Exception: pass
    with _lock: _memory.pop(key, None)
