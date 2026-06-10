# 文件路径：services/data_desensitizer.py
import os
import sys
import re
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.prompts import DESENSITIZE_PROMPT
from llm_clients.llm_client import UnifiedLLMClient

class DataDesensitizerService:
    """
    脱敏过滤组件 (纯粹积木)
    输入：任意结构化或非结构化文本rawASR.xlsx
    输出：安全文本及映射字典
    """
    def __init__(self):
        self.llm = UnifiedLLMClient(model_type="text")
        self.sys_prompt = DESENSITIZE_PROMPT.get("system", "")
        self.user_tpl = DESENSITIZE_PROMPT["user_template"]

    def process(self, raw_text: str) -> dict:
        if not raw_text:
            return {"safe_text": "", "mappings": {}}

        prompt = self.user_tpl.format(raw_text=raw_text)
        resp = self.llm.chat_text(prompt=prompt, system_prompt=self.sys_prompt)
        return self._parse_mappings(resp)

    def _parse_mappings(self, text: str) -> dict:
        if not text:
            return {"safe_text": "", "mappings": {}}

        safe_text = ""
        mappings = {}
        for line in text.split("\n"):
            line = line.strip()
            if line.startswith("[") and "=" in line:
                m = re.match(r"\[([^\]]+)\]\s*=\s*(.+)", line)
                if m: mappings[m.group(1).strip()] = m.group(2).strip()
            elif not line.startswith("输出：") and not line.startswith("样例"):
                safe_text += (line + "\n")
                
        if not safe_text.strip():
            m = re.search(r"输出：\s*(.*?)(?=\n\[|$)", text, flags=re.DOTALL)
            if m: safe_text = m.group(1).strip()

        return {"safe_text": safe_text.strip(), "mappings": mappings}