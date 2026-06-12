# 文件路径：use_cases/document_extraction_orchestrator.py
import os
import re
import time
import pandas as pd
from typing import Callable

# 引入底层两大标准积木
from services.document_splitter import DocumentSplitterService 
from services.vision_qa_extractor import VisionQAExtractorService 

class DocumentExtractionPipelineEngine:
    """
    文档图文抽取编排引擎 (Application Service Layer)
    职责：统筹调度文本切分积木与多模态模型提炼积木，实现非结构化 Word 到结构化 FAQ 的转化。
    """
    def __init__(self, work_dir: str):
        self.work_dir = work_dir
        # 强制将所有图片的落地和提取范围，绝对锁定在当前任务的专属沙盒中！
        self.img_output_dir = os.path.join(self.work_dir, "extracted_images")

    def run(
        self,
        task_id: str,
        local_docx_path: str,
        llm_config: any,
        log_callback: Callable[[str], None]
    ) -> str:
        
        def log(msg: str):
            log_callback(f"[{time.strftime('%H:%M:%S')}] {msg}\n")

        # --- 1. 物理切分：Word 文档解析与图片落地 ---
        log(f"开始解析 Word 文档: {os.path.basename(local_docx_path)}")
        os.makedirs(self.img_output_dir, exist_ok=True)
        
        extractor_svc = DocumentSplitterService(output_img_dir=self.img_output_dir)
        # 调度切分积木
        chunks = extractor_svc.process_word_docx(local_docx_path)
        log(f"文档切分完毕，共提取出 {len(chunks)} 个图文内容切片。图片保存至沙盒子目录。")

        # --- 2. 视觉大模型图文抽取 ---
        log("初始化多模态视觉大模型引擎 (Vision-LLM)...")
        vision_llm_svc = VisionQAExtractorService(
            base_url=llm_config.chat_base_url if llm_config else None,
            api_key=llm_config.chat_api_key if llm_config else None,
            model_name=llm_config.chat_model_name if llm_config else None,
        )
        
        rows = []
        log("开始进行 AI 多模态理解与 FAQ 矩阵提取，请耐心等待...")
        
        # 💡【BUG 修正开始】：精细化重构大模型输出扫描与矩阵平铺逻辑
        for i, chunk in enumerate(chunks):
            log(f"正在驱动大模型提炼图文切片 [{i+1}/{len(chunks)}]...")
            
            # 调度升级后的多模态积木，传入图片沙盒
            llm_output = vision_llm_svc.extract_qa_from_chunk(chunk, self.img_output_dir)
            
            # 防超时保护降级
            if llm_output is None:
                log(f"⚠️ [网络超时降级] 切片 [{i+1}] 大模型响应失败，已自动跳过，保护前面已有数据！")
                continue
                
            llm_output = llm_output.strip()
            
            # 【打假防幻觉线】：代码层双重拒答过滤
            if not llm_output or llm_output == "无" or "无" in llm_output[:5]:
                continue
            
            # 兼容性提取原始文本：全面适配 chunk 为字典、对象或纯文本的极端场景
            if hasattr(chunk, 'text'):
                original_text = chunk.text
            elif isinstance(chunk, dict):
                original_text = chunk.get("text", "")
            else:
                original_text = str(chunk)
                
            # 💡【核心算法重构点】：使用正向预查按照 "问题：" 标记动态切分单切片内的多个 FAQ 块
            # 如果大模型吐出了多个问答对，这里会自动分割成一个包含多个文本块的 list
            extracted_items = [block.strip() for block in re.split(r'(?=问题：)', llm_output) if block.strip()]
            
            if extracted_items:
                # 对齐您的修正规范：构建以“原始文本”为核心的平铺数据行字典
                row = {"原始文本": original_text}
                for idx, item in enumerate(extracted_items):
                    row[f"提取内容_{idx+1}"] = item
                rows.append(row)

        # --- 3. 结构化结果在沙盒内落盘 ---
        log(f"大模型图文交互处理完毕！共清洗、沉淀出 {len(rows)} 条高拟合度平铺结果记录。")
        output_excel_path = os.path.join(self.work_dir, f"faq_extracted_{task_id}.xlsx")
        
        if len(rows) > 0:
            df = pd.DataFrame(rows)
            df.to_excel(output_excel_path, index=False)
        else:
            # 极端空文档防御兜底
            pd.DataFrame([{
                "原始文本": "未提取到任何有效业务数据", 
                "提取内容_1": "文档不包含具体可落盘的操作或FAQ内容"
            }]).to_excel(output_excel_path, index=False)

        log(f"✅ 多模态数据提炼全链路执行完毕，数据已平铺落盘至沙盒空间。")
        return os.path.abspath(output_excel_path)