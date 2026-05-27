# 文件路径：services/rag_synthesizer.py
import os
import sys
import re
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.prompts import DIALOGUE_STRUCTURE_PROMPT
from core_clients.llm_client import UnifiedLLMClient

class RAGSynthesizerService:
    """
    RAG 融合裁判组件 (纯粹积木)
    输入：原始对话文本、初始草稿、命中的标准 FAQ 字典
    输出：最终二次修正后的结构化业务文本
    """
    def __init__(self):
        self.llm = UnifiedLLMClient(model_type="text")
        self.sys_prompt = DIALOGUE_STRUCTURE_PROMPT["system"]
        self.user_tpl = DIALOGUE_STRUCTURE_PROMPT["user_template"]

    def synthesize(self, asr_text: str, initial_extraction: str, matched_faq: dict = None) -> str:
        # 业务逻辑：未命中知识库，直接放行草稿，节省算力
        if not matched_faq:
            return initial_extraction

        faq_context = (
            "\n以下为外部知识库检索到的参考信息："
            f"\nFAQ问题：{matched_faq['question']}"
            f"\nFAQ答案：{matched_faq['answer']}\n"
        )
        prompt = self.user_tpl.format(raw_text=asr_text, faq_context=faq_context)
        response_text = self.llm.chat_text(prompt=prompt, system_prompt=self.sys_prompt)

        if response_text:
            return re.sub(r'<think>.*?</think>', '', response_text, flags=re.DOTALL).strip()
        return initial_extraction