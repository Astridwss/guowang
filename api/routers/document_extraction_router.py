from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from schemas.request_models import DocExtractionSubmitRequest
from schemas.response_models import TaskSubmitResponse, DocExtractionTaskStatusResponse
from core.state_manager import StateManager
from handlers.document_extraction_handler import DocExtractionTaskHandler

router = APIRouter(prefix="/api/v1/document_extraction", tags=["文档解析与多模态抽取"])

@router.post("", response_model=TaskSubmitResponse, response_model_exclude_none=True)
async def submit_doc_extraction_task(request: DocExtractionSubmitRequest, background_tasks: BackgroundTasks):
    task_id = request.task_id
    
    if not DocExtractionTaskHandler.initialize_task(task_id, request.work_dir):
        return {"task_id": task_id, "status": "already_exists", "message": "任务已存在或目录创建失败"}
    
    background_tasks.add_task(
        DocExtractionTaskHandler.execute_task, 
        task_id=task_id,
        work_dir=request.work_dir, 
        document_url=request.document_url, 
        llm_config=request.llm_config
    )
    return {"task_id": task_id, "status": "accepted"}

@router.get("", response_model=DocExtractionTaskStatusResponse)
async def poll_doc_extraction_status(task_id: str = Query(..., description="任务ID")):
    task_info = StateManager.get_task(task_id)
    
    if not task_info:
        raise HTTPException(status_code=404, detail=f"找不到任务 ID: {task_id}")
        
    task_info["task_id"] = task_id
    return task_info