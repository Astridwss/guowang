# 文件路径：services/vector_embedding.py
import os
import sys
import numpy as np

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from llm_clients.embedding_client import EmbeddingClient

class VectorEmbeddingService:
    """
    向量化特征提取服务 (ETL - Transform)
    职责：纯粹的文本到向量的转换，不关心文本从哪来，要到哪去。
    """
    def __init__(self, base_url=None, api_key=None, model_name=None):
        print(f"[VectorEmbeddingService] 初始化向量化引擎 (model={model_name or '默认'})...")
        self.embedder = EmbeddingClient(
            base_url=base_url,
            api_key=api_key,
            model_name=model_name
        )

    def vectorize(self, texts: list) -> np.ndarray:
        """
        将文本列表转换为 FAISS 兼容的 float32 向量矩阵
        """
        if isinstance(texts, str):
            texts = [texts]
        if not texts:
            return np.array([])
            
        print(f"[VectorEmbeddingService] 正在将 {len(texts)} 条文本输入大模型进行向量化计算...")
        vectors = self.embedder.encode(texts)
        
        return np.array(vectors).astype('float32')