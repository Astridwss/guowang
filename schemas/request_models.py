# 放 TaskSubmitRequest, ModelConfig
from pydantic import BaseModel
from typing import Optional

class ModelConfig(BaseModel):
    """
    平台动态下发的双模型配置 (数据契约)
    所有参数设为 Optional，未传则由底层降级读取 settings.py
    """
    # 1. 通用大语言模型配置 (负责提炼与融合)
    chat_base_url: Optional[str] = None
    chat_api_key: Optional[str] = None
    chat_model_name: Optional[str] = None
    temperature: Optional[float] = None
    
    # 2. 向量嵌入模型配置 (负责计算特征向量)
    embed_base_url: Optional[str] = None
    embed_api_key: Optional[str] = None
    embed_model_name: Optional[str] = None


class TaskSubmitRequest(BaseModel):
    """话务 POST /api/v1/rag 接口入参模型 (数据契约)"""
    work_dir: str
    task_id: str
    asr_file_url: str                                # 必须: 原始话务 rawASR 表格路径
    faq_file_url: Optional[str] = None               # 可选: FAQ 知识表格路径 (当知识库不存在时必须提供)
    llm_config: Optional[ModelConfig] = None         # 可选: 平台下发的动态模型配置


class AugmentationSubmitRequest(BaseModel):
    """数据增强 POST 接口入参模型"""
    work_dir: str
    task_id: str
    source_file_url: str                             # 必须：原始对话 opt_ASR 表格路径
    llm_config: Optional[ModelConfig] = None         # 可选：平台下发的动态模型配置


class ClusterSubmitRequest(BaseModel):
    """聚类 POST 接口入参模型"""
    work_dir: str
    task_id: str
    faq_file_url: str                                # 必须：原始对话 FAQ 表格路径
    n_clusters: Optional[int] = None                 # 可选：聚类数量
    clustering: Optional[str] = None                 # 可选：聚类方式
    dim_reduce: Optional[str] = None                 # 可选：聚类网络
    llm_config: Optional[ModelConfig] = None         # 可选：平台下发的动态模型配置