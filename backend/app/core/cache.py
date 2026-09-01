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
