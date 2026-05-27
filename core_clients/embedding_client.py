# 文件路径：core_clients/embedding_client.py
import os
from openai import OpenAI
from config import settings

class EmbeddingClient:
    """
    向量特征提取客户端 (Embedding Client)
    职责：专职调用 GTE 等特征抽取模型 (符合 OpenAI Embeddings API 规范)。
    绝对不包含任何 LLM 文本生成逻辑。
    """
    def __init__(self):
        self.base_url = getattr(settings, "EMBEDDING_URL", "http://localhost:8001/v1")
        self.api_key = getattr(settings, "EMBEDDING_KEY", "dummy")
        self.model_name = getattr(settings, "EMBEDDING_MODEL", "Alibaba-NLP/gte-Qwen2-7B-instruct")
        
        custom_headers = {}
        if getattr(settings, "SYSTEM_CODE", None):
            custom_headers["x-system-code"] = settings.SYSTEM_CODE

        self.client = OpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
            default_headers=custom_headers if custom_headers else None
        )

    def encode(self, texts: list) -> list:
        """将文本列表转换为特征向量矩阵"""
        if isinstance(texts, str):
            texts = [texts]
            
        if not texts:
            return []

        try:
            response = self.client.embeddings.create(
                model=self.model_name,
                input=texts
            )
            # 确保按照输入顺序提取 embedding 向量
            embeddings = [item.embedding for item in sorted(response.data, key=lambda x: x.index)]
            return embeddings
        except Exception as e:
            print(f"[Embedding Client] ❌ 向量模型请求失败: {e}")
            return []