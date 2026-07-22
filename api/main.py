import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
import uvicorn
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 引入连通性自检调度器
from core.health_check import run_all_llm_health_checks

# 1. 导入业务路由文件
from routers.rag_router import router as rag_pipeline_router
from routers.augmentation_router import router as augment_router
from routers.cluster_router import router as cluster_router
from routers.document_extraction_router import router as document_extraction_router
from routers.desensitization_router import router as desensitization_router
from routers.sentiment_analysis_router import router as sentiment_analysis_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI 官方推荐生命周期管理器：
    服务启动时，使用 asyncio.create_task 在后台异步拉起自检，
    保证 uvicorn 能够在毫秒级内瞬间启动并对外提供服务，绝对不因大模型网络延迟而卡死。
    """
    asyncio.create_task(run_all_llm_health_checks())
    yield

app = FastAPI(
    title="Smart QA 智能客服微服务", 
    version="1.0",
    lifespan=lifespan
)

# 2. 挂载路由到主 app
app.include_router(rag_pipeline_router)           # 话务 RAG 处理流水线对应 opt_asr.py
app.include_router(augment_router)                # 数据增强
app.include_router(cluster_router)                # 聚类
app.include_router(document_extraction_router)    # 多模态处理：word-chunk-VLLM-excel
app.include_router(desensitization_router)        # 脱敏
app.include_router(sentiment_analysis_router)    # 情绪分析

if __name__ == "__main__":
    # 3. 启动服务 (运行在 8000 端口)
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)