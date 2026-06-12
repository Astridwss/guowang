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

class RagTaskStatusResponse(BaseModel):
    """话务 RAG GET 接口返回契约"""
    task_id: str
    status: str
    result_detailed_file_url: Optional[str] = ""
    result_opt_file_url: Optional[str] = ""
    log: str

class AugmentationTaskStatusResponse(BaseModel):
    """数据增强 GET 接口返回契约"""
    task_id: str
    status: str
    result_file_url: Optional[str] = ""  # 数据增强通常只有1个产物文件
    log: str

class ClusterTaskStatusResponse(BaseModel):
    """知识聚类 接口返回契约"""
    task_id: str
    status: str
    result_html_url: Optional[str] = ""  # 聚类专属产物：3D可视化网页
    log: str

class DocExtractionTaskStatusResponse(BaseModel):
    """图文抽取 接口返回契约"""
    task_id: str
    status: str
    result_excel_url: Optional[str] = ""             # 图文抽取专属产物：结构化 FAQ 表格
    log: str

class DesensitizationTaskStatusResponse(BaseModel):
    """数据脱敏 接口返回契契约"""
    task_id: str
    status: str
    result_excel_url: Optional[str] = ""             # 产物1：脱敏后的明细 Excel 文件路径
    #result_image_url: Optional[str] = ""             # 产物2：脱敏字段数量分布统计图路径
    log: str

class SentimentTaskStatusResponse(BaseModel):
    """情绪分析 接口返回契约"""
    task_id: str
    status: str
    result_excel_url: Optional[str] = ""             # 产物：情绪质检完备的 Excel 表格物理路径
    log: str