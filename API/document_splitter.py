# 对应原项目的extract_features.py
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import tempfile
import os
import shutil
from services.document_splitter import DocumentSplitterService

router = APIRouter(prefix="/api/v1/splitter", tags=["文档解耦切分入口"])

# 实例化核心组件（指定 Word 内嵌图片抽离后的安全保存盘符/目录）
IMAGE_SAVE_DIR = "data/word_images"
splitter_service = DocumentSplitterService(output_img_dir=IMAGE_SAVE_DIR)


@router.post("/split_word")
async def split_word_docx(file: UploadFile = File(...)):
    """
    1. Word 多模态手册切分接口
    输入：.docx 文件
    输出：按标题物理切割并抽离好图片的逻辑块(Chunks) JSON 列表
    """
    if not file.filename.endswith(".docx"):
        raise HTTPException(status_code=400, detail="只支持 .docx 格式的 Word 文件")

    # 落地物理临时文件，供 python-docx 库底层流式读取
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as temp_docx:
            shutil.copyfileobj(file.file, temp_docx)
            temp_path = temp_docx.name
    except Exception as e:
         raise HTTPException(status_code=500, detail=f"服务器暂存 Word 失败: {str(e)}")

    try:
        # 调用重构服务：抽离图片、按标题切块
        chunks = splitter_service.process_word_docx(temp_path)
        
        return JSONResponse(content={
            "filename": file.filename,
            "total_chunks": len(chunks),
            "status": "success",
            "chunks": chunks
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"解析 Word 发生致命错误: {str(e)}")
    finally:
        # 防御性编程：阅后即焚，绝不堆积临时文件
        if os.path.exists(temp_path):
            os.remove(temp_path)


@router.post("/parse_excel")
async def parse_faq_excel(file: UploadFile = File(...)):
    """
    2. Excel 存量 FAQ 问答对解析接口
    输入：存量知识点 .xlsx 表格
    输出：去重、全局标准化清洗后的有效 payloads 列表（可直接用于 FAISS 批量构建索引）
    """
    if not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="只支持 .xlsx 或 .xls 格式的 Excel 表格")

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as temp_excel:
            shutil.copyfileobj(file.file, temp_excel)
            temp_path = temp_excel.name
    except Exception as e:
         raise HTTPException(status_code=500, detail=f"服务器暂存 Excel 失败: {str(e)}")

    try:
        # 调用重构服务：去重并清洗问题
        valid_texts, payloads = splitter_service.process_faq_excel(temp_path)
        
        return JSONResponse(content={
            "filename": file.filename,
            "total_valid_records": len(valid_texts),
            "status": "success",
            "payloads": payloads  # 直接抛出结构化的 [{"question": "...", "answer": "..."}] 数组
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"解析 Excel 发生致命错误: {str(e)}")
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)