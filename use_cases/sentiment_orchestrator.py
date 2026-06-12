import os
import sys
import time
import pandas as pd
import concurrent.futures
from typing import Callable, Dict, Tuple

# 将项目根目录加入系统路径，确保组件可跨目录独立引入
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.sentiment_analysis import SentimentAnalysisService

class SentimentOrchestratorPipelineEngine:
    """
    情绪分析质检应用编排引擎 (Application Service Layer)
    职责：管理线程池并发调度、控制行序一致性恢复、输出轻量单轨 Excel 结构化产物。
    """
    def __init__(self, work_dir: str):
        self.work_dir = work_dir

    @staticmethod
    def _process_single_row_flat(
        index: int,
        asr_text: str,
        auditor_svc: SentimentAnalysisService
    ) -> Tuple[int, int, str, str, str]:
        """
        静态独立单行子处理器。
        不包含对外部高层变量的任何隐式闭包依赖，满足可 Picklable 序列化要求，
        方便未来无缝向多进程池 (Multiprocessing) 或 Celery 分布式任务队列迁移。
        """
        try:
            # 调度底层无状态质检组件
            res = auditor_svc.process(asr_text)
            
            score = res.get("score", 60)
            sentiment = res.get("sentiment", "中性")
            
            # 将多行依据列表合并为 Excel 单单元格更易读的换行纯文本
            evidence_list = res.get("evidence", [])
            evidence = "\n".join(evidence_list) if isinstance(evidence_list, list) else str(evidence_list)
            
            suggestions = res.get("suggestions", "无")
            return index, score, sentiment, evidence, suggestions
        except Exception as e:
            # 行级高级容错保护，单行崩溃不影响大盘流水线
            return index, 60, "处理异常", f"大模型调用发生非预期阻断: {str(e)}", "无"

    def run(
        self,
        task_id: str,
        local_excel_path: str,
        llm_config: any,
        log_callback: Callable[[str], None]
    ) -> str:
        """
        启动批量话务情绪质检流水线
        """
        def log(msg: str):
            log_callback(f"[{time.strftime('%H:%M:%S')}] {msg}\n")

        # 1. 业务数据预读与契约强校验
        log(f"开始解析本地待质检话务文件: {os.path.basename(local_excel_path)}")
        df = pd.read_excel(local_excel_path)
        
        # 兼容 "ASR" 或 "ASR原文" 列名
        asr_col = "ASR" if "ASR" in df.columns else ("ASR原文" if "ASR原文" in df.columns else None)
        if not asr_col:
            raise KeyError("数据契约校验异常：传入的 Excel 表格中未能找到标准的 'ASR' 会话文本列！")

        # 2. 动态提取 API 传入的 llm_config 运行期配置，初始化服务积木
        base_url = llm_config.chat_base_url if llm_config else None
        api_key = llm_config.chat_api_key if llm_config else None
        model_name = llm_config.chat_model_name if llm_config else None

        auditor_svc = SentimentAnalysisService(
            base_url=base_url,
            api_key=api_key,
            model_name=model_name
        )

        # 3. 驱动高性能多线程池，显式传参调度
        log(f"高性能并发智能质检通道全开，批处理总行数: {len(df)} 条。")
        results_collector = []
        
        # 安全平滑并发上限设置为 16，防瞬时高并发冲垮大模型网关
        max_workers = min(16, len(df))
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_idx = {
                executor.submit(
                    self._process_single_row_flat,
                    idx,
                    str(row[asr_col]),
                    auditor_svc
                ): idx
                for idx, row in df.iterrows()
            }
            
            for future in concurrent.futures.as_completed(future_to_idx):
                idx = future_to_idx[future]
                try:
                    index, score, sentiment, evidence, suggestions = future.result()
                    log_callback(f"智能质检进度汇报：[会话切片 {idx + 1}/{len(df)}] 情感特征多维度分析完成。\n")
                    
                    results_collector.append({
                        "original_index": index,
                        "ASR": str(df.loc[index, asr_col]),
                        "情感评分": score,
                        "情感结论": sentiment,
                        "关键依据": evidence,
                        "改进建议": suggestions
                    })
                except Exception as exc:
                    log_callback(f"⚠️ [系统块处理错误] 话务索引 {idx} 发生意外挂起: {str(exc)}\n")

        # 4. 强力行序重排：利用 original_index 恢复数据原本在 Excel 中的视觉顺序
        sorted_df = pd.DataFrame(results_collector).sort_values(by="original_index").drop(columns=["original_index"])

        # 5. 轻量结构化 Excel 结果物理落盘
        output_excel_path = os.path.join(self.work_dir, f"sentiment_audited_{task_id}.xlsx")
        sorted_df.to_excel(output_excel_path, index=False)
        
        log("✅ 客服满意度智能质检任务链圆满闭环，单轨结果文件已成功落盘！")
        return os.path.abspath(output_excel_path)