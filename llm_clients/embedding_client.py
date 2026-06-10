# 文件路径：core_clients/embedding_client.py
import os
from openai import OpenAI
from core import settings, config

class EmbeddingClient:
    """
    向量特征提取客户端 (Embedding Client)
    """
    # 👇 增加动态参数接收口
    def __init__(self, base_url=None, api_key=None, model_name=None):
        # 优先使用动态参数，否则降级回 settings 读取
        self.base_url = base_url or getattr(settings, "EMBEDDING_URL", "http://localhost:8001/v1")
        self.api_key = api_key or getattr(settings, "EMBEDDING_KEY", "dummy")
        self.model_name = model_name or getattr(settings, "EMBEDDING_MODEL", "Alibaba-NLP/gte-Qwen2-7B-instruct")
        
        custom_headers = {}
        if getattr(settings, "SYSTEM_CODE", None):
            custom_headers["x-system-code"] = settings.SYSTEM_CODE

        self.client = OpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
            default_headers=config.GLOBAL_HEADERS
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