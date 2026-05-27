from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
import pandas as pd
import tempfile
from services.sentiment_auditor import SentimentAuditorService

router = APIRouter(prefix="/api/v1/sentiment", tags=["情感质检"])

# 实例化核心分析引擎
auditor_service = SentimentAuditorService()

@router.post("/batch_excel")
async def process_sentiment_batch(file: UploadFile = File(...)):
    """
    批量情感质检接口：接收原始 ASR Excel，调用大模型分析，返回包含评分与建议的详细 Excel。
    """
    # 1. 拦截非 Excel 文件格式
    if not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="只支持 .xlsx 或 .xls 格式的 Excel 文件")

    # 2. 读取用户上传的 Excel
    try:
        df = pd.read_excel(file.file)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"无法解析 Excel 文件: {str(e)}")

    # 3. 兼容原业务逻辑：寻找目标列，优先找 'ASR' 列
    target_col = "ASR" if "ASR" in df.columns else df.columns[0]
    
    rows = []
    
    # 4. 遍历数据，调用纯净的服务引擎进行打分
    for idx, row in df.iterrows():
        raw_text = str(row[target_col])
        
        # 核心：调用底层的解耦服务
        res_dict = auditor_service.process(raw_text)
        
        # 5. 结果映射：按照原项目要求的 5 列结构进行完美复刻
        rows.append({
            "ASR": raw_text,
            "情感评分": res_dict.get("score", -1),
            "情感结论": res_dict.get("sentiment", "解析失败"),
            # 原项目的依据要求是字符串，而底层返回的是 list，这里做 join 拼接
            "关键依据": ", ".join(res_dict.get("key_points", [])),
            "改进建议": res_dict.get("suggestions", "无")
        })
        
    # 6. 生成与原项目一致的结果表
    result_df = pd.DataFrame(rows)
    
    # 生成临时文件返回给客户端
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
    result_df.to_excel(temp_file.name, index=False)
    
    return FileResponse(
        path=temp_file.name, 
        filename=f"sentiment_analysis_{file.filename}",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )