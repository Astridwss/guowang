# 文件路径：api/routers/augmentation_router.py
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from schemas.request_models import AugmentationSubmitRequest
from schemas.response_models import TaskSubmitResponse, AugmentationTaskStatusResponse
from core.state_manager import StateManager
from handlers.augmentation_handler import AugmentationTaskHandler

router = APIRouter(prefix="/api/v1/augmentation", tags=["数据增强并发流水线"])

@router.post("", response_model=TaskSubmitResponse, response_model_exclude_none=True)
async def submit_augmentation_task(request: AugmentationSubmitRequest, background_tasks: BackgroundTasks):
    task_id = request.task_id
    
    # 1. 业务层校验
    if not AugmentationTaskHandler.initialize_task(task_id, request.work_dir):
        return {"task_id": task_id, "status": "already_exists", "message": "任务已在队列中，或创建工作目录失败"}
    
    # 2. 框架层派发：用 FastAPI 专属武器把干活方法甩进后台
    background_tasks.add_task(
        AugmentationTaskHandler.execute_task, 
        task_id,
        request.work_dir, 
        request.source_file_url, 
        request.llm_config
    )
    
    return {"task_id": task_id, "status": "accepted"}

@router.get("", response_model=AugmentationTaskStatusResponse)
async def poll_augmentation_status(task_id: str = Query(..., description="任务ID")):
    """轮询增强任务进度与产物结果"""
    task_info = StateManager.get_task(task_id)

    # 1. 先进行判空拦截！如果找不到任务，直接抛出 404 错误返回给前端
    if not task_info:
        raise HTTPException(status_code=404, detail=f"找不到任务 ID: {task_id}")
        
    # 2. 确认 task_info 存在（是一个字典）后，再追加 task_id 字段
    task_info["task_id"] = task_id
    
    return task_info