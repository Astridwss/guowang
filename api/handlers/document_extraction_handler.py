# 文件路径：api/handlers/document_extraction_handler.py
import os
import asyncio
import shutil
from core.state_manager import StateManager
from utils.file_downloader import download_file
from use_cases.document_extraction_orchestrator import DocumentExtractionPipelineEngine

class DocExtractionTaskHandler:
    
    @classmethod
    def initialize_task(cls, task_id: str, work_dir: str) -> bool:
        """同步初始化：任务在通用状态机占坑"""
        return StateManager.create_task(task_id)

    @classmethod
    async def execute_task(
        cls, 
        task_id: str, 
        work_dir: str, 
        document_url: str, 
        llm_config: any
    ):
        StateManager.set_processing(task_id)
        log_cb = lambda msg: StateManager.append_log(task_id, msg)
        
        # 💡【架构对齐】：将该任务产生的所有物理垃圾、图片、输入输出，严格隔离在独立的沙盒路径下
        task_sandbox_dir = os.path.join(work_dir, task_id)
        
        # 前置局部变量声明，万无一失地防御 UnboundLocalError
        local_docx_path = None

        try:
            log_cb(f"正在拉取原始操作手册，分流至任务安全隔离沙盒空间: {task_id}...\n")
            
            # 💡【下载器对齐】：只传沙盒目录，动态接住流式下载器返回的物理绝对路径
            local_docx_path = await download_file(document_url, task_sandbox_dir)
            
            # 💡.doc拦截
            if local_docx_path.lower().endswith(".doc"):
                log_cb("❌ 格式拦截：底层抽取引擎仅支持新版 OpenXML 格式 (.docx)，不支持老旧二进制格式 (.doc)，任务强行终止！\n")
                StateManager.set_failed(task_id, "格式不兼容 (.doc)")
                return

            log_cb(f"原始文件已在沙盒中安全着陆: {os.path.basename(local_docx_path)}，拉起多模态重编排引擎...\n")
            
            # 初始化编排引擎，并直接注入沙盒目录作为其基座
            engine = DocumentExtractionPipelineEngine(work_dir=task_sandbox_dir)
            loop = asyncio.get_running_loop()
            
            # 丢进物理线程池，全面放开主循环，支持极高并发的路由状态轮询
            result_excel_path = await loop.run_in_executor(
                None, engine.run, task_id, local_docx_path, llm_config, log_cb
            )
            
            # 💡【状态机对齐】：以高度通用的关键字参数，将成功的 Excel 绝对路径回传给状态机
            StateManager.set_success(task_id, result_excel_url=result_excel_path)
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            StateManager.set_failed(task_id, str(e))
            
        finally:
            # 💡【沙盒清理防线】：用完后，只安全擦除下载进沙盒里的那个庞大的原始 docx 文件，保留生成的 excel 产物和图片
            if local_docx_path and os.path.exists(local_docx_path):
                try:
                    os.remove(local_docx_path)
                except Exception as ex:
                    print(f"[Handler 垃圾清理异常] 无法物理释放源文件 {local_docx_path}: {str(ex)}")