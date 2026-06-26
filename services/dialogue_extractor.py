# 文件路径：services/dialogue_extractor.py
import os
import sys
import re
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.prompts import DIALOGUE_STRUCTURE_PROMPT
from llm_clients.llm_client import UnifiedLLMClient

class DialogueExtractorService:
    """
    话务结构化盲提炼组件 (纯粹积木)
    """
    # 👇 改造点 1：接收平台传来的动态参数，并设置默认值为 None（兼容旧代码）
    def __init__(self, base_url=None, api_key=None, model_name=None, temperature=None):
        # 👇 改造点 2：将参数透传给底层的 LLM 客户端
        self.llm = UnifiedLLMClient(
            model_type="text",
            base_url=base_url,
            api_key=api_key,
            model_name=model_name,
            temperature=temperature
        )
        self.sys_prompt = DIALOGUE_STRUCTURE_PROMPT["system"]
        self.user_tpl = DIALOGUE_STRUCTURE_PROMPT["user_template"]

    def extract(self, asr_text: str) -> dict:
        if not asr_text:
            return {"raw_extraction": "", "core_question": ""}

        prompt = self.user_tpl.format(raw_text=asr_text, faq_context="")
        response_text = self.llm.chat_text(prompt=prompt, system_prompt=self.sys_prompt)
        
        if not response_text:
            return {"raw_extraction": "", "core_question": ""}

        core_q = self._parse_core_question(response_text)
        return {"raw_extraction": response_text, "core_question": core_q}

    def _parse_core_question(self, text: str) -> str:
        '''正则扣出问题'''
        text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()
        match = re.search(r'问题：\s*(.+)', text)
        return match.group(1).strip() if match else ""
    
    def _parse_core_answer(self, text: str) -> str:
        '''正则扣出问题'''
        text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()
        match = re.search(r'答案：\s*(.+)', text)
        return match.group(1).strip() if match else ""