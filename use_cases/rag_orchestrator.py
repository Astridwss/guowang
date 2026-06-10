# 文件路径：use_cases/rag_orchestrator.py
import os
import time
from tkinter import N
import pandas as pd
from typing import Callable, Optional, Tuple

# 导入底层能力积木
from services.document_splitter import DocumentSplitterService
from services.dialogue_extractor import DialogueExtractorService
from services.vector_embedding import VectorEmbeddingService
from services.index_store import IndexStoreService
from services.knowledge_retriever import KnowledgeRetrieverService
from services.rag_synthesizer import RAGSynthesizerService

class RAGPipelineEngine:
    """
    话务 RAG 流水线编排引擎 (Application Service Layer)
    """
    def __init__(self, work_dir: str = None, db_dir: str = None):
        self.work_dir = work_dir
        self.db_dir = work_dir

    def run(
        self,
        task_id: str, 
        local_asr_path: str, 
        local_faq_path: str, 
        llm_config: any, 
        log_callback: Callable[[str], None]  
    ) -> Tuple[str, str]:
        """
        执行主业务编排流水线，生成对齐原始项目规范的双轨文件，原始项目只输出了详细的
        """
        def log(msg: str):
            log_callback(f"[{time.strftime('%H:%M:%S')}] {msg}\n")

        # --- 0. 动态依赖注入 ---
        splitter_svc = DocumentSplitterService(output_img_dir=self.work_dir)
        extractor_svc = DialogueExtractorService(
            base_url=llm_config.chat_base_url if llm_config else None,
            api_key=llm_config.chat_api_key if llm_config else None,
            model_name=llm_config.chat_model_name if llm_config else None,
            temperature=llm_config.temperature if llm_config else None
        )
        synthesizer_svc = RAGSynthesizerService(
            base_url=llm_config.chat_base_url if llm_config else None,
            api_key=llm_config.chat_api_key if llm_config else None,
            model_name=llm_config.chat_model_name if llm_config else None,
            temperature=llm_config.temperature if llm_config else None
        )
        embedding_svc = VectorEmbeddingService(
            base_url=llm_config.embed_base_url if llm_config else None,
            api_key=llm_config.embed_api_key if llm_config else None,
            model_name=llm_config.embed_model_name if llm_config else None
        )

        # --- 1. 自动建库防线 ---
        db_index_path = os.path.join(self.db_dir, "faiss.index")
        if not os.path.exists(db_index_path):
            log("检测到底层 FAISS 知识库不存在，启动自动建库程序...")
            if not local_faq_path or not os.path.exists(local_faq_path):
                raise ValueError("知识库不存在，且未提供 faq_file_url，无法自动建库！")
            
            valid_texts, payloads = splitter_svc.process_faq_excel(local_faq_path)
            vectors_ndarray = embedding_svc.vectorize(valid_texts)
            
            store = IndexStoreService(db_dir=self.db_dir)
            if not store.build_and_save(vectors_ndarray, payloads):
                raise RuntimeError("底层数据库写入失败！")
            log("自动建库完成！")

        # 【核心对齐 1】：把检索器的阈值设为 -1，允许盲查出全库最高分的第一名，不做硬拦截
        retriever_svc = KnowledgeRetrieverService(db_dir=self.db_dir, threshold=-1)

        # --- 2. 话务 RAG 串联流转 ---
        log("开始处理话务 ASR 数据，驱动双引擎...")
        df = pd.read_excel(local_asr_path)
        target_col = "ASR" if "ASR" in df.columns else df.columns[0]
        results = []
        total_rows = len(df)
        
        for idx, row in df.iterrows():
            asr_text = str(row[target_col])
            if not asr_text.strip() or asr_text.lower() in ['nan', 'nat', 'none']:
                continue
            
            row_prefix = f"[{idx+1}/{total_rows}]"
            
            # 2.1 第一轮提炼：提取核心问题
            extracted = extractor_svc.extract(asr_text)
            core_question = extracted.get("core_question", "")
            raw_extraction = extracted.get("raw_extraction", "")
            
            # 2.2 知识检索：不管分高分低，先抓出最像的那一条标准 FAQ
            matched_faq = None
            if core_question:
                q_vectors = embedding_svc.vectorize([core_question])
                if len(q_vectors) > 0:
                    matched_faq = retriever_svc.retrieve_by_vector(q_vectors[0])
            
            # 2.3 【核心对齐 2】：根据得分决定 RAG 生成策略
            similarity = matched_faq["similarity"] if matched_faq else -1
            
            if matched_faq and similarity >= 0.8:
                # 达到 0.8 阈值，大模型参考外部知识进行第二轮修正生成
                log(f"{row_prefix} 命中库(相似度: {similarity:.4f}) -> 触发二级 RAG 润色")
                final_output = synthesizer_svc.synthesize(asr_text, raw_extraction, matched_faq)
            else:
                # 未达阈值，直接沿用第一轮裸抽的结果，不传递 matched_faq 干扰大模型
                log(f"{row_prefix} 未命中库(最高相似度: {similarity:.4f}) -> 保持一级提炼")
                final_output = raw_extraction

            # 2.4 【核心对齐 3】：像素级保留中间件比对痕迹
            results.append({
                "ASR": asr_text,
                "refined_question": core_question,
                "faq_question": matched_faq["question"] if matched_faq else "",
                "similarity": similarity,
                "final_output": final_output,
                "faq_answer": matched_faq["answer"] if matched_faq else ""
            })

        # --- 3. 产生双轨文件交付 ---
        log("所有数据流转完毕！正在物理落盘双份交付 Excel...")
        
        # 文件一：算法详细对齐表 (对应原项目的 detailed_FAQ_output.xlsx)
        local_detailed_path = os.path.join(self.work_dir, f"detailed_rag_{task_id}.xlsx")
        detailed_df = pd.DataFrame(results)
        # 严格控制列的物理顺序，与原项目完全一致
        detailed_df = detailed_df[["ASR", "refined_question", "faq_question", "similarity", "final_output", "faq_answer"]]
        detailed_df.to_excel(local_detailed_path, index=False)

        # 文件二：业务极简交付表 (原项目预留但未落盘的简版表，我们在微服务中真正吐给主后端)
        local_opt_path = os.path.join(self.work_dir, f"optASR_rag_{task_id}.xlsx")
        df["opt_ASR"] = [r["dynamic_output" if "dynamic_output" in r else "final_output"] for r in results]
        df.to_excel(local_opt_path, index=False)
        
        log("交付表格物理落盘成功。")
        return os.path.abspath(local_detailed_path), os.path.abspath(local_opt_path)