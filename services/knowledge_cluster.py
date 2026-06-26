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
        target_col: str,            # 问题列名
        output_html_path: str,
        system_col: str = None,     # 接收所属系统列名
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
        # 3. 渲染 3D HTML 可视化 (定制极简 3D 态势球悬浮面板)
        # ---------------------------------------------------------
        # 💡【高抗震防呆设计】：若外部未提供 system_col 或该列不在 df_data 中，则自建一列填充'未知'，确保显示格式永远一致
        actual_system_col = system_col
        if not actual_system_col or actual_system_col not in df_data.columns:
            actual_system_col = '所属系统_默认'
            df_data[actual_system_col] = '未知'

        # 💡【核心重构点】：使用 custom_data 绑定目标列，配合 hovertemplate 控制 3D 态势球浮窗样式
        # customdata[0] 对应 actual_system_col，customdata[1] 对应 target_col
        # <extra></extra> 用于抹除 Plotly 默认在右侧展示的 Trace 名称/簇标签小盒子，实现绝对纯净的单卡片 hover
        custom_data_cols = [actual_system_col, target_col]
        hovertemplate = (
            "<b>所属系统</b>: %{customdata[0]}<br>"
            "<b>问题</b>: %{customdata[1]}<extra></extra>"
        )

        fig = px.scatter_3d(
            df_data, x='x', y='y', z='z',
            color='Cluster_Labels',
            custom_data=custom_data_cols,  # 将指定数据压入渲染上下文
            title=f"知识点聚类空间分布 ({clustering.upper()} | {dim_reduce.upper()})",
            color_continuous_scale='viridis'
        )
        
        # 💡 重写 Trace 渲染规则，彻底剥离 x, y, z 坐标等噪音，仅输出 custom 模版格式
        fig.update_traces(
            hovertemplate=hovertemplate,
            marker=dict(size=5, opacity=0.8)
        )
        
        # 优化显示效果
        fig.update_layout(margin=dict(l=0, r=0, b=0, t=40))

        fig.write_html(output_html_path)
        print(f"[Clusterer] 聚类分析完成，极简样式 3D 图表已生成: {output_html_path}")
        
        return output_html_path