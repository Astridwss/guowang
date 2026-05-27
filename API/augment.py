import os
from pathlib import Path
import sys

# 确保能找到项目根目录
sys.path.append(str(Path(__file__).parent.parent))

from fastapi import APIRouter, UploadFile, File
from fastapi.responses import FileResponse
import pandas as pd
import tempfile
import os
from services.corpus_augmentor import CorpusAugmentorService

router = APIRouter(prefix="/api/v1/augmentation", tags=["语料增强"])

# 实例化我们的核心引擎
augmentor_service = CorpusAugmentorService()

@router.post("/batch_excel")
async def process_augmentation_batch(file: UploadFile = File(...)):
    """
    完全复刻原项目的业务逻辑：接收 optASR Excel，输出 detailed Excel
    """
    # 1. 读取用户上传的 Excel
    df = pd.read_excel(file.file)
    
    # 检查是否包含必需的列（兼容原业务逻辑）
    target_col = "opt_ASR" if "opt_ASR" in df.columns else df.columns[0]
    
    rows = []
    
    # 2. 遍历数据，调用纯净的服务引擎
    # （注：实际生产中可以使用 asyncio.gather 或 ThreadPoolExecutor 实现像原版一样的并发）
    for idx, row in df.iterrows():
        raw_text = str(row[target_col])
        
        # 核心：调用底层的解耦服务
        augmented_results = augmentor_service.process(raw_text)
        
        # 3. 结果映射：把服务返回的 list 拼装回原项目需要的列格式
        # 防止大模型返回异常，做安全防御
        aug_1 = augmented_results[0].get("dialogue", raw_text) if len(augmented_results) > 0 else raw_text
        aug_2 = augmented_results[1].get("dialogue", raw_text) if len(augmented_results) > 1 else raw_text
        aug_3 = augmented_results[2].get("dialogue", raw_text) if len(augmented_results) > 2 else raw_text
        
        rows.append({
            "opt_ASR原文": raw_text,
            "augment_1": aug_1,
            "augment_2": aug_2,
            "augment_3": aug_3
        })
        
    # 4. 生成与原项目完全一致的结果表
    result_df = pd.DataFrame(rows)
    
    # 生成临时文件返回给客户端
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
    #TODO:磁盘回收，把新 Excel 上传到对象存储（OSS）文件服务器，删除本地临时文件
    result_df.to_excel(temp_file.name, index=False)
    
    return FileResponse(
        path=temp_file.name, 
        filename=f"augmentation_detailed_{file.filename}",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

"""
应用服务生成 Excel 临时文件
调用 OSS SDK，把文件上传推送到对象存储服务器集群
上传成功拿到公开下载链接 / 资源路径
把这条链接 + 业务关联信息插入数据库表
立刻删除应用服务器本地临时文件
前端要下载：直接拿库里存的 OSS 地址直连下载，不走业务服务
"""