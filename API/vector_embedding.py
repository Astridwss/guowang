#对应原项目：extract_features.py    TODO:这要注意系统业务的流程。要改的
from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from fastapi.responses import JSONResponse
import tempfile
import os
import shutil
import numpy as np
from services.vector_embedding import VectorEmbeddingService
from services.document_splitter import DocumentSplitterService

router = APIRouter(prefix="/api/v1/embedding", tags=["向量化与特征提取"])

# 实例化核心算力积木
embedding_service = VectorEmbeddingService()
splitter_service = DocumentSplitterService()


@router.post("/extract")
async def extract_features_api(
    file: UploadFile = File(..., description="要提取特征的 FAQ Excel 文件"),
    column_name: str = Form(..., description="Excel 中需要转为向量的目标列名（如 question 或 ASR）"),
    deduplicate: bool = Form(False, description="是否开启全局文本去重"),
    filter_invalid: bool = Form(True, description="是否过滤空行、NaN 或无意义文本"),
    remove_punctuation: bool = Form(False, description="是否去除所有标点符号"),
    remove_words: str = Form("", description="要过滤的特定高频词/停用词，多个词用逗号分隔")
):
    """
    还原原项目 extract_features.py 的完整全套核心逻辑：
    输入 FAQ Excel，在内存中完成高度定制化的清洗、去重与向量化计算，最终统一抛出。
    """
    if not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="只支持 .xlsx 或 .xls 格式的 Excel 表格")

    # 1. 落地物理临时文件
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as temp_excel:
            shutil.copyfileobj(file.file, temp_excel)
            temp_path = temp_excel.name
    except Exception as e:
         raise HTTPException(status_code=500, detail=f"服务器暂存本地失败: {str(e)}")

    try:
        # 2. 借用底层文本清洗公共逻辑，读取并按照参数精确处理 Excel 指定列
        # 注：为了实现原项目中诸如 `--remove_words` 等精细化的清洗开关，
        # 我们直接使用底层高度收拢的 TextProcessor 工具或在服务层调配
        import pandas as pd
        from utils.text_processor import TextProcessor

        df = pd.read_excel(temp_path)
        if column_name not in df.columns:
            raise HTTPException(status_code=400, detail=f"Excel 中未找到指定的列名: '{column_name}'")

        processed_data = []
        seen_texts = set()

        for idx, row in df.iterrows():
            raw_text = row[column_name]
            
            # 执行细粒度清洗洗涤
            clean_text = TextProcessor.clean_text(
                text=raw_text,
                filter_invalid=filter_invalid,
                remove_punctuation=remove_punctuation,
                remove_words=remove_words
            )
            
            if not clean_text:
                continue
                
            # 去重开关控制
            if deduplicate:
                if clean_text in seen_texts:
                    continue
                seen_texts.add(clean_text)

            # 结构化暂存，保留原项目中的索引 index 对齐能力
            processed_data.append({
                "original_text": str(raw_text),
                "processed_text": clean_text,
                "index": idx
            })

        if not processed_data:
            return JSONResponse(content={"status": "warning", "message": "经过规则过滤后，没有合法的文本用于提取向量"})

        # 3. 批量打入核心 VectorEmbeddingService 算力矩阵
        texts_to_embed = [item["processed_text"] for item in processed_data]
        vectors_ndarray = embedding_service.vectorize(texts_to_embed)

        # 4. 组装成原项目熟悉的 pkl / json 混合承载格式
        features_response = []
        for i, item in enumerate(processed_data):
            features_response.append({
                "original_text": item["original_text"],
                "text": item["processed_text"],
                "feature": vectors_ndarray[i].tolist(),  # numpy 矩阵序列化为标准可传输 JSON list
                "index": item["index"]
            })

        return JSONResponse(content={
            "filename": file.filename,
            "total_extracted": len(features_response),
            "status": "success",
            "features": features_response
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"特征矩阵提取爆发致命错误: {str(e)}")
    finally:
        # 阅后即焚，强防御临时文件积压
        if os.path.exists(temp_path):
            os.remove(temp_path)