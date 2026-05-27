# 文件路径：services/index_store.py
import os
import faiss
import pickle
import numpy as np

class IndexStoreService:
    """
    向量库索引与存储服务 (彻底合并版)
    职责：
        1、对向量构建索引
        2、将向量存入数据库  这部分只将问题入库了，答案payloads列表被序列化保存在本地metadata.pkl文件了。键值对存储方式，后续可能引入关系数据库
        3、检索（在线话务流转阶段）
    """
    def __init__(self, db_dir: str = "database"):
        self.db_dir = db_dir
        self.dimension = None
        self.index = None
        self.metadata = [] 
        print(f"[IndexStoreService] 向量库服务初始化 (指向目录: {self.db_dir}/)")

    # ==========================================
    # 写入功能 (用于知识库构建流水线)
    # ==========================================
    def build_and_save(self, vectors: np.ndarray, payloads: list) -> bool:
        """布置成增量构建 FAISS 索引并持久化到本地"""
        if len(vectors) == 0 or len(vectors) != len(payloads):
            print("[IndexStoreService]  向量矩阵与载荷长度不匹配或为空，拒绝入库！")
            return False
            
        print(f"[IndexStoreService] 正在构建 {len(payloads)} 条知识的底层 FAISS 索引树...")
        self.dimension = vectors.shape[1]
        self.index = faiss.IndexFlatIP(self.dimension) 
        
        # 向量 L2 归一化后，内积 (IP) 计算等价于余弦相似度计算
        faiss.normalize_L2(vectors)
        self.index.add(vectors)
        self.metadata = payloads

        # 落盘保存
        os.makedirs(self.db_dir, exist_ok=True)
        faiss.write_index(self.index, os.path.join(self.db_dir, "faiss.index"))
        with open(os.path.join(self.db_dir, "metadata.pkl"), "wb") as f:
            pickle.dump({"dim": self.dimension, "meta": self.metadata}, f)
            
        print(f"[IndexStoreService]  索引构建完成！知识库已安全落盘。")
        return True

    def build_and_save_rf(self, vectors: np.ndarray, payloads: list) -> bool:
        """支持增量追加 FAISS 索引并持久化到本地"""
        if len(vectors) == 0 or len(vectors) != len(payloads):
            print("[IndexStoreService] 向量矩阵与载荷长度不匹配或为空，拒绝入库！")
            return False
            
        self.dimension = vectors.shape[1]
        faiss.normalize_L2(vectors) # 先进行归一化

        # 核心：增量构建逻辑
        # 1. 尝试拉起本地历史库（如果内存中还没有加载的话）
        if self.index is None:
            self.load()

        # 2. 判断是【全新构建】还是【增量追加】
        if self.index is None:
            print(f"[IndexStoreService] [全新构建] 正在初始化 FAISS 索引树并存入 {len(payloads)} 条知识...")
            self.index = faiss.IndexFlatIP(self.dimension) 
            self.metadata = payloads
        else:
            print(f"[IndexStoreService] [增量追加] 正在向现有 FAISS 索引库追加 {len(payloads)} 条知识...")
            if self.dimension != self.index.d:
                print(f"[IndexStoreService] 维度不匹配！当前:{self.dimension}, 库中:{self.index.d}，拒绝入库！")
                return False
            self.metadata.extend(payloads) # 追加文本载荷

        # 将向量加入索引树 (无论是新建的还是加载的，都用 add 方法追加)
        self.index.add(vectors)

        # 落盘保存覆盖旧文件
        os.makedirs(self.db_dir, exist_ok=True)
        faiss.write_index(self.index, os.path.join(self.db_dir, "faiss.index"))
        with open(os.path.join(self.db_dir, "metadata.pkl"), "wb") as f:
            pickle.dump({"dim": self.dimension, "meta": self.metadata}, f)
            
        print(f"[IndexStoreService] 索引构建/追加完成！当前库内共 {len(self.metadata)} 条知识。已安全落盘。")
        return True

    # ==========================================
    # 读取与检索功能 (用于日常话务 RAG 流水线)
    # ==========================================
    def load(self) -> bool:
        """从本地磁盘快速拉起并挂载索引"""
        index_path = os.path.join(self.db_dir, "faiss.index")
        meta_path = os.path.join(self.db_dir, "metadata.pkl")
        
        if not os.path.exists(index_path) or not os.path.exists(meta_path): 
            return False
            
        self.index = faiss.read_index(index_path)
        with open(meta_path, "rb") as f:
            data = pickle.load(f)
            self.dimension, self.metadata = data["dim"], data["meta"]
        return True

    def search(self, query_vector: np.ndarray, top_k: int = 1) -> list:
        """极速检索返回 Top-K 结果及相似度"""
        if self.index is None or len(self.metadata) == 0: 
            return []
        
        query_vector = np.array(query_vector).reshape(1, -1).astype('float32')
        faiss.normalize_L2(query_vector)
        distances, indices = self.index.search(query_vector, top_k)
        
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx != -1:
                match_data = self.metadata[idx].copy()
                match_data["similarity"] = float(dist)
                results.append(match_data)
        return results