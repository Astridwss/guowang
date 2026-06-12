# 文件路径：api/handlers/sentiment_analysis_handler.py
import os
import asyncio
import traceback
from core.state_manager import StateManager
from utils.file_downloader import download_file
from use_cases.sentiment_orchestrator import SentimentOrchestratorPipelineEngine

class SentimentAnalysisTaskHandler:
    
    @classmethod
    def initialize_task(cls, task_id: str, work_dir: str) -> bool:
        """
        任务前置初始化，注册进状态机容器
        """
        return StateManager.create_task(task_id)

    @classmethod
    async def execute_task(
        cls, 
        task_id: str, 
        work_dir: str, 
        asr_file_url: str, 
        llm_config: any
    ):
        """
        异步流转执行话务情绪分析与智能质检流水线任务
        """
        # 激活状态机流转为处理中
        StateManager.set_processing(task_id)
        log_cb = lambda msg: StateManager.append_log(task_id, msg)
        
        # 💡【任务沙盒安全隔离】：将此并发任务派生出的所有数据绝对封闭在此子空间下
        task_sandbox_dir = os.path.join(work_dir, task_id)
        local_asr_path = None

        try:
            log_cb(f"正在拉取云端原始质检话务包，分流至任务专属安全隔离沙盒空间: {task_id}...\n")
            # 调度高级流式分块下载核心积木，只给沙盒目录，动态接回绝对路径
            local_asr_path = await download_file(asr_file_url, task_sandbox_dir)
            
            # 初始化情绪分析编排流水线引擎
            engine = SentimentOrchestratorPipelineEngine(work_dir=task_sandbox_dir)
            loop = asyncio.get_running_loop()
            
            # 💡【解耦重构】：丢进物理线程池，彻底解除大模型并发交互导致主异步循环的卡僵假死
            excel_res = await loop.run_in_executor(
                None, 
                engine.run, 
                task_id, 
                local_asr_path, 
                llm_config, 
                log_cb
            )
            
            # 💡【状态机契约对齐】：契合 Response 契约，精准回写单轨情绪质检 Excel 产物路径
            StateManager.set_success(task_id, result_excel_url=excel_res)
            
        except Exception as e:
            # 核心链路兜底保护与堆栈落盘打印
            traceback.print_exc()
            StateManager.set_failed(task_id, str(e))
            
        finally:
            # 沙盒主动安全擦除：仅安全抹除下载进沙盒的庞大原始 ASR 临时源文件，完美留存最终生成的 Excel 成果包
            if local_asr_path and os.path.exists(local_asr_path):
                try:
                    os.remove(local_asr_path)
                except Exception:
                    pass