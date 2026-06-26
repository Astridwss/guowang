import os
import time
import pandas as pd
from typing import Callable

# 引入底层积木 (Services)
from services.vector_embedding import VectorEmbeddingService
from services.knowledge_cluster import KnowledgeClustererService

class ClusterPipelineEngine:
    """
    知识聚类流水线编排引擎 (Application Service Layer)
    """
    def __init__(self, work_dir: str):
        self.work_dir = work_dir

    def run(
        self,
        task_id: str,
        local_faq_path: str,
        dim_reduce: str,
        clustering: str,
        n_clusters: int,
        llm_config: any,
        log_callback: Callable[[str], None]
    ) -> str:
        
        def log(msg: str):
            log_callback(f"[{time.strftime('%H:%M:%S')}] {msg}\n")

        # --- 1. 业务数据预加载 ---
        log(f"开始解析本地表格: {os.path.basename(local_faq_path)}")
        df = pd.read_excel(local_faq_path)
        
        # 智能寻找特征列
        target_col = "问题" if "问题" in df.columns else df.columns[1]
        system_col = "所属系统" if "所属系统" in df.columns else df.columns[0]

        # 👇 强力数据清洗逻辑
        # 1. 剔除核心问题真实存在的空值 (NaN)
        df = df.dropna(subset=[target_col])
        # 2. 问题列强转为字符串并去除首尾空格
        df[target_col] = df[target_col].astype(str).str.strip()
        # 3. 剔除纯粹的空字符串和 pandas 强转生成的 "nan" 字眼
        df = df[df[target_col] != ""]
        df = df[df[target_col].str.lower() != "nan"]
        
        # 处理系统列：如果某条数据有"问题"但没有"系统"，温和补全为"未知"，防止被丢弃
        if system_col:
            df[system_col] = df[system_col].fillna("未知").astype(str).str.strip()
            df.loc[df[system_col].str.lower() == "nan", system_col] = "未知"
            df.loc[df[system_col] == "", system_col] = "未知"
            log(f"检测到额外的分类维度: [{system_col}]，将加入 3D 可视化面板。")

        # 4. 【极度重要】重置索引
        df = df.reset_index(drop=True)

        questions = df[target_col].tolist()
        log(f"清洗完毕，成功提取 {len(questions)} 条有效待聚类文本。")

        # --- 2. 调度积木A：调用向量大模型 ---
        log("初始化向量大模型引擎，开始实时特征抽取...")
        embedding_svc = VectorEmbeddingService(
            base_url=llm_config.embed_base_url if llm_config else None,
            api_key=llm_config.embed_api_key if llm_config else None,
            model_name=llm_config.embed_model_name if llm_config else None
        )
        
        embeddings_matrix = embedding_svc.vectorize(questions)
        if embeddings_matrix is None or len(embeddings_matrix) == 0:
            raise ConnectionError("向量抽取失败，请检查向量大模型网络！")
        log(f"特征提取完毕！获取特征矩阵: {embeddings_matrix.shape}")

        # --- 3. 调度积木B：调用聚类算法与可视化 ---
        log(f"移交聚类与可视化分析引擎 (算法:{clustering.upper()}, 降维:{dim_reduce.upper()})...")
        clusterer_svc = KnowledgeClustererService()
        
        output_html_path = os.path.join(self.work_dir, f"cluster_3d_{task_id}.html")
        
        result_path = clusterer_svc.process(
            embeddings_matrix=embeddings_matrix,
            df_data=df,
            target_col=target_col,
            output_html_path=output_html_path,
            system_col=system_col,  # 所属系统
            dim_reduce=dim_reduce,
            clustering=clustering,
            n_clusters=n_clusters
        )
        
        log("✅ 聚类任务完成！")
        return os.path.abspath(result_path)
        