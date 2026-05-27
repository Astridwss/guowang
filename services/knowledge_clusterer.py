import os
import sys
import pandas as pd
import numpy as np
import hdbscan
from sklearn.manifold import TSNE
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
import plotly.express as px

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.index_store import IndexStoreService

class KnowledgeClustererService:
    """
    知识聚类与可视化分析服务 (完全基于 FAISS 数据库的高级洞察插件)
    职责：读取 FAISS 底层索引中的高维向量与 Payload，执行降维与无监督聚类。
    输入：数据库文件夹db_dir。
    输出：原来项目是输出一个交互式的 xxx.html (3D 散点图)。
        一个 _cluster_stats.xlsx (统计每个簇有多少条数据、中心点坐标)。
        一个 _domain_result.xlsx (给原始数据打上聚类标签后的明细表)。
    """
    def __init__(self):
        print("[KnowledgeClustererService] 初始化知识聚类与可视化引擎...")

    def process(self, 
                db_dir: str, 
                output_html_path: str,
                dim_reduce: str = 'tsne', 
                clustering: str = 'hdbscan', 
                n_clusters: int = None):
        """
        核心业务方法：执行降维、聚类并生成 3D 报表
        【架构升级】：不再需要传入原始的 Excel 和 pkl，直接从向量数据库中提取一切！
        """
        print(f"[Clusterer] 正在挂载向量数据库: {db_dir}/ ...")
        store = IndexStoreService(db_dir=db_dir)
        
        if not store.load() or store.index is None or store.index.ntotal == 0:
            print(f"[Clusterer] ❌ 数据库加载失败或为空，无法进行聚类分析。")
            return

        n_samples = store.index.ntotal
        dimension = store.dimension
        print(f"[Clusterer] 数据加载成功！共提取到 {n_samples} 条向量，维度: {dimension}。")

        # ---------------------------------------------------------
        # 0. 从 FAISS 底层逆向提取特征矩阵
        # ---------------------------------------------------------
        # 因为我们使用的是 IndexFlatIP，可以通过 reconstruct 完美还原存入的浮点矩阵
        embeddings = np.zeros((n_samples, dimension), dtype=np.float32)
        for i in range(n_samples):
            embeddings[i] = store.index.reconstruct(i)

        # ---------------------------------------------------------
        # 1. 降维逻辑 (3D) - 防御性降级算法
        # ---------------------------------------------------------
        min_samples_for_tsne = 100
        if dim_reduce == 'tsne' and n_samples < min_samples_for_tsne:
            print(f"[Clusterer]  样本量 ({n_samples}) 少于 t-SNE 最佳要求 ({min_samples_for_tsne})，自动降级为 PCA")
            dim_reduce = 'pca'
            
        if dim_reduce == 'pca':
            reduced_embeddings = PCA(n_components=3, random_state=42).fit_transform(embeddings)
        else:
            try:
                reduced_embeddings = TSNE(n_components=3, random_state=42).fit_transform(embeddings)
            except Exception as e:
                print(f"[Clusterer]  t-SNE 降维失败 ({str(e)})，自动切回 PCA")
                reduced_embeddings = PCA(n_components=3, random_state=42).fit_transform(embeddings)

        # ---------------------------------------------------------
        # 2. 聚类逻辑
        # ---------------------------------------------------------
        if clustering == 'kmeans':
            if n_clusters is None:
                print("[Clusterer] 未指定 K 值，使用 HDBSCAN 自动嗅探聚类数量...")
                temp_labels = hdbscan.HDBSCAN(min_cluster_size=2).fit_predict(embeddings)
                n_clusters = max(2, len(set(temp_labels)) - (1 if -1 in temp_labels else 0))
                print(f"[Clusterer] 嗅探完成，动态设定的 K 值为: {n_clusters}")
            
            clusterer = KMeans(n_clusters=n_clusters, random_state=42)
            labels = clusterer.fit_predict(embeddings)
        else:
            clusterer = hdbscan.HDBSCAN(min_cluster_size=2)
            labels = clusterer.fit_predict(embeddings)

        if len(set(labels)) == 1 and -1 in labels:
            print("[Clusterer]  样本极度离散（全部判定为噪声），已强制归一处理。")
            labels = [0] * len(labels)

        # ---------------------------------------------------------
        # 3. 结果写回与统计 (直接利用 store.metadata 组装数据)
        # ---------------------------------------------------------
        # metadata 里自带了 question, answer
        df_data = pd.DataFrame(store.metadata)
        df_data["hdb_cluster"] = labels

        df_vis = pd.DataFrame(reduced_embeddings, columns=["x", "y", "z"])
        df_vis["hdbscan_cluster"] = labels
        # 将原始问题绑定到可视化图中，方便鼠标悬停查看
        df_vis["question"] = df_data.get("question", "未知问题")
        
        df_valid = df_vis[df_vis["hdbscan_cluster"] != -1] # 滤除噪声

        cluster_stats = []
        for cluster_id in sorted(df_valid["hdbscan_cluster"].unique()):
            cluster_data = df_valid[df_valid["hdbscan_cluster"] == cluster_id]
            cluster_stats.append({
                "簇ID": cluster_id,
                "簇内样本数": len(cluster_data),
                "中心点X": cluster_data["x"].mean(),
                "中心点Y": cluster_data["y"].mean(),
                "中心点Z": cluster_data["z"].mean()
            })
            
        stats_file = output_html_path.replace(".html", "_cluster_stats.xlsx")
        pd.DataFrame(cluster_stats).to_excel(stats_file, index=False)
        
        output_excel = output_html_path.replace(".html", "_domain_result.xlsx")
        df_data.to_excel(output_excel, index=False)

        # ---------------------------------------------------------
        # 4. 生成 3D HTML 散点图
        # ---------------------------------------------------------
        fig = px.scatter_3d(
            df_valid, x="x", y="y", z="z", 
            color="hdbscan_cluster",
            hover_name="question", # 鼠标悬停时显示真实的 FAQ 问题！
            title="知识库聚类 3D 可视化洞察分析",
            color_continuous_scale='viridis'
        )
        fig.write_html(output_html_path)
        print(f"\n[Clusterer]  聚类分析完成！")
        print(f"   3D 可视化报告: {output_html_path}")
        print(f"  📈 簇群统计数据: {stats_file}")
        print(f"  💾 附带簇标签的业务明细表: {output_excel}")


# ==========================================
# 独立测试模块
# ==========================================
if __name__ == "__main__":
    service = KnowledgeClustererService()
    # 当你的造库流水线跑完，生成了 database 目录后，你可以直接 run 这段代码体验 3D 聚类！
    # service.process(
    #     db_dir="database",
    #     output_html_path="insight_report.html"
    # )