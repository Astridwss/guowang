import os
import time
import json
import logging
import concurrent.futures
import pandas as pd
import matplotlib
matplotlib.use('Agg') 
import matplotlib.pyplot as plt
from typing import Callable, Tuple, Optional

# 导入底层能力积木 (原子服务)
from services.corpus_augmentor import CorpusAugmentorService

class AugmentationEngine:
    """
    数据增强核心编排引擎 (Application Service Layer)
    职责：统筹 Pandas 读写、多线程并发调度、调用语料增强服务，以及图表生成。
    """
    def __init__(self, work_dir: str = None, max_workers: int = 16):
        self.work_dir = work_dir
        self.max_workers = max_workers

    def _process_single_dialogue(self, asr_text: str, augmentor_svc: CorpusAugmentorService) -> Tuple:
        """单条数据的处理闭包，隔离异常，防止单条失败导致整体崩溃"""
        try:
            # 直接调用底层的业务服务进行 1 扩 3
            results = augmentor_svc.process(str(asr_text))
            
            # 安全解析返回的列表字典 [{}, {}, {}]
            augment_1 = results[0].get("dialogue", asr_text) if len(results) > 0 else asr_text
            augment_2 = results[1].get("dialogue", asr_text) if len(results) > 1 else asr_text
            augment_3 = results[2].get("dialogue", asr_text) if len(results) > 2 else asr_text
            
            full_output = json.dumps(results, ensure_ascii=False) if results else "空返回"
            
            return asr_text, augment_1, augment_2, augment_3, full_output
            
        except Exception as e:
            logging.error(f"增强彻底失败，跳过: {str(e)}")
            return asr_text, asr_text, asr_text, asr_text, f"处理失败: {str(e)}"

    def run(self, task_id: str, local_input_path: str, llm_config: Optional[any], log_callback: Callable[[str], None]) -> Tuple[str, str]:
        """执行主编排流水线"""
        def log(msg: str):
            log_callback(f"[{time.strftime('%H:%M:%S')}] {msg}\n")

        # 1. 初始化底层语料增强服务
        # 注意：此处统一使用了 UnifiedLLMClient，如果未来需要支持前端动态切换模型，
        # 可以在 CorpusAugmentorService 的 __init__ 中预留 config 注入参数。
        augmentor_svc = CorpusAugmentorService(
            base_url=llm_config.chat_base_url if llm_config else None,
            api_key=llm_config.chat_api_key if llm_config else None,
            model_name=llm_config.chat_model_name if llm_config else None,
            temperature=llm_config.temperature if llm_config else None
        )

        # 2. 读取并校验数据
        log("正在解析原始会话表格...")
        df = pd.read_excel(local_input_path)
        target_col = "opt_ASR" if "opt_ASR" in df.columns else df.columns[0]
        
        if "opt_ASR" not in df.columns:
            log(f"⚠️ 未找到 opt_ASR 列，自动降级使用首列: {target_col}")

        # 3. 多线程并发请求
        total_rows = len(df)
        log(f"启动语料裂变加速引擎 (并发数: {self.max_workers})，总任务量: {total_rows} 条...")
        
        args_list = [
            (str(row[target_col]), augmentor_svc) 
            for _, row in df.iterrows() if pd.notna(row[target_col])
        ]
        
        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 使用 executor.map 并发，同时通过外部日志回调播报进度
            for i, res in enumerate(executor.map(lambda args: self._process_single_dialogue(*args), args_list)):
                results.append(res)
                if (i + 1) % 10 == 0 or (i + 1) == len(args_list):
                    log(f"并发进度: {i + 1} / {len(args_list)} 条已完成裂变。")

        # 4. 数据落盘 (Excel)
        log("拼装裂变数据矩阵，准备生成最终表格...")
        detailed_df = pd.DataFrame([
            {"opt_ASR原文": r[0], "augment_1": r[1], "augment_2": r[2], "augment_3": r[3]}
            for r in results
        ])
        excel_out_path = os.path.join(self.work_dir, f"aug_detailed_{task_id}.xlsx")
        detailed_df.to_excel(excel_out_path, index=False)

        # 5. 生成统计图表 (PNG)
        log("正在计算特征分布并渲染统计直方图...")
        plot_out_path = os.path.join(self.work_dir, f"aug_distribution_{task_id}.png")
        
        plt.figure(figsize=(12, 8))
        plt.hist([
            [len(str(t)) for t in detailed_df["opt_ASR原文"]],
            [len(str(t)) for t in detailed_df["augment_1"]],
            [len(str(t)) for t in detailed_df["augment_2"]],
            [len(str(t)) for t in detailed_df["augment_3"]]
        ], bins=30, alpha=0.7, label=["Original", "Version 1", "Version 2", "Version 3"])
        
        plt.title(f"Task {task_id} - Text Length Distribution")
        plt.xlabel("Text Length (characters)")
        plt.ylabel("Frequency")
        plt.legend()
        plt.grid(axis="y", alpha=0.75)
        plt.savefig(plot_out_path, dpi=300)
        plt.close() # 释放内存

        log("✅ 所有语料裂变流转完毕，产物已成功物理落盘。")
        return os.path.abspath(excel_out_path), os.path.abspath(plot_out_path)