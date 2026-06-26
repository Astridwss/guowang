# 文件路径：services/knowledge_retriever.py
import os
import sys
import numpy as np

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.index_store import IndexStoreService

class KnowledgeRetrieverService:
    """
    在线向量检索与业务裁判组件 (纯粹积木)
    输入：Numpy 向量矩阵 (由流水线调用 VectorEmbeddingService 算好后传入)
    输出：命中阈值的 FAQ 字典，或 None
    """
    def __init__(self, db_dir: str = "database", threshold: float = 0.5):
        self.threshold = threshold
        self.store = IndexStoreService(db_dir=db_dir)
        
        if self.store.load():
            print(f"[RetrieverService] 挂载底座成功，知识条目数: {len(self.store.metadata)}")
        else:
            print(f"[RetrieverService]  找不到向量库 {db_dir}，组件将空转。")

    def retrieve_by_vector(self, query_vector: np.ndarray) -> dict:
        if query_vector is None or not self.store.index:
            return None

        results = self.store.search(query_vector, top_k=1)
        if not results:
            return None
            
        best = results[0]
        if best["similarity"] >= self.threshold:
            print(f"[Retriever] 🎯 命中知识库! 相似度: {best['similarity']:.4f}")
            return best
        
        print(f"[Retriever]  相似度 {best['similarity']:.4f} 低于阈值")
        return best