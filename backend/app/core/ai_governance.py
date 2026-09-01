"""Cross-provider AI governance primitives: redaction, rate limit and circuit breaker."""
import re
import time
from .cache import increment, get, set, delete

SENSITIVE = re.compile(r"(password|passwd|secret|token|api[_-]?key|phone|mobile|email|身份证|证件|住址|address)", re.I)
PII_PATTERNS = (
    (re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)"), "[REDACTED_PHONE]"),
    (re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b"), "[REDACTED_EMAIL]"),
    (re.compile(r"(?<!\d)\d{17}[\dXx](?!\w)"), "[REDACTED_ID]"),
)

class RateLimitExceeded(Exception): pass
class CircuitOpen(Exception): pass

def redact(value, *, max_chars=12000, key=""):
    if SENSITIVE.search(key): return "[REDACTED]"
    if isinstance(value, dict): return {k: redact(v, max_chars=max_chars, key=str(k)) for k, v in value.items()}
    if isinstance(value, list): return [redact(v, max_chars=max_chars, key=key) for v in value[:100]]
    text = str(value) if value is not None else ""
    text = re.sub(r"(?i)(sk-[A-Za-z0-9_-]{12,})", "[REDACTED_KEY]", text)
    # Also protect values after sensitive keys in serialized JSON/dict-like prompts.
    text = re.sub(r"(?i)(['\"]?(?:password|passwd|secret|token|api[_-]?key|phone|mobile|email|address|身份证|证件|住址)['\"]?\s*[:=]\s*)['\"]?[^,}\]\n]+", r"\1[REDACTED]", text)
    for pattern, replacement in PII_PATTERNS:
        text = pattern.sub(replacement, text)
    return text[:max_chars]

def outbound_payload(payload, allowed_fields):
    """Apply an explicit top-level outbound contract before recursive redaction."""
    if not isinstance(payload, dict): return redact(payload)
    return redact({key: payload[key] for key in allowed_fields if key in payload})

def allow(key, limit, window=60):
    bucket = int(time.time() // window)
    if increment(f"ai:rate:{key}:{bucket}", ttl=window + 1) > max(1, limit):
        raise RateLimitExceeded("AI rate limit exceeded")

def before_call(provider, threshold=5, recovery=30):
    if get(f"ai:circuit:open:{provider}"):
        raise CircuitOpen("AI circuit is open")

def mark_success(provider):
    delete(f"ai:circuit:failures:{provider}")
    delete(f"ai:circuit:open:{provider}")

def mark_failure(provider, threshold=5, recovery=30):
    failures = increment(f"ai:circuit:failures:{provider}", ttl=recovery)
    if failures >= max(1, threshold): set(f"ai:circuit:open:{provider}", True, ttl=recovery)
