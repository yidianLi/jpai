"""
本地大模型服务（Ollama + Qwen2.5）
原则：大模型只做理解和表达，不做计算和判定
所有数字由后端规则引擎算出，大模型负责组织语言
"""
import json
import logging
import httpx
from ..config import settings

logger = logging.getLogger(__name__)


class LLMService:
    def __init__(self):
        self.base_url = settings.OLLAMA_BASE_URL
        self.model = settings.OLLAMA_MODEL
        self.enabled = settings.LLM_ENABLED

    async def chat(self, prompt: str, system_prompt: str = None, temperature: float = 0.3) -> str:
        """调用本地大模型"""
        if not self.enabled:
            return ""
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    f"{self.base_url}/api/chat",
                    json={"model": self.model, "messages": messages,
                          "stream": False, "options": {"temperature": temperature}}
                )
                resp.raise_for_status()
                data = resp.json()
                return data.get("message", {}).get("content", "")
        except Exception as e:
            logger.error(f"LLM调用失败: {e}")
            return ""

    async def nl_query(self, user_query: str, context: dict) -> dict:
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

        prompt = f"用户问题：{user_query}\n可用上下文：{json.dumps(context, ensure_ascii=False)}"
        result = await self.chat(prompt, system)
        try:
            # 提取JSON
            start = result.find("{")
            end = result.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(result[start:end])
        except Exception as e:
            logger.error(f"NL查询解析失败: {e}, result: {result}")
        return {"intent": "unknown", "filters": {}, "answer_hint": ""}

    async def polish_report(self, report_data: dict) -> str:
        """用大模型润色报告文字"""
        system = "你是机关单位公文写作助手，请根据数据生成简洁、正式、客观的分析文字，不要夸大，不要用感叹号。"
        prompt = f"请根据以下固定资产数据生成一段分析文字（300字以内）：\n{json.dumps(report_data, ensure_ascii=False)}"
        return await self.chat(prompt, system, temperature=0.5)

    async def classify_asset(self, asset_info: str, standard_names: list) -> str:
        """资产名称智能归类（向量匹配更准，这里用大模型做备选）"""
        system = "你是资产分类助手。根据资产描述，从给定的标准名称列表中选择最匹配的一项，只返回名称。"
        prompt = f"资产描述：{asset_info}\n标准名称列表：{', '.join(standard_names[:50])}"
        return await self.chat(prompt, system, temperature=0.1)

    def check_ollama_health(self) -> dict:
        """检查Ollama服务状态"""
        try:
            import requests
            resp = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if resp.status_code == 200:
                models = [m["name"] for m in resp.json().get("models", [])]
                return {"status": "ok", "models": models, "model_loaded": self.model in models}
            return {"status": "error", "message": f"HTTP {resp.status_code}"}
        except Exception as e:
            return {"status": "offline", "message": str(e)}
