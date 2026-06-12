# 文件路径：api/routers/cluster_router.py
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from schemas.request_models import ClusterSubmitRequest
from schemas.response_models import TaskSubmitResponse, ClusterTaskStatusResponse
from core.state_manager import StateManager
from handlers.cluster_handler import ClusterTaskHandler

router = APIRouter(prefix="/api/v1/cluster", tags=["知识聚类可视化分析"])

@router.post("", response_model=TaskSubmitResponse, response_model_exclude_none=True)
async def submit_cluster_task(request: ClusterSubmitRequest, background_tasks: BackgroundTasks):
    task_id = request.task_id
    
    if not ClusterTaskHandler.initialize_task(task_id, request.work_dir):
        return {"task_id": task_id, "status": "already_exists", "message": "任务已存在或目录创建失败"}
    
    background_tasks.add_task(
        ClusterTaskHandler.execute_task, 
        task_id=task_id,
        work_dir=request.work_dir, 
        faq_file_url=request.faq_file_url, 
        dim_reduce=request.dim_reduce,
        clustering=request.clustering,
        n_clusters=request.n_clusters,
        llm_config=request.llm_config
    )
    return {"task_id": task_id, "status": "accepted"}

@router.get("", response_model=ClusterTaskStatusResponse)
async def poll_cluster_status(task_id: str = Query(..., description="任务ID")):
    task_info = StateManager.get_task(task_id)
    
    if not task_info:
        raise HTTPException(status_code=404, detail=f"找不到任务 ID: {task_id}")
        
    task_info["task_id"] = task_id
    return task_info