# 文件路径：services/vision_qa_extractor.py
import os
import base64
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from llm_clients.llm_client import UnifiedLLMClient

class VisionQAExtractorService:
    """
    视觉模型通信代理
    职责：只负责 Multimodal LLM 的 Request/Response。
    """
    def __init__(self):
        self.llm = UnifiedLLMClient(model_type="vision")
        # 从配置层加载 Prompt
        from config.prompts import VISION_EXTRACT_PROMPT
        self.system_prompt = VISION_EXTRACT_PROMPT["system"]
        self.user_template = VISION_EXTRACT_PROMPT["user_template"]

    def chat_vision_chunk(self, text_content: str, image_base64: str = "") -> str:
        """输入内容，返回模型原始输出字符串"""
        prompt = self.user_template.format(text_content=text_content)
        if image_base64:
            return self.llm.chat_vision(image_base64=image_base64, prompt=prompt, system_prompt=self.system_prompt)
        return self.llm.chat_text(prompt=prompt, system_prompt=self.system_prompt)

    @staticmethod
    def encode_local_image(image_path: str) -> str:
        if not os.path.exists(image_path): return ""
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode('utf-8')