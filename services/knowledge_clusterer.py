# 文件路径：services/knowledge_clusterer.py
import pandas as pd
import numpy as np
import hdbscan
from sklearn.manifold import TSNE
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
import plotly.express as px

class KnowledgeClustererService:
    """
    知识聚类与可视化分析服务 (无状态积木)
    """
    def __init__(self):
        print("[KnowledgeClustererService] 初始化知识聚类与可视化引擎...")

    def process(
        self,
        embeddings_matrix: np.ndarray,
        df_data: pd.DataFrame,
        target_col: str,            #问题
        output_html_path: str,
        system_col: str = None,  # 接收所属系统列名
        dim_reduce: str = 'tsne',
        clustering: str = 'hdbscan',
        n_clusters: int = None
    ) -> str:
        """
        核心算法方法：执行降维、聚类并生成 3D HTML 文件
        """
        n_samples = len(embeddings_matrix)
        
        # ---------------------------------------------------------
        # 1. 降维处理 (PCA / t-SNE)
        # ---------------------------------------------------------
        min_samples_tsne = 100
        if dim_reduce.lower() == 'tsne' and n_samples < min_samples_tsne:
            print(f"[Clusterer] ⚠️ 样本量({n_samples})少于 t-SNE 要求下限，自动降级为 PCA。")
            dim_reduce = 'pca'

        if dim_reduce.lower() == 'pca':
            reduced_embeddings = PCA(n_components=3, random_state=42).fit_transform(embeddings_matrix)
        else:
            reduced_embeddings = TSNE(n_components=3, random_state=42).fit_transform(embeddings_matrix)
        
        df_data['x'] = reduced_embeddings[:, 0]
        df_data['y'] = reduced_embeddings[:, 1]
        df_data['z'] = reduced_embeddings[:, 2]

        # ---------------------------------------------------------
        # 2. 聚类处理 (HDBSCAN / KMeans)
        # ---------------------------------------------------------
        if clustering.lower() == 'kmeans':
            if n_clusters is None:
                raise ValueError("使用 KMeans 算法时，必须传入 n_clusters 参数！")
            clusterer = KMeans(n_clusters=n_clusters, random_state=42)
            labels = clusterer.fit_predict(reduced_embeddings)
        else: # 默认为 hdbscan
            clusterer = hdbscan.HDBSCAN(min_cluster_size=min(5, max(2, n_samples // 10)))
            labels = clusterer.fit_predict(reduced_embeddings)
        
        df_data['Cluster_Labels'] = labels.astype(str)

        # ---------------------------------------------------------
        # 3. 渲染 3D HTML 可视化 (带系统属性悬浮展示)
        # ---------------------------------------------------------
        # 👇 动态构建悬浮框展示数据：默认展示问题和簇标签，隐藏坐标
        hover_data_dict = {target_col: True, 'Cluster_Labels': True, 'x': False, 'y': False, 'z': False}
        if system_col and system_col in df_data.columns:
            hover_data_dict[system_col] = True # 如果有系统列，加入悬浮展示面板
        
        fig = px.scatter_3d(
            df_data, x='x', y='y', z='z',
            hover_name=target_col,
            hover_data=hover_data_dict,
            color='Cluster_Labels',
            title=f"知识点聚类空间分布 ({clustering.upper()} | {dim_reduce.upper()})",
            color_continuous_scale='viridis'
        )
        
        # 优化显示效果
        fig.update_traces(marker=dict(size=5, opacity=0.8))
        fig.update_layout(margin=dict(l=0, r=0, b=0, t=40))

        fig.write_html(output_html_path)
        print(f"[Clusterer] 聚类分析完成，3D 图表已生成: {output_html_path}")
        
        return output_html_path