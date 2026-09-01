import pytest
import asyncio
from backend.app.core.ai_governance import redact, outbound_payload, allow, RateLimitExceeded, before_call, mark_failure, CircuitOpen
from backend.app.services.llm_service import LLMService
import backend.app.services.llm_service as llm_module

def test_redact_sensitive_and_bound():
    assert redact({"email": "a@example.com", "name": "ok"})["email"] == "[REDACTED]"
    assert "a@example.com" not in redact('{"email": "a@example.com", "name": "ok"}')
    assert "13800138000" not in redact("联系人 13800138000")
    assert "11010519491231002X" not in redact("证件 11010519491231002X")
    assert len(redact("x" * 20, max_chars=10)) == 10
    assert outbound_payload({"asset_name": "PC", "sn": "secret"}, {"asset_name"}) == {"asset_name": "PC"}

def test_rate_limit_and_circuit():
    key = "test-governance"
    allow(key, 1, window=60)
    with pytest.raises(RateLimitExceeded): allow(key, 1, window=60)
    provider = "test-circuit"
    for _ in range(2): mark_failure(provider, 2)
    with pytest.raises(CircuitOpen): before_call(provider, 2, 60)

def test_retry_is_bounded(monkeypatch):
    calls = {"count": 0}
    class Client:
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def post(self, *args, **kwargs):
            calls["count"] += 1
            raise RuntimeError("offline")
    svc = LLMService.__new__(LLMService)
    svc.enabled = True; svc.provider = "openai"; svc.api_key = "test"; svc.base_url = "https://example.test"; svc.model = "test"; svc.last_error = ""
    svc._record_usage = lambda *args, **kwargs: None
    monkeypatch.setattr(llm_module.httpx, "AsyncClient", lambda **kwargs: Client())
    monkeypatch.setattr(llm_module.settings, "AI_MAX_RETRIES", 2)
    assert asyncio.run(svc.chat("hello", operation="retry_test")) == ""
    assert calls["count"] == 3
