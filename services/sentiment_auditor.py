# 文件路径：services/sentiment_auditor.py
import os
import sys
import re
import json
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.prompts import SENTIMENT_PROMPT
from llm_clients.llm_client import UnifiedLLMClient

class SentimentAuditorService:
    """
    情感质检组件 (纯粹积木)
    输入：对话文本
    输出：打分结果字典
    """
    def __init__(self):
        self.llm = UnifiedLLMClient(model_type="text")
        self.sys_prompt = SENTIMENT_PROMPT.get("system", "")
        self.user_tpl = SENTIMENT_PROMPT["user_template"]

    def process(self, dialogue_text: str) -> dict:
        if not dialogue_text:
            return {"score": 60, "sentiment": "中性", "key_points": [], "suggestions": "无内容"}

        prompt = self.user_tpl.format(raw_text=dialogue_text)
        
        for _ in range(3):
            resp = self.llm.chat_text(prompt=prompt, system_prompt=self.sys_prompt)
            res = self._parse_json(resp)
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