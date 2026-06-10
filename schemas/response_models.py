'''
返回体结构的定义
：一是能自动生成极其标准的 Swagger UI 接口文档；二是能严格过滤返回字段，防止内部敏感信息泄露。
'''
from pydantic import BaseModel
from typing import Optional

class TaskSubmitResponse(BaseModel):
    task_id: str
    status: str
    message: Optional[str] = None

class TaskStatusResponse(BaseModel):
    """话务 GET /api/v1/rag 接口入参模型 (数据契约)"""
    task_id: str
    status: str
    result_detailed_file_url: str
    result_opt_file_url: str
    log: str