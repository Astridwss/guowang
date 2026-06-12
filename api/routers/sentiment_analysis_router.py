# 文件路径：api/routers/sentiment_analysis_router.py
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from schemas.request_models import SentimentAnalysisSubmitRequest
from schemas.response_models import TaskSubmitResponse, SentimentTaskStatusResponse
from core.state_manager import StateManager
from handlers.sentiment_analysis_handler import SentimentAnalysisTaskHandler

# 初始化路由元数据，绑定专属前缀与 Swagger UI 标签分组
router = APIRouter(prefix="/api/v1/sentiment_analysis", tags=["话务情绪分析与智能质检"])

@router.post("", response_model=TaskSubmitResponse, response_model_exclude_none=True)
async def submit_sentiment_task(request: SentimentAnalysisSubmitRequest, background_tasks: BackgroundTasks):
    """
    异步提交话务情绪分析与智能质检流水线任务
    """
    task_id = request.task_id
    
    # 💡【高并发互斥防呆】：通过状态机原子化锁校验，防止前端或上游因网络抖动重复发起相同任务
    if not SentimentAnalysisTaskHandler.initialize_task(task_id, request.work_dir):
        return {
            "task_id": task_id, 
            "status": "already_exists", 
            "message": "该话务情绪分析任务已在后台排队或处理中，请勿重复发起！"
        }
    
    # 💡【非阻塞异步流转】：交由 FastAPI 专属后台轻量级 Worker 线程池，保障 HTTP 握手瞬间响应
    # 注意：根据 Sentiment 契约，此处完美去除了脱敏业务特有的 tooltip 参数
    background_tasks.add_task(
        SentimentAnalysisTaskHandler.execute_task, 
        task_id=task_id,
        work_dir=request.work_dir, 
        asr_file_url=request.asr_file_url, 
        llm_config=request.llm_config
    )
    return {"task_id": task_id, "status": "accepted"}

@router.get("", response_model=SentimentTaskStatusResponse)
async def poll_sentiment_status(task_id: str = Query(..., description="情绪分析质检任务ID")):
    """
    前端 / 主后端分布式轮询：实时捕获智能质检任务流转进度、动态日志与最终单轨 Excel 产物物理路径
    """
    # 从状态机全局单例容器中检索任务上下文
    task_info = StateManager.get_task(task_id)
    
    # 💡【全局边界防御】：强流式拦截空指针，彻底卡死 Python 隐式 'NoneType' 导致的运行时崩溃
    if not task_info:
        raise HTTPException(
            status_code=404, 
            detail=f"在分布式全网状态管理器中未能查找到有效的情绪分析任务 ID: {task_id}"
        )
        
    # 完美对齐出参契约：动态合并拼装任务 ID 键值对，回传结构化数据大包
    task_info["task_id"] = task_id
    return task_info