# 文件路径：llm_clients/llm_client.py
import requests
from core import settings

class UnifiedLLMClient:
    """
    统一大模型通信底座 (LLM / VLM Client) - 严格遵循大模型智能应用服务接口规范V1.5
    """
    def __init__(self, model_type="text", base_url=None, api_key=None, model_name=None, temperature=None):
        self.model_type = model_type
        
        # 自动路由到底座配置 (规范定义了各自独立的完整路径命名空间)
        if model_type == "text":
            # 语义大模型完整接口地址（规范表 1.5），由 settings 或调用方直接配置
            self.url = base_url or settings.TEXT_LLM_URL
            self.api_key = api_key or getattr(settings, "TEXT_LLM_KEY", "dummy")
            self.model_name = model_name or getattr(settings, "TEXT_MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct-AWQ")
            self.default_temperature = 0.95  # 规范表 1.5 默认值为 0.95
        elif model_type == "vision":
            # 多模态大模型完整接口地址（规范表 1.16），由 settings 或调用方直接配置
            self.url = base_url or settings.VL_LLM_URL
            self.api_key = api_key or getattr(settings, "VL_LLM_KEY", "dummy")
            self.model_name = model_name or getattr(settings, "VL_MODEL_NAME", "Qwen/Qwen2.5-VL-32B-Instruct-AWQ")
            self.default_temperature = 0.9   # 规范表 1.16 默认值为 0.9
        else:
            raise ValueError(f"不支持的模型类型: {model_type}")

        # 设置 temperature (严格遵循规范推荐的默认值与有效性判断)
        self.temperature = temperature if temperature is not None else self.default_temperature

        # 严格构建符合规范表 1.1 要求的公共请求头
        self.headers = {
            "Content-Type": "application/json;charset=utf-8",
            "Authorization": self.api_key,  # 规范要求：直接存放 APP_KEY，绝不能携带 'Bearer ' 前缀
        }

    def chat_text(self, prompt: str, system_prompt: str = "") -> str:
        """
        发起一次语义模型对话请求 (遵循规范表1.5 / 表1.6)
        """
        try:
            # 组织 messages，规范表1.6明确指出单条内容为 String
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            # 构建符合规范表1.5的 Payload 结构
            payload = {
                "model": self.model_name,
                "messages": messages,
                "temperature": self.temperature,
                "stream": False
            }

            response = requests.post(self.url, json=payload, headers=self.headers, timeout=60)
            response.raise_for_status()
            res_data = response.json()
            
            # 解析符合规范表1.5/1.7的返回体
            if "choices" in res_data and len(res_data["choices"]) > 0:
                return res_data["choices"][0]["message"]["content"]
            
            # 如果返回了规范定义的通用错误结构，打印日志
            if "code" in res_data and res_data["code"] != "000000":
                print(f"[LLM Client] ❌ 平台返回错误: {res_data.get('message')}({res_data['code']})")
                
            return ""
        except Exception as e:
            print(f"[LLM Client] ❌ 文本请求异常: {e}")
            return ""

    def chat_vision(self, prompt: str, image_base64: str, system_prompt: str = "") -> str:
        """
        发起一次多模态大模型对话请求 (严格遵循规范表1.16 / 表1.17 / 表1.18)
        """
        try:
            # 依据规范表1.17/1.18，多模态的 content 必须是 Array[]，图片键名必须是 image
            user_content = [
                {"type": "text", "text": prompt},
                {"type": "image_base64", "image": f"data:image/jpeg;base64,{image_base64}"}
            ]
            
            messages = []
            if system_prompt:
                # 系统提示词在多模态下也严格采用 Array 包装以确保结构稳健
                messages.append({
                    "role": "system", 
                    "content": [{"type": "text", "text": system_prompt}]
                })
            
            messages.append({"role": "user", "content": user_content})

            # 构建符合规范表1.16的 Payload 结构
            payload = {
                "model": self.model_name,
                "messages": messages,
                "temperature": self.temperature,
                "stream": False
            }

            response = requests.post(self.url, json=payload, headers=self.headers, timeout=60)
            response.raise_for_status()
            res_data = response.json()

            # 解析符合规范表1.16/1.19的返回体
            if "choices" in res_data and len(res_data["choices"]) > 0:
                return res_data["choices"][0]["message"]["content"]
            
            if "code" in res_data and res_data["code"] != "000000":
                print(f"[LLM Client] ❌ 平台返回多模态错误: {res_data.get('message')}({res_data['code']})")
                
            return ""
        except Exception as e:
            print(f"[LLM Client] ❌ 视觉/多模态请求异常: {e}")
            return ""