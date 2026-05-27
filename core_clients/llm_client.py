# 文件路径：core_clients/llm_client.py
import os
from openai import OpenAI
from config import settings

class UnifiedLLMClient:
    """
    统一大模型通信底座 (LLM / VLM Client)
    职责：负责文本大模型和视觉大模型的标准网络请求，不包含任何业务组装逻辑。
    """
    def __init__(self, model_type="text"):
        self.model_type = model_type
        
        # 自动路由到底座配置
        if model_type == "text":
            self.base_url = getattr(settings, "TEXT_LLM_URL", "http://localhost:8000/v1")
            self.api_key = getattr(settings, "TEXT_LLM_KEY", "dummy")
            self.model_name = getattr(settings, "TEXT_MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct-AWQ")
        elif model_type == "vision":
            self.base_url = getattr(settings, "VL_LLM_URL", "http://localhost:8002/v1")
            self.api_key = getattr(settings, "VL_LLM_KEY", "dummy")
            self.model_name = getattr(settings, "VL_MODEL_NAME", "Qwen/Qwen2.5-VL-32B-Instruct-AWQ")
        else:
            raise ValueError(f"不支持的模型类型: {model_type}")

        custom_headers = {}
        if getattr(settings, "SYSTEM_CODE", None):
            custom_headers["x-system-code"] = settings.SYSTEM_CODE

        self.client = OpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
            default_headers=custom_headers if custom_headers else None
        )

    def chat_text(self, prompt: str, system_prompt: str = "") -> str:
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"[LLM Client] ❌ 文本请求异常: {e}")
            return ""

    def chat_vision(self, prompt: str, image_base64: str, system_prompt: str = "") -> str:
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}}
                        ]
                    }
                ],
                temperature=0.1
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"[LLM Client] ❌ 视觉请求异常: {e}")
            return ""