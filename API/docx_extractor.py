#对应原项目得docx_extractor.py：
# 上传 Word ➡️ DocumentSplitterService ➡️ 产生 Chunks ➡️ VLLMExtractorService (缺少的拼图，用来调大模型) ➡️ 组装生成 Excel。

from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
import pandas as pd
import tempfile
import os
import shutil

# 导入底层的三大核心积木 (解析、提取、文本清洗全部分离)
from services.document_splitter import DocumentSplitterService
from services.vision_qa_extractor import VisionQAExtractorService
from utils.text_processor import TextProcessor  # <--- 引入你的全局清洗库

router = APIRouter(prefix="/api/v1/docx", tags=["图文手册提取"])

#TODO:图片存储MinIO,清磁盘
IMAGE_SAVE_DIR = "data/word_images" 
splitter_service = DocumentSplitterService(output_img_dir=IMAGE_SAVE_DIR)
vision_extractor_service = VisionQAExtractorService()

# ⚠️ 注意：那个局部的 parse_llm_output 函数已经被彻底删除了！API 层恢复了绝对的纯净。

@router.post("/extract_faq_excel")
async def extract_docx_to_excel(file: UploadFile = File(...)):
    """
    综合业务接口：上传 Word 手册 -> 切分 -> 多模态提取 -> 全局清洗 -> 导出 Excel
    """
    if not file.filename.endswith(".docx"):
        raise HTTPException(status_code=400, detail="只支持 .docx 格式的 Word 文件")

    ##TODO:文件存储MinIO,清磁盘
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as temp_docx:
            shutil.copyfileobj(file.file, temp_docx)
            temp_path = temp_docx.name
    except Exception as e:
         raise HTTPException(status_code=500, detail=f"文件保存失败: {str(e)}")

    try:
        # 1. 切分 Word
        chunks = splitter_service.process_word_docx(temp_path)
        results = []
        
        # 2. 遍历处理每个 Chunk
        for chunk in chunks:
            chunk_text = ""
            image_filename = ""
            
            for item in chunk:
                if item.get("type") == "text":
                    chunk_text += item.get("text", "") + "\n"
                elif item.get("type") == "image" and not image_filename:
                    image_filename = item.get("image")
            
            if not chunk_text.strip() and not image_filename:
                continue

            image_base64 = ""
            if image_filename:
                img_path = os.path.join(IMAGE_SAVE_DIR, image_filename)
                image_base64 = vision_extractor_service.encode_local_image(img_path)

            # 3. 调用视觉大模型
            llm_response = vision_extractor_service.chat_vision_chunk(
                text_content=chunk_text, 
                image_base64=image_base64
            )
            
            # 4. 【核心替换】调用全局公共工具进行解析！
            # 优雅地拿到清洗后的 question 列表和 payloads 字典
            valid_texts, payloads = TextProcessor.parse_llm_qa_extraction(llm_response)
            
            # 5. 拼装行数据 (把结构化的 payload 拼回原项目所需的纯文本格式)
            if payloads:
                row = {"原始文本": chunk_text.strip()}
                for i, payload in enumerate(payloads):
                    # 将问题和答案重新组装成一段话，填入 Excel 单元格
                    formatted_cell_text = f"问题：{payload['question']}\n{payload['answer']}"
                    row[f"提取内容_{i+1}"] = formatted_cell_text
                results.append(row)

        # 6. 生成导出 Excel
        df = pd.DataFrame(results)
        temp_excel = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
        df.to_excel(temp_excel.name, index=False)
        
        return FileResponse(
            path=temp_excel.name,  ##TODO:存储MinIO,清磁盘
            filename=f"extracted_faq_{file.filename}.xlsx",
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"流水线处理出错: {str(e)}")
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)