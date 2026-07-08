# 文件路径：llm_clients/embedding_client.py
import requests
from core import settings

class EmbeddingClient:
    """
    向量特征提取客户端 (Embedding Client)
    严格遵循大模型智能应用服务接口规范 V1.5 公共请求头（表 1.1）。
    规范未单独定义特征模型接口，调用方式与语义大模型接口保持一致。
    """

    def __init__(self, base_url=None, api_key=None, model_name=None):
        # 特征模型完整接口地址，由 settings 或调用方直接配置
        self.url = base_url or settings.EMBEDDING_URL
        self.api_key = api_key or getattr(settings, "EMBEDDING_KEY", "dummy")
        self.model_name = model_name or getattr(settings, "EMBEDDING_MODEL", "Alibaba-NLP/gte-Qwen2-7B-instruct")

        # 严格构建符合规范表 1.1 要求的公共请求头
        self.headers = {
            "Content-Type": "application/json;charset=utf-8",
            "Authorization": self.api_key,  # 规范要求：直接存放 APP_KEY，绝不能携带 'Bearer ' 前缀
        }

    def encode(self, texts: list) -> list:
        """将文本列表转换为特征向量矩阵"""
        if isinstance(texts, str):
            texts = [texts]

        if not texts:
            return []

        try:
            payload = {
                "model": self.model_name,
                "input": texts,
            }

            response = requests.post(self.url, json=payload, headers=self.headers, timeout=120)
            response.raise_for_status()
            res_data = response.json()

            if "data" in res_data and res_data["data"]:
                return [
                    item["embedding"]
                    for item in sorted(res_data["data"], key=lambda x: x.get("index", 0))
                ]

            if res_data.get("code") and res_data["code"] != "000000":
                print(f"[Embedding Client] ❌ 平台返回错误: {res_data.get('message')}({res_data['code']})")

            return []
        except Exception as e:
            print(f"[Embedding Client] ❌ 向量模型请求失败: {e}")
            return []
