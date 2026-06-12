# 放 TaskSubmitRequest, ModelConfig
from pydantic import BaseModel
from typing import Optional, Dict

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

    # 3. 多模态模型配置 (负责多模态提炼与融合)
    vllm_base_url: Optional[str] = None
    vllm_api_key: Optional[str] = None
    vllm_model_name: Optional[str] = None

class RagTaskSubmitRequest(BaseModel):
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
    """聚类 POST 接口入参模型 (数据契约)"""
    work_dir: str
    task_id: str
    faq_file_url: str                                # 必须：带有"问题"列的表格
    dim_reduce: Optional[str] = "tsne"               # 可选：降维网络 (tsne 或 pca)
    clustering: Optional[str] = "hdbscan"            # 可选：聚类算法 (hdbscan 或 kmeans)
    n_clusters: Optional[int] = None                 # 可选：聚类数量 (KMeans 必填)
    llm_config: Optional[ModelConfig] = None         # 可选：向量大模型配置

class DocExtractionSubmitRequest(BaseModel):
    """图文抽取 POST 接口入参模型 (数据契约)"""
    work_dir: str
    task_id: str
    document_url: str                                # 必须：原始 .docx 操作手册路径
    llm_config: Optional[ModelConfig] = None         # 可选：多模态视觉大模型配置

class DesensitizationSubmitRequest(BaseModel):
    """数据脱敏 POST 接口入参模型"""
    work_dir: str
    task_id: str
    asr_file_url: str                                # 必须：待脱敏的原始客服对话 Excel 表格
    tooltip: Optional[Dict[str, str]] = None         # 可选：自定义敏感词映射字典, 例如 {"手机号": "PHONE"}
    llm_config: Optional[ModelConfig] = None         # 可选：大语言模型配置项

class SentimentAnalysisSubmitRequest(BaseModel):
    """话务情绪分析与智能质检 POST 接口入参契约"""
    work_dir: str
    task_id: str
    asr_file_url: str                                # 必须：待分析的原始客服对话 Excel 表格
    llm_config: Optional[ModelConfig] = None         # 可选：多模态/大模型底层运行配置