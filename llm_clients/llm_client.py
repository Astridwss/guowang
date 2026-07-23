import re
import json
import requests
from core import settings

class UnifiedLLMClient:
    """
    统一大模型通信底座 (LLM / VLM Client)
    
    设计与兼容保障：
    1. 函数签名兼容：保留 system_prompt 可选形参，完全对齐 services 层现有调用逻辑，杜绝 TypeError。
    2. 协议结构兼容：内部自动将 system_prompt 融合拼接至 user 内容头部，不增加额外的 system role message 节点，确保 100% 契合严格的网关 JSON 结构要求。
    3. 思考链清洗：底层强力清除 <think>...</think> 推理步骤及 <answer> 标签。
    4. 安全日志记录：自动打印完整请求 Payload，针对多模态 Base64 图片进行截断展示，避免控制台刷屏。
    """
    
    def __init__(self, model_type="text", base_url=None, api_key=None, model_name=None, temperature=None):
        self.model_type = model_type
        
        if model_type == "text":
            self.url = base_url or settings.TEXT_LLM_URL
            self.api_key = api_key or getattr(settings, "TEXT_LLM_KEY", "dummy")
            self.model_name = model_name or getattr(settings, "TEXT_MODEL_NAME", "SGGM-NLP-80B-C")
            self.default_temperature = 0.95
        elif model_type == "vision":
            self.url = base_url or settings.VL_LLM_URL
            self.api_key = api_key or getattr(settings, "VL_LLM_KEY", "dummy")
            self.model_name = model_name or getattr(settings, "VL_MODEL_NAME", "SGGM-VL-8B")
            self.default_temperature = 0.9
        else:
            raise ValueError(f"不支持的模型类型: {model_type}")

        # 确保网关路由 URL 具有统一的尾部斜杠
        if self.url and not self.url.endswith("/"):
            self.url = f"{self.url}/"

        self.temperature = temperature if temperature is not None else self.default_temperature

        self.headers = {
            "Content-Type": "application/json;charset=utf-8",
            "Authorization": self.api_key,
        }

    def _clean_response_content(self, raw_content: str) -> str:
        """
        高可用响应清洗引擎：剥离推理模型的思考链 <think>...</think> 及包裹标记
        """
        if not raw_content:
            return ""
        # 1. 强力清除 <think>...</think> 标签及其包裹的所有推理步骤内容
        clean_text = re.sub(r"<think>.*?</think>", "", raw_content, flags=re.DOTALL)
        # 2. 剥离 <answer> 或 </answer> 标签本身，保留纯粹的回答正文
        clean_text = re.sub(r"</?answer>", "", clean_text, flags=re.IGNORECASE)
        return clean_text.strip()

    def chat_text(self, prompt: str, system_prompt: str = "") -> str:
        """
        发起一次语义模型对话请求
        :param prompt: 用户提问文本
        :param system_prompt: 可选的系统提示词，会自动融合入 user 消息中以保持接口协议结构稳定
        """
        try:
            # 💡【核心融合逻辑】：平铺拼接 system_prompt，既保持网关只包含 user 角色的简单格式，又不丢失系统设定
            if system_prompt and system_prompt.strip():
                combined_content = f"系统指令：{system_prompt.strip()}\n\n用户提问：{prompt.strip()}"
            else:
                combined_content = prompt

            messages = [{"role": "user", "content": combined_content}]

            payload = {
                "model": self.model_name,
                "messages": messages,
                "temperature": self.temperature,
                "stream": False
            }

            # 打印请求调试入参
            print(f"[LLM Client] 📤 chat_text 请求入参:\n{json.dumps(payload, ensure_ascii=False, indent=2)}")

            response = requests.post(self.url, json=payload, headers=self.headers, timeout=60)
            response.raise_for_status()
            res_data = response.json()
            
            if "choices" in res_data and len(res_data["choices"]) > 0:
                raw_content = res_data["choices"][0]["message"]["content"]
                return self._clean_response_content(raw_content)
            
            if "code" in res_data and res_data["code"] != "000000":
                print(f"[LLM Client] ❌ 平台返回错误: {res_data.get('message')}({res_data['code']})")
                
            return ""
        except Exception as e:
            print(f"[LLM Client] ❌ 文本请求异常: {e}")
            return ""

    def chat_vision(self, prompt: str, image_base64: str, system_prompt: str = "") -> str:
        """
        发起一次多模态/视觉大模型对话请求
        :param prompt: 用户文本描述
        :param image_base64: 图片 Base64 文本
        :param system_prompt: 可选的系统提示词
        """
        try:
            # 确保规范的 Base64 格式头
            if image_base64.startswith("data:image"):
                image_value = image_base64
            else:
                image_value = f"data:image/jpeg;base64,{image_base64}"
            
            # 💡【核心融合逻辑】：平铺拼接系统指令到多模态文本节点
            if system_prompt and system_prompt.strip():
                combined_prompt = f"系统指令：{system_prompt.strip()}\n\n用户提问：{prompt.strip()}"
            else:
                combined_prompt = prompt

            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": combined_prompt},
                        {"type": "image_base64", "image": image_value}
                    ]
                }
            ]

            payload = {
                "model": self.model_name,
                "messages": messages,
                "temperature": self.temperature,
                "stream": False
            }

            # 打印日志（针对 Base64 进行截断保护，防止控制台刷屏）
            payload_log = {
                **payload,
                "messages": [
                    {
                        **msg,
                        "content": [
                            {**item, "image": item["image"][:50] + "... (截断)"} 
                            if item.get("type") == "image_base64" else item
                            for item in msg["content"]
                        ]
                    } if isinstance(msg.get("content"), list) else msg
                    for msg in messages
                ]
            }
            print(f"[LLM Client] 📤 chat_vision 请求入参:\n{json.dumps(payload_log, ensure_ascii=False, indent=2)}")

            response = requests.post(self.url, json=payload, headers=self.headers, timeout=60)
            response.raise_for_status()
            res_data = response.json()

            if "choices" in res_data and len(res_data["choices"]) > 0:
                raw_content = res_data["choices"][0]["message"]["content"]
                return self._clean_response_content(raw_content)
            
            if "code" in res_data and res_data["code"] != "000000":
                print(f"[LLM Client] ❌ 平台返回多模态错误: {res_data.get('message')}({res_data['code']})")
                
            return ""
        except Exception as e:
            print(f"[LLM Client] ❌ 视觉/多模态请求异常: {e}")
            return ""