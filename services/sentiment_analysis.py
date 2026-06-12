# 文件路径：services/sentiment_auditor.py
import os
import sys
import re
import json
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.prompts import SENTIMENT_PROMPT
from llm_clients.llm_client import UnifiedLLMClient

class SentimentAnalysisService:
    """
    情感质检组件 (纯粹积木)
    输入：对话文本
    输出：打分结果字典
    """
    def __init__(self, base_url: str = None, api_key: str = None, model_name: str = None):
        # 💡 完美重构：支持直接从 Request 数据模型中解包参数，安全注入大模型客户端，避免全局配置污染
        self.llm = UnifiedLLMClient(
            base_url=base_url,
            api_key=api_key,
            model_name=model_name
        )
        # 从全局 prompts.py 中动态加载标准国产化 ERP 客服质检提示词
        self.system_prompt = SENTIMENT_PROMPT.get("system", "你是一个专业的客服质量与情绪分析专家。")
        self.user_template = SENTIMENT_PROMPT["user_template"]
        
    def process(self, asr_text: str) -> dict:
        if not asr_text:
            return {"score": 60, "sentiment": "中性", "key_points": [], "suggestions": "无内容"}

        prompt = self.user_template.format(raw_text=asr_text)
        
        for _ in range(3):
            response_text = self.llm.chat_text(prompt=prompt, system_prompt=self.system_prompt)
            res = self._parse_json(response_text)
            if res["score"] != -1:
                return res
        return {"score": 60, "sentiment": "解析失败", "key_points": [], "suggestions": "失败"}

    def _parse_json(self, text: str) -> dict:
        if not text: return {"score": -1}
        match = re.search(r"\{.*?\}", text, flags=re.DOTALL)
        if not match: return {"score": -1}
        
        try:
            data = json.loads(match.group(0))
            if isinstance(data, list): data = data[0]
            raw_score = data.get("情感评分", -1)
            if raw_score == -1: return {"score": -1}

            final_score = int(raw_score / 100.0 * 40) + 60
            sentiment = "满意" if final_score >= 80 else ("中性" if final_score >= 60 else "不满意")
            
            return {
                "score": final_score,
                "sentiment": sentiment,
                "key_points": data.get("关键依据", []),
                "suggestions": data.get("改进建议", "无")
            }
        except:
            return {"score": -1}