# 文件路径：use_cases/desensitization_orchestrator.py
import os
import time
import pandas as pd
import concurrent.futures
from typing import Callable, Dict, Tuple

# 引入底层无状态能力积木
from services.data_desensitizer import DataDesensitizerService

class DesensitizationPipelineEngine:
    """
    智能脱敏流水线编排引擎 (Application Service Layer)
    职责：统筹调度高性能多线程池、组装和清洗 Excel 话务明细。
    """
    def __init__(self, work_dir: str):
        self.work_dir = work_dir

    @staticmethod
    def _process_single_row(
        index: int,
        asr_text: str,
        desens_svc: DataDesensitizerService,
        tooltip: Dict[str, str],
        model_name: str
    ) -> Tuple[int, str, int, str, str]:
        """
        💡【优雅重构点 1】：将原本的嵌套 worker 彻底抽离为独立的私有静态方法。
        依赖全部显式参数化，100% 具备可测试性，且完全满足可 Picklable 序列化要求。
        """
        try:
            # 将每一行的动态 Prompt 编译与交互完全移交 Service 积木层
            d_text, s_count, d_type, s_map = desens_svc.process_line(asr_text, tooltip, model_name)
            return index, d_text, s_count, d_type, s_map
        except Exception as e:
            # 行级高级容错保护
            return index, f"大模型调用抛出异常: {str(e)}", 0, "错误", "{}"

    def run(
        self,
        task_id: str,
        local_excel_path: str,
        tooltip: Dict[str, str],
        llm_config: any,
        log_callback: Callable[[str], None]
    ) -> str:
        
        def log(msg: str):
            log_callback(f"[{time.strftime('%H:%M:%S')}] {msg}\n")

        # 1. 业务表格数据加载与前置校验
        log(f"开始解析本地待处理话务源文件: {os.path.basename(local_excel_path)}")
        df = pd.read_excel(local_excel_path)
        if "ASR" not in df.columns:
            raise KeyError("数据契约校验异常：待脱敏的 Excel 中未能找到标准的 'ASR' 会话明细列！")

        # 2. 初始化核心算法能力积木
        desens_svc = DataDesensitizerService(
            base_url=llm_config.chat_base_url if llm_config else None,
            api_key=llm_config.chat_api_key if llm_config else None,
            model_name=llm_config.chat_model_name if llm_config else None
        )
        model_name = llm_config.chat_model_name if llm_config else "Qwen/QwQ-32B-AWQ"

        # 3. 构建高性能工作线程池，并发驱动大模型
        log(f"高性能并发脱敏通道全启，批处理总量: {len(df)} 条记录。")
        rows = []
        
        # 限制并发度最大为16
        max_workers = min(16, len(df))
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 💡【优雅重构点 2】：利用 executor.submit 的多参数传递特性，将变量显式灌入处理器
            future_to_idx = {
                executor.submit(
                    self._process_single_row,  # 任务目标函数
                    idx,                       # 参数 1: 行索引
                    str(row["ASR"]),           # 参数 2: 待脱敏原文
                    desens_svc,                # 参数 3: 算法积木实例
                    tooltip,                   # 参数 4: 敏感词词典
                    model_name                 # 参数 5: 模型名称
                ): idx 
                for idx, row in df.iterrows()
            }
            
            for future in concurrent.futures.as_completed(future_to_idx):
                idx = future_to_idx[future]
                try:
                    index, d_text, s_count, d_type, s_map = future.result()
                    log_callback(f"脱敏流水线进度汇报：[会话切片 {idx + 1}/{len(df)}] 处理并收口成功。\n")
                    rows.append({
                        "original_index": index,
                        "ASR原文": str(df.loc[index, "ASR"]),
                        "脱敏后文本": d_text,
                        "脱敏字段数量": s_count,
                        "脱敏类型": d_type,
                        "敏感信息映射": s_map
                    })
                except Exception as exc:
                    log_callback(f"⚠️ [系统块警告] 线程切片索引 {idx} 内部数据发生阻断: {str(exc)}\n")

        # 4. 排序恢复因多线程并发引发的交错行序
        sorted_rows = pd.DataFrame(rows).sort_values(by="original_index").drop(columns=["original_index"])

        # 5. 结构化 Excel 产物物理沙盒落盘
        output_excel_path = os.path.join(self.work_dir, f"desensitized_{task_id}.xlsx")
        sorted_rows.to_excel(output_excel_path, index=False)
        
        log("✅ 数据脱敏编排引擎任务闭环，结构化结果顺利落盘！")
        return os.path.abspath(output_excel_path)