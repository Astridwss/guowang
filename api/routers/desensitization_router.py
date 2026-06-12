# 文件路径：api/routers/desensitization_router.py
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from schemas.request_models import DesensitizationSubmitRequest
from schemas.response_models import TaskSubmitResponse, DesensitizationTaskStatusResponse
from core.state_manager import StateManager
from handlers.desensitization_handler import DesensitizationTaskHandler

router = APIRouter(prefix="/api/v1/desentitize", tags=["话务脱敏与数据安全隔离"])

@router.post("", response_model=TaskSubmitResponse, response_model_exclude_none=True)
async def submit_desensitization_task(request: DesensitizationSubmitRequest, background_tasks: BackgroundTasks):
    """
    异步提交脱敏流水线任务
    """
    task_id = request.task_id
    
    # 互斥锁机制校验，防呆防并发重复发起
    if not DesensitizationTaskHandler.initialize_task(task_id, request.work_dir):
        return {"task_id": task_id, "status": "already_exists", "message": "该数据脱敏任务已在后台排队处理中，请勿重复发起！"}
    
    # 转交 FastAPI 专属后台轻量级线程池进行非阻塞异步流转
    background_tasks.add_task(
        DesensitizationTaskHandler.execute_task, 
        task_id=task_id,
        work_dir=request.work_dir, 
        asr_file_url=request.asr_file_url, 
        tooltip=request.tooltip,
        llm_config=request.llm_config
    )
    return {"task_id": task_id, "status": "accepted"}

@router.get("", response_model=DesensitizationTaskStatusResponse)
async def poll_desensitization_status(task_id: str = Query(..., description="脱敏任务ID")):
    """
    前端/主后端轮询脱敏任务流转进度与单轨 Excel 产物路径
    """
    task_info = StateManager.get_task(task_id)
    
    # 💡【顺序校准】：必须前置对 None 执行拦截，全面卡死 'NoneType' object has no attribute 报错！
    if not task_info:
        raise HTTPException(status_code=404, detail=f"在全网状态管理机中未能查找到数据脱敏任务 ID: {task_id}")
        
    # 安全回合并追加任务 ID
    task_info["task_id"] = task_id
    return task_info