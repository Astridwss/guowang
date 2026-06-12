# 文件路径：services/vision_qa_extractor.py
import os
import base64
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.prompts import VISION_EXTRACT_PROMPT
from llm_clients.llm_client import UnifiedLLMClient

class VisionQAExtractorService:
    """
    视觉大模型多模态通信积木
    职责：专职负责与多模态大模型进行 Request/Response 交互，解析图文混合切片。
    """
    def __init__(self, base_url=None, api_key=None, model_name=None):
        self.llm = UnifiedLLMClient(
            base_url=base_url,
            api_key=api_key,
            model_name=model_name
        )
        # 从全局 prompts.py 中动态加载标准国产化 ERP 提示词
        self.system_prompt = VISION_EXTRACT_PROMPT["system"]
        self.user_template = VISION_EXTRACT_PROMPT["user_template"]

    def extract_qa_from_chunk(self, chunk: list, img_dir: str) -> str:
        """
        核心方法：接收自上游物理切片积木输出的混合列表，自动转化为大模型所需的标准多模态入参。
        """
        text_lines = []
        image_filename = None

        # 1. 自动解析并组装当前切片里的所有文本和图片要素
        for element in chunk:
            if element["type"] == "text":
                text_lines.append(element["text"])
            elif element["type"] == "image":
                # 记录图片文件名（多模态大模型单次请求通常建议处理一张核心操作截图）
                image_filename = element["image"]

        full_text_content = "\n".join(text_lines)

        # 2. 如果切片里带有图片，自动读取并转化成绝对安全的 Base64 字符串
        image_base64 = ""
        if image_filename:
            full_img_path = os.path.join(img_dir, image_filename)
            image_base64 = self.encode_local_image(full_img_path)

        # 3. 驱动底层统一大模型客户端，进行智能提炼
        return self.chat_vision_chunk(full_text_content, image_base64)

    def chat_vision_chunk(self, text_content: str, image_base64: str = "") -> str:
        """纯净包装：输入内容，返回模型原始输出字符串"""
        prompt = self.user_template.format(text_content=text_content)
        if image_base64:
            return self.llm.chat_vision(image_base64=image_base64, prompt=prompt, system_prompt=self.system_prompt)
        return self.llm.chat_text(prompt=prompt, system_prompt=self.system_prompt)

    @staticmethod
    def encode_local_image(image_path: str) -> str:
        """静态工具：本地图片高并发安全转码 base64"""
        if not os.path.exists(image_path): 
            return ""
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode('utf-8')