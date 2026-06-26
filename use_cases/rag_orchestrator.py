# 文件路径：use_cases/rag_orchestrator.py
import os
import time
import pandas as pd
from typing import Callable, Tuple
import re

# 导入底层能力积木
from services.document_splitter import DocumentSplitterService
from services.dialogue_extractor import DialogueExtractorService
from services.vector_embedding import VectorEmbeddingService
from services.index_store import IndexStoreService
from services.knowledge_retriever import KnowledgeRetrieverService
from services.rag_synthesizer import RAGSynthesizerService


class RAGPipelineEngine:
    """
    话务 RAG 流水线编排引擎
    """

    def __init__(self, work_dir: str = None, db_dir: str = None):
        self.work_dir = work_dir
        self.db_dir = db_dir or work_dir

    def _parse_core_question(self, text: str) -> str:
        """
        正则扣出问题（带防溢出边界保护）
        """
        text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()
        match = re.search(r'(?:问题|核心问题)[:：]\s*(.*?)(?=\n所属业务域|\n答案|$)', text, flags=re.DOTALL)
        return match.group(1).strip() if match else text.strip()

    def _parse_core_answer(self, text: str) -> str:
        """
        正则扣出答案全量内容（开启换行穿透，支持跨行提取多级步骤）
        """
        text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()
        match = re.search(r'(?:答案|核心答案)[:：]\s*(.*)', text, flags=re.DOTALL)
        return match.group(1).strip() if match else ""

    def run(
        self,
        task_id: str,
        local_asr_path: str,
        local_faq_path: str,
        llm_config: any,
        log_callback: Callable[[str], None]
    ) -> Tuple[str, str]:

        def log(msg):
            log_callback(f"[{time.strftime('%H:%M:%S')}] {msg}\n")

        # =========================
        # 0. 服务初始化
        # =========================
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

        # =========================
        # 1. FAQ知识库检测
        # =========================
        has_valid_kb = False
        db_index_path = os.path.join(self.db_dir, "faiss.index")

        if os.path.exists(db_index_path):
            has_valid_kb = True
            log("检测到已有FAQ向量库，启用RAG模式")
        else:
            log("未检测到FAQ向量库，尝试自动建库")
            if local_faq_path and os.path.exists(local_faq_path):
                valid_texts, payloads = splitter_svc.process_faq_excel(local_faq_path)

                # ===== 空FAQ保护 =====
                if not valid_texts:
                    log("FAQ.xlsx为空，无有效数据，切换盲提炼模式")
                else:
                    vectors_ndarray = embedding_svc.vectorize(valid_texts)

                    if vectors_ndarray is None or len(vectors_ndarray) == 0:
                        log("向量生成失败，切换盲提炼模式")
                    else:
                        store = IndexStoreService(db_dir=self.db_dir)
                        if store.build_and_save(vectors_ndarray, payloads):
                            has_valid_kb = True
                            log("FAQ自动建库成功")
                        else:
                            log("数据库写入失败，切换盲提炼模式")
            else:
                log("无FAQ文件，切换盲提炼模式")

        # =========================
        # 2. 初始化检索器
        # =========================
        retriever_svc = None
        if has_valid_kb:
            retriever_svc = KnowledgeRetrieverService(db_dir=self.db_dir, threshold=-1)
        else:
            log("当前任务无知识库，仅使用DialogueExtractor")

        # =========================
        # 3. ASR处理
        # =========================
        df = pd.read_excel(local_asr_path)
        target_col = "ASR" if "ASR" in df.columns else df.columns[1]
        
        results = []
        total_rows = len(df)

        for idx, row in df.iterrows():
            asr_text = str(row[target_col])
            
            if not asr_text.strip() or asr_text.lower() in ['nan', 'nat', 'none']:
                continue

            row_prefix = f"[{idx+1}/{total_rows}]"

            # =====================
            # 第一轮盲提炼 (只获取原有 contract 的两个字段)
            # =====================
            extracted = extractor_svc.extract(asr_text)
            core_question = extracted.get("core_question", "")
            raw_extraction = extracted.get("raw_extraction", "")

            matched_faq = None
            similarity = -1

            # =====================
            # 第二轮 RAG
            # =====================
            if has_valid_kb and core_question:
                q_vectors = embedding_svc.vectorize([core_question])
                if q_vectors is not None and len(q_vectors) > 0:
                    matched_faq = retriever_svc.retrieve_by_vector(q_vectors[0])

            if matched_faq:
                similarity = matched_faq["similarity"]

            # =====================
            # 最终输出逻辑优化
            # =====================
            if matched_faq and similarity >= 0.8:
                log(f"{row_prefix} 命中FAQ {similarity:.4f}")
                final_output = synthesizer_svc.synthesize(
                    asr_text,
                    raw_extraction,
                    matched_faq
                )
                final_q = self._parse_core_question(final_output)
                final_a = self._parse_core_answer(final_output)
            else:
                log(f"{row_prefix} 无有效FAQ，采用一级提炼结果")
                final_output = raw_extraction
                
                # ⭐ 完美对齐思路：
                # 1. 提炼出的问题直接映射 final_q
                final_q = core_question
                # 2. 从盲提炼原始文本中，通过正则直接提炼出答案，无需修改 dialogue_extractor 任何契约
                final_a = self._parse_core_answer(raw_extraction)

            results.append({
                "ASR": asr_text,
                "refined_question": core_question,
                "faq_question": matched_faq["question"] if matched_faq else "",
                "similarity": similarity,
                "final_output": final_output,
                "final_output_question": final_q,
                "final_output_answer": final_a,
                "faq_answer": matched_faq["answer"] if matched_faq else ""
            })

        # =========================
        # 4. 输出Excel
        # =========================
        detailed_path = os.path.join(self.work_dir, f"detailed_rag_{task_id}.xlsx")
        detailed_df = pd.DataFrame(results)

        detailed_df = detailed_df[[
            "ASR",
            "refined_question",
            "faq_question",
            "similarity",
            "final_output",
            "final_output_question",
            "final_output_answer",
            "faq_answer"
        ]]

        detailed_df.to_excel(detailed_path, index=False)

        opt_path = os.path.join(self.work_dir, f"optASR_rag_{task_id}.xlsx")
        
        df["opt_ASR"] = [r["final_output"] for r in results]
        df.to_excel(opt_path, index=False)

        log("全部处理完成")
        
        return os.path.abspath(detailed_path), os.path.abspath(opt_path)