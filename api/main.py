from fastapi import FastAPI
import uvicorn

# 1. 导入路由文件
from routers.rag_router import router as rag_pipeline_router
from routers.augmentation_router import router as augment_router
from routers.cluster_router import router as cluster_router
from routers.document_extraction_router import router as document_extraction_router
from routers.desensitization_router import router as desensitization_router
from routers.sentiment_analysis_router import router as sentiment_analysis_router

app = FastAPI(title="Smart QA 智能客服微服务", version="1.0")

# 2. 挂载路由到主 app
app.include_router(rag_pipeline_router) # 话务 RAG 处理流水线对应 opt_asr.py
app.include_router(augment_router) # 数据增强
app.include_router(cluster_router) # 聚类
app.include_router(document_extraction_router) # 多模态处理：word-chunk-VLLM-excel
app.include_router(desensitization_router) # 脱敏
app.include_router(sentiment_analysis_router) #情绪分析

if __name__ == "__main__":
    # 3. 启动服务 (假设运行在 8000 端口)
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)