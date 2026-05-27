# 文件路径：services/dialogue_extractor.py
import os
import sys
import re
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.prompts import DIALOGUE_STRUCTURE_PROMPT
from core_clients.llm_client import UnifiedLLMClient

class DialogueExtractorService:
    """
    话务结构化盲提炼组件 (纯粹积木)
    输入：对话纯文本
    输出：包含 raw_extraction (草稿) 和 core_question (核心问题) 的字典
    """
    def __init__(self):
        self.llm = UnifiedLLMClient(model_type="text")
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