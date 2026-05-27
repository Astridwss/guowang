from fastapi import FastAPI
import uvicorn

# 1. 导入路由文件
from augment import router as augmentation_router
from asr import router as asr_router
from sentiment import router as sentiment_router
from desensitize import router as desensitize_router
from document_splitter import router as docx_split_router


app = FastAPI(title="Smart QA 智能客服微服务", version="1.0")

# 2. 挂载路由到主 app
app.include_router(augmentation_router)  #扩写
app.include_router(asr_router)          #语音转写
app.include_router(sentiment_router)
app.include_router(desensitize_router)

if __name__ == "__main__":
    # 3. 启动服务 (假设运行在 8000 端口)
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)