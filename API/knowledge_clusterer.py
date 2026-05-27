#对应原项目的cluster.py 需要手动传入 pkl 特征文件和原始 Excel
from fastapi import APIRouter, HTTPException, Form
from fastapi.responses import FileResponse
import tempfile
import os
import zipfile
from services.knowledge_clusterer import KnowledgeClustererService

router = APIRouter(prefix="/api/v1/cluster", tags=["知识聚类与洞察分析"])

# 实例化核心聚类引擎
clusterer_service = KnowledgeClustererService()


@router.post("/generate_report")
async def generate_cluster_report(
    dim_reduce: str = Form("tsne", description="降维算法: tsne 或 pca"),
    clustering: str = Form("hdbscan", description="聚类算法: hdbscan 或 kmeans"),
    n_clusters: int = Form(None, description="KMeans的簇数，留空则由 HDBSCAN 自动嗅探")
):
    """
    一键生成知识库聚类分析报告。
    直接从底层 FAISS 向量库中提取数据，返回包含 3D 可视化 HTML 和统计明细 Excel 的 ZIP 压缩包。
    """
    # 1. 确认底层数据库是否存在
    db_dir = "database"
    if not os.path.exists(os.path.join(db_dir, "faiss.index")):
        raise HTTPException(status_code=400, detail="向量数据库尚未构建，请先入库数据！")

    # 2. 开辟安全隔离的临时沙箱目录
    temp_dir = tempfile.mkdtemp()
    base_html_name = "cluster_insight_report.html"
    html_path = os.path.join(temp_dir, base_html_name)

    try:
        # 3. 呼叫底层核心算力，执行降维与聚类
        clusterer_service.process(
            db_dir=db_dir,
            output_html_path=html_path,
            dim_reduce=dim_reduce,
            clustering=clustering,
            n_clusters=n_clusters
        )

        # 依据重构服务的逻辑，寻找伴生的 Excel 文件
        stats_path = html_path.replace(".html", "_cluster_stats.xlsx")
        excel_path = html_path.replace(".html", "_domain_result.xlsx")

        # 4. 把生成的 3 个文件优雅地打包进 ZIP
        zip_filename = f"knowledge_cluster_results_{clustering}_{dim_reduce}.zip"
        zip_path = os.path.join(temp_dir, zip_filename)

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            if os.path.exists(html_path):
                zipf.write(html_path, arcname="1_3D_可视化洞察图.html")
            if os.path.exists(stats_path):
                zipf.write(stats_path, arcname="2_簇群统计数据.xlsx")
            if os.path.exists(excel_path):
                zipf.write(excel_path, arcname="3_打标分类明细表.xlsx")

        # 5. 返回 ZIP 压缩包给调用方
        return FileResponse(
            path=zip_path, 
            filename=zip_filename,
            media_type="application/zip"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"聚类分析爆发致命错误: {str(e)}")