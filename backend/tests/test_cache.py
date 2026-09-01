import time
from backend.app.core.cache import get, set


def test_memory_cache_ttl():
    set("test:key", {"value": 1}, ttl=1)
    assert get("test:key") == {"value": 1}
    time.sleep(1.05)
    assert get("test:key") is None
