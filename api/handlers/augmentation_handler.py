import os
import asyncio
import time
import traceback


from core.state_manager import StateManager
from utils.file_downloader import download_file
from schemas.request_models import ModelConfig

# 导入纯粹的算法编排引擎
from use_cases.augmentation_orchestrator import AugmentationEngine

class AugmentationTaskHandler:
    """
    数据增强任务调度器 (Application Task Worker)
    职责：纯 Python 业务调度，无任何 Web 框架依赖。
    连接外部下载器、状态机与内部核心算法引擎。
    """
    
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
    async def execute_task(cls, task_id: str, work_dir: str, source_url: str, llm_config: ModelConfig):
        """
        异步方法：数据增强流水线的实际执行者。
        """
        # 1. 切换状态机至执行中
        StateManager.set_processing(task_id)
        
        # 2. 规约物理存储路径
        task_sandbox_dir = os.path.join(work_dir, task_id)
        # local_input_path = os.path.join(work_dir, f"aug_input_{task_id}.xlsx")
        
        # 3. 定义无状态的日志回调闭包
        log_cb = lambda msg: StateManager.append_log(task_id, msg)

        try:
            # --- 阶段 A：网络 I/O ---
            log_cb(f"[{time.strftime('%H:%M:%S')}] 正在拉取源对话表格...\n")
            local_input_path = await download_file(source_url, task_sandbox_dir)

            log_cb(f"[{time.strftime('%H:%M:%S')}] 文件下载就绪，移交引擎执行并发裂变...\n")
            
            # --- 阶段 B：CPU 与大模型计算密集型任务 ---
            # 实例化引擎，固定最大并发数为 16（避免前端传参打爆内存）
            engine = AugmentationEngine(work_dir=task_sandbox_dir, max_workers=16)
            loop = asyncio.get_running_loop()
            
            # 将同步的重度计算扔进线程池，彻底防止主线程阻塞
            excel_path, chart_path = await loop.run_in_executor(
                None, 
                engine.run, 
                task_id, 
                local_input_path, 
                llm_config, 
                log_cb
            )

            # --- 阶段 C：成功闭环 ---
            StateManager.set_success(
                task_id, 
                result_file_url=excel_path
            )

        except Exception as e:
            # 异常兜底落库，并在控制台打印详细堆栈以供运维排查
            traceback.print_exc()
            StateManager.set_failed(task_id, str(e))
            
        finally:
            # --- 阶段 D：清理物理战壕 ---
            # 用完即焚，保证系统磁盘永远不会被临时文件撑爆
            if os.path.exists(local_input_path): 
                os.remove(local_input_path)