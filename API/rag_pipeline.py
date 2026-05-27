#原来代码opt_asr.py脚本业务流程：原始的ARS文本--LLM初次提炼--向量化/存储--向量检索--rag融合检索
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
import pandas as pd
import tempfile
import os

from services.dialogue_extractor import DialogueExtractorService
from services.vector_embedding import VectorEmbeddingService
from services.knowledge_retriever import KnowledgeRetrieverService
from services.rag_synthesizer import RAGSynthesizerService

router = APIRouter(prefix="/api/v1/rag", tags=["话务 RAG 处理流水线"])

# TODO:向量库怎么存？

# 注意：Retriever 初始化时会去加载 FAISS 索引库 (默认 database 目录)
print("正在初始化 RAG 流水线组件...")
extractor_svc = DialogueExtractorService()
embedding_svc = VectorEmbeddingService()
retriever_svc = KnowledgeRetrieverService(db_dir="database", threshold=0.8) 
synthesizer_svc = RAGSynthesizerService()

@router.post("/batch_process_asr")
async def batch_process_asr(file: UploadFile = File(...)):
    """
    话务 RAG 终极流水线：接收 ASR 表格，经过 [提炼->向量化->检索->融合]，输出详细结果表。
    """
    if not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="只支持 Excel 文件")

    try:
        df = pd.read_excel(file.file)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"文件解析失败: {str(e)}")

    target_col = "ASR" if "ASR" in df.columns else df.columns[0]
    results = []

    # 遍历处理每一行对话
    for idx, row in df.iterrows():
        asr_text = str(row[target_col])
        if not asr_text.strip():
            continue

        # ---------------------------------------------------------
        # 步骤 1：LLM初次提炼
        extracted_data = extractor_svc.extract(asr_text)
        core_question = extracted_data.get("core_question", "")
        raw_extraction = extracted_data.get("raw_extraction", "")

        matched_faq = None
        
        if core_question:
            # ---------------------------------------------------------
            # 步骤 2：向量化计算
            # 返回的是 shape 为 (1, dim) 的 numpy 矩阵
            q_vectors = embedding_svc.vectorize([core_question])
            
            if len(q_vectors) > 0:
                # ---------------------------------------------------------
                #步骤 3：知识库检索 (带阈值拦截)
                # 注意取出第 0 个向量传入
                matched_faq = retriever_svc.retrieve_by_vector(q_vectors[0])

        # ---------------------------------------------------------
        # 步骤 4：RAG 二次融合裁判
        # 如果 matched_faq 为 None，底层会自动直接返回 raw_extraction 草稿
        final_output = synthesizer_svc.synthesize(
            asr_text=asr_text, 
            initial_extraction=raw_extraction, 
            matched_faq=matched_faq
        )

        # ---------------------------------------------------------
        # 组装返回数据 (完美复刻原项目详细 Excel 的字段)
        results.append({
            "ASR": asr_text,
            "refined_question": core_question,
            "faq_question": matched_faq["question"] if matched_faq else "",
            "similarity": matched_faq["similarity"] if matched_faq else -1,
            "faq_answer": matched_faq["answer"] if matched_faq else "",
            "final_output": final_output
        })

    # 将结果写入临时 Excel 文件
    result_df = pd.DataFrame(results)
    temp_excel = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") #TODO:临时文件
    result_df.to_excel(temp_excel.name, index=False)

    return FileResponse(
        path=temp_excel.name, 
        filename=f"optASR_RAG_result_{file.filename}",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )