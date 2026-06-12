import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from schemas.request_models import RagTaskSubmitRequest
from schemas.response_models import TaskSubmitResponse, RagTaskStatusResponse
from core.state_manager import StateManager
from handlers.rag_handler import RAGTaskHandler

router = APIRouter(prefix="/api/v1/rag", tags=["话务 RAG 全自动流水线"])

@router.post("", response_model=TaskSubmitResponse, response_model_exclude_none=True)
async def submit_rag_task(request: RagTaskSubmitRequest, background_tasks: BackgroundTasks):
    task_id = request.task_id
    
    # 1. 业务层校验
    if not RAGTaskHandler.initialize_task(task_id, request.work_dir):
        return {"task_id": task_id, "status": "already_exists", "message": "任务已在队列中，或创建工作目录失败"}

    # 直接调用调度器类的执行方法
    background_tasks.add_task(
        RAGTaskHandler.execute_task, 
        task_id, request.work_dir, request.asr_file_url, request.faq_file_url, request.llm_config
    )
    return {"task_id": task_id, "status": "accepted"}

@router.get("", response_model=RagTaskStatusResponse)
async def poll_rag_status(task_id: str = Query(..., description="要查询的任务ID")):
    task_info = StateManager.get_task(task_id)

    if not task_info:
        raise HTTPException(status_code=404, detail=f"找不到任务 ID: {task_id}")
    
    task_info["task_id"] = task_id
    return task_info