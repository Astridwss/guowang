# 文件路径：services/rag_task_handler.py
import os
import asyncio
import time
from utils.file_downloader import download_file
from core.state_manager import StateManager
from use_cases.rag_orchestrator import RAGPipelineEngine
from schemas.request_models import ModelConfig

class RAGTaskHandler:
    """RAG 后台任务调度器：负责组装下载器、状态机与编排引擎"""

    @classmethod
    def initialize_task(cls, task_id: str, work_dir: str) -> bool:
        """
        同步方法：【统一管理】状态校验、占坑、以及动态目录的安全创建。
        """
        # 1. 统一在这里确保动态目录存在，后续业务无需再关心
        if not os.path.exists(work_dir):
            try:
                os.makedirs(work_dir, exist_ok=True)
            except Exception as e:
                print(f"[Handler 错误] 创建动态工作目录失败: {str(e)}")
                return False
                
        # 2. 状态机占坑
        return StateManager.create_task(task_id)

    @classmethod
    async def execute_task(cls, task_id: str, work_dir:str, asr_url: str, faq_url: str, llm_config: ModelConfig):
        StateManager.set_processing(task_id)
        StateManager.append_log(task_id, f"[{time.strftime('%H:%M:%S')}] 任务启动...\n")
        
        task_sandbox_dir = os.path.join(work_dir, task_id)
        
        # 消除闭包：使用 lambda 或直接提取为一个类方法
        log_cb = lambda msg: StateManager.append_log(task_id, msg)

        try:
            log_cb(f"[{time.strftime('%H:%M:%S')}] 正在拉取目标源文件...\n")
            local_asr_path = await download_file(asr_url, task_sandbox_dir)
            if faq_url:
                local_faq_path = await download_file(faq_url, task_sandbox_dir)

            log_cb(f"[{time.strftime('%H:%M:%S')}] 文件准备完毕，开始 AI 计算...\n")
            
            engine = RAGPipelineEngine(work_dir=task_sandbox_dir, db_dir=task_sandbox_dir)
            loop = asyncio.get_running_loop()
            detailed_path, opt_path = await loop.run_in_executor(
                None, engine.run, task_id, local_asr_path, local_faq_path, llm_config, log_cb
            )

            StateManager.set_success(
                task_id, 
                result_detailed_file_url=detailed_path, 
                result_opt_file_url=opt_path
            )

        except Exception as e:
            import traceback
            traceback.print_exc()
            StateManager.set_failed(task_id, str(e))
            
        finally:
            if os.path.exists(local_asr_path): os.remove(local_asr_path)
            if faq_url and os.path.exists(local_faq_path): os.remove(local_faq_path)