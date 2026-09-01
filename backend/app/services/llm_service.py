"""
大模型服务（支持本地Ollama和线上OpenAI兼容接口）
原则：大模型只做理解和表达，不做计算和判定
所有数字由后端规则引擎算出，大模型负责组织语言
"""
import json
import logging
import httpx
import os
from urllib.parse import urlparse
import ipaddress
import asyncio
import time
from datetime import datetime
from ..config import settings
from ..database import AiSessionLocal
from ..models.report import AiConfig
from ..models.ai_governance import AiUsageLog
from ..core.ai_governance import redact, outbound_payload, allow, before_call, mark_success, mark_failure, RateLimitExceeded, CircuitOpen
from ..core.request_context import request_id_var

logger = logging.getLogger(__name__)


class LLMService:
    def __init__(self):
        runtime_config = self._load_runtime_config()
        self.provider = runtime_config["provider"]
        self.enabled = runtime_config["enabled"]
        if self.provider == "openai":
            self.base_url = runtime_config["base_url"].rstrip("/")
            self.api_key = runtime_config["api_key"]
            self.model = runtime_config["model"]
        else:
            self.base_url = runtime_config["base_url"].rstrip("/")
            self.api_key = ""
            self.model = runtime_config["model"]
        self.last_error = ""
        self._validate_endpoint()

    def _validate_endpoint(self):
        parsed = urlparse(self.base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            self.enabled = False
            self.last_error = "invalid AI endpoint"
            return
        if self.provider == "openai" and parsed.scheme != "https":
            self.enabled = False
            self.last_error = "online AI endpoint must use HTTPS"
            return
        try:
            address = ipaddress.ip_address(parsed.hostname)
            if self.provider == "openai" and (address.is_private or address.is_loopback or address.is_link_local):
                self.enabled = False
                self.last_error = "private AI endpoint is not allowed"
        except ValueError:
            if self.provider == "openai" and parsed.hostname in {"localhost", "host.docker.internal"}:
                self.enabled = False
                self.last_error = "local AI endpoint is not allowed for online provider"

    @staticmethod
    def _load_runtime_config():
        """数据库配置优先，未配置时回退到环境变量。"""
        values = {}
        db = AiSessionLocal()
        try:
            values = {row.config_key: row.config_value for row in db.query(AiConfig).filter(
                AiConfig.config_key.in_(["ai_provider", "ai_enabled", "ai_base_url", "ai_api_key", "ai_model"])
            ).all()}
        except Exception as exc:
            logger.warning("读取AI运行配置失败，使用环境变量: %s", exc)
        finally:
            db.close()
        provider = os.getenv("LLM_PROVIDER") or settings.LLM_PROVIDER or values.get("ai_provider")
        env_base = os.getenv("OPENAI_API_BASE") if provider == "openai" else os.getenv("OLLAMA_BASE_URL")
        env_key = os.getenv("OPENAI_API_KEY")
        env_model = os.getenv("OPENAI_MODEL") if provider == "openai" else os.getenv("OLLAMA_MODEL")
        return {
            "provider": provider if provider in ("openai", "ollama") else settings.LLM_PROVIDER,
            "enabled": (os.getenv("LLM_ENABLED") or values.get("ai_enabled", str(settings.LLM_ENABLED))).lower() == "true",
            "base_url": env_base or (settings.OPENAI_API_BASE if provider == "openai" else settings.OLLAMA_BASE_URL) or values.get("ai_base_url", ""),
            "api_key": env_key or settings.OPENAI_API_KEY or values.get("ai_api_key", ""),
            "model": env_model or (settings.OPENAI_MODEL if provider == "openai" else settings.OLLAMA_MODEL) or values.get("ai_model", ""),
        }
    async def chat(self, prompt: str, system_prompt: str = None, temperature: float = 0.3, operation: str = "chat", user_id: int = None) -> str:
        """调用大模型（自动适配本地/线上）"""
        started = time.monotonic(); safe_prompt = redact(prompt, max_chars=settings.AI_INPUT_MAX_CHARS)
        if not self.enabled:
            self._record_usage(user_id, operation, "skipped", 0, 0, "AI_DISABLED", safe_prompt, started)
            return ""
        if self.provider == "openai" and not self.api_key:
            logger.warning("OpenAI API Key未配置，LLM功能降级")
            self._record_usage(user_id, operation, "skipped", 0, 0, "API_KEY_MISSING", safe_prompt, started)
            return ""
        try:
            allow(f"{self.provider}:{user_id or 'system'}", settings.AI_RATE_LIMIT_PER_MINUTE)
            before_call(self.provider, settings.AI_CIRCUIT_FAILURE_THRESHOLD, settings.AI_CIRCUIT_RECOVERY_SECONDS)
            messages = ([{"role": "system", "content": redact(system_prompt, max_chars=settings.AI_INPUT_MAX_CHARS)}] if system_prompt else [])
            messages.append({"role": "user", "content": safe_prompt})
            data = None
            for attempt in range(max(0, settings.AI_MAX_RETRIES) + 1):
                try:
                    async with httpx.AsyncClient(timeout=60.0) as client:
                        if self.provider == "openai":
                            resp = await client.post(f"{self.base_url}/chat/completions", headers={"Authorization": f"Bearer {self.api_key}"}, json={"model": self.model, "messages": messages, "temperature": temperature, "stream": False})
                        else:
                            resp = await client.post(f"{self.base_url}/api/chat", json={"model": self.model, "messages": messages, "stream": False, "options": {"temperature": temperature}})
                        resp.raise_for_status(); data = resp.json(); break
                except Exception:
                    if attempt >= settings.AI_MAX_RETRIES: raise
                    await asyncio.sleep(0.2 * (2 ** attempt))
            mark_success(self.provider)
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "") if self.provider == "openai" else data.get("message", {}).get("content", "")
            usage = data.get("usage", {}) or {}
            inp = int(usage.get("prompt_tokens", data.get("prompt_eval_count", 0)) or 0) or max(1, len(safe_prompt) // 4)
            out = int(usage.get("completion_tokens", data.get("eval_count", 0)) or 0) or max(1, len(content) // 4)
            self._record_usage(user_id, operation, "success", inp, out, None, safe_prompt, started)
            return content
        except (RateLimitExceeded, CircuitOpen) as e:
            self.last_error = str(e); self._record_usage(user_id, operation, "blocked", 0, 0, type(e).__name__, safe_prompt, started); return ""
        except Exception as e:
            self.last_error = str(e)
            mark_failure(self.provider, settings.AI_CIRCUIT_FAILURE_THRESHOLD, settings.AI_CIRCUIT_RECOVERY_SECONDS)
            self._record_usage(user_id, operation, "failed", 0, 0, type(e).__name__, safe_prompt, started)
            logger.error(f"LLM调用失败({self.provider}): {e}")
            return ""

    def _record_usage(self, user_id, operation, status, input_tokens, output_tokens, error_code, prompt, started):
        db = None
        try:
            db = AiSessionLocal()
            db.add(AiUsageLog(user_id=user_id, provider=self.provider, model=self.model, operation=operation, status=status,
                              request_id=request_id_var.get(),
                              input_tokens=input_tokens, output_tokens=output_tokens,
                              cost=input_tokens / 1000 * settings.AI_COST_INPUT_PER_1K + output_tokens / 1000 * settings.AI_COST_OUTPUT_PER_1K,
                              latency_ms=int((time.monotonic() - started) * 1000), error_code=error_code,
                              redacted_input=prompt, created_at=datetime.now()))
            db.commit()
        except Exception as exc:
            if db: db.rollback()
            logger.warning("AI usage audit unavailable: %s", exc)
        finally:
            if db: db.close()

    async def nl_query(self, user_query: str, context: dict, user_id: int = None) -> dict:
        """
        自然语言查询：意图识别 + 模板匹配（不直接生成SQL）
        返回匹配的查询模板和参数
        """
        system = """你是固定资产管理系统的查询助手。请分析用户问题，判断查询意图和提取参数。
        支持的查询类型：
        - count: 统计数量（如"有多少台笔记本"）
        - list: 查询明细（如"列出闲置的电脑"）
        - rank: 排名对比（如"哪个部门资产最多"）
        - trend: 趋势分析（如"今年采购了多少"）
        - value: 价值统计（如"总资产价值多少"）

        请以JSON格式返回：{"intent": "查询类型", "filters": {"分类": "", "部门": "", "状态": "", "时间范围": ""}, "answer_hint": "回答要点"}
        只返回JSON，不要其他文字。"""

        safe = outbound_payload({"user_query": user_query, "classes": context.get("classes", []), "depts": context.get("depts", []), "states": context.get("states", []), "conversation": context.get("conversation", [])}, {"user_query", "classes", "depts", "states", "conversation"})
        prompt = f"用户问题与允许外发的上下文：{json.dumps(safe, ensure_ascii=False)}"
        result = await self.chat(prompt, system, operation="nl_query", user_id=user_id)
        try:
            start = result.find("{")
            end = result.rfind("}") + 1
            if start >= 0 and end > start:
                parsed = json.loads(result[start:end])
                parsed["model_used"] = True
                parsed["model_error"] = ""
                return parsed
        except Exception as e:
            logger.error(f"NL查询解析失败: {e}, result: {result}")
        return {"intent": "unknown", "filters": {}, "answer_hint": "",
                "model_used": bool(result), "model_error": self.last_error}

    async def polish_report(self, report_data: dict) -> str:
        """用大模型润色报告文字"""
        system = "你是机关单位公文写作助手，请根据数据生成简洁、正式、客观的分析文字，不要夸大，不要用感叹号。"
        allowed = {"period", "asset_count", "asset_value", "idle_count", "idle_rate", "repair_count", "scrap_count", "department_summary", "class_summary"}
        prompt = f"请根据以下固定资产数据生成一段分析文字（300字以内）：\n{json.dumps(outbound_payload(report_data, allowed), ensure_ascii=False)}"
        return await self.chat(prompt, system, temperature=0.5, operation="report_polish")

    async def classify_asset(self, asset_info: str, standard_names: list) -> str:
        """资产名称智能归类"""
        system = "你是资产分类助手。根据资产描述，从给定的标准名称列表中选择最匹配的一项，只返回名称。"
        safe = outbound_payload({"asset_description": asset_info, "standard_names": standard_names[:50]}, {"asset_description", "standard_names"})
        prompt = f"允许外发的分类信息：{json.dumps(safe, ensure_ascii=False)}"
        return await self.chat(prompt, system, temperature=0.1, operation="asset_classify")

    def check_health(self) -> dict:
        """检查大模型服务状态"""
        if not self.enabled:
            return {"status": "disabled", "provider": self.provider}
        if self.provider == "openai":
            if not self.api_key:
                return {"status": "no_api_key", "provider": "openai", "model": self.model,
                        "message": "请在config.py或.env中配置OPENAI_API_KEY"}
            return {"status": "configured", "provider": "openai", "model": self.model,
                    "base_url": self.base_url}
        else:
            try:
                import requests
                resp = requests.get(f"{self.base_url}/api/tags", timeout=5)
                if resp.status_code == 200:
                    models = [m["name"] for m in resp.json().get("models", [])]
                    return {"status": "ok", "provider": "ollama", "models": models,
                            "model_loaded": self.model in models}
                return {"status": "error", "message": f"HTTP {resp.status_code}"}
            except Exception as e:
                return {"status": "offline", "provider": "ollama", "message": str(e)}
