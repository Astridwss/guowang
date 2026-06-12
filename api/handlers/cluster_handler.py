import os
import asyncio
from core.state_manager import StateManager
from utils.file_downloader import download_file
from use_cases.cluster_orchestrator import ClusterPipelineEngine

class ClusterTaskHandler:
    
    @classmethod
    def initialize_task(cls, task_id: str, work_dir: str) -> bool:
        if not os.path.exists(work_dir):
            os.makedirs(work_dir, exist_ok=True)
        return StateManager.create_task(task_id)

    @classmethod
    async def execute_task(
        cls, 
        task_id: str, 
        work_dir: str, 
        faq_file_url: str, 
        dim_reduce: str, 
        clustering: str, 
        n_clusters: int, 
        llm_config: any
    ):
        StateManager.set_processing(task_id)
        task_sandbox_dir = os.path.join(work_dir, task_id)
        # local_faq_path = os.path.join(work_dir, f"input_cluster_{task_id}.xlsx")
        log_cb = lambda msg: StateManager.append_log(task_id, msg)
        
        try:
            log_cb("正在拉取云端 FAQ 语料库文件...\n")
            local_faq_path = await download_file(faq_file_url, task_sandbox_dir)
            
            engine = ClusterPipelineEngine(work_dir=work_dir)
            loop = asyncio.get_running_loop()
            
            # 执行聚类引擎，拿到 HTML 路径
            html_path = await loop.run_in_executor(
                None, engine.run, task_id, local_faq_path, dim_reduce, clustering, n_clusters, llm_config, log_cb
            )
            
            # 使用前面重构的通用状态写入方法，键名与 Pydantic 响应模型严格一致！
            StateManager.set_success(task_id, result_html_url=html_path)
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            StateManager.set_failed(task_id, str(e))
            
        finally:
            if os.path.exists(local_faq_path):
                os.remove(local_faq_path)