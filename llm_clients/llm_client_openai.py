# 文件路径：core_clients/llm_client.py
import os
from openai import OpenAI, default_headers
from core import settings, config

class UnifiedLLMClient:
    """
    统一大模型通信底座 (LLM / VLM Client)
    """
    def __init__(self, model_type="text", base_url=None, api_key=None, model_name=None, temperature=None):
        self.model_type = model_type
        
        # 自动路由到底座配置 (优先使用传入的动态参数，如果没有则读取 settings 兜底)
        if model_type == "text":
            self.base_url = base_url or getattr(settings, "TEXT_LLM_URL", "http://localhost:8000/v1")
            self.api_key = api_key or getattr(settings, "TEXT_LLM_KEY", "dummy")
            self.model_name = model_name or getattr(settings, "TEXT_MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct-AWQ")
        elif model_type == "vision":
            self.base_url = base_url or getattr(settings, "VL_LLM_URL", "http://localhost:8002/v1")
            self.api_key = api_key or getattr(settings, "VL_LLM_KEY", "dummy")
            self.model_name = model_name or getattr(settings, "VL_MODEL_NAME", "Qwen/Qwen2.5-VL-32B-Instruct-AWQ")
        else:
            raise ValueError(f"不支持的模型类型: {model_type}")

        # 设置 temperature (注意 0.0 也是有效值，需用 is not None 判断)
        self.temperature = temperature if temperature is not None else 0.1

        custom_headers = {}
        if getattr(settings, "SYSTEM_CODE", None):
            custom_headers["x-system-code"] = settings.SYSTEM_CODE

        self.client = OpenAI(
            base_url=self.base_url,
            api_key=self.api_key
        )

    def chat_text(self, prompt: str, system_prompt: str = "") -> str:
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=self.temperature  # 👇 使用实例的动态参数
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
                temperature=self.temperature  # 👇 使用实例的动态参数
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"[LLM Client] ❌ 视觉请求异常: {e}")
            return ""