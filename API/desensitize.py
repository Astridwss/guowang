from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
import pandas as pd
import tempfile
from services.data_desensitizer import DataDesensitizerService

router = APIRouter(prefix="/api/v1/desensitize", tags=["数据脱敏"])

# 实例化核心脱敏引擎
desensitizer_service = DataDesensitizerService()

@router.post("/batch_excel")
async def process_desensitize_batch(file: UploadFile = File(...)):
    """
    批量数据脱敏接口：接收包含 ASR 列的 Excel，返回脱敏后的详细 Excel。
    """
    # 1. 拦截非 Excel 文件格式
    if not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="只支持 .xlsx 或 .xls 格式的 Excel 文件")

    try:
        df = pd.read_excel(file.file)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"无法解析 Excel 文件: {str(e)}")

    # 2. 寻找目标列，优先找 'ASR' 列
    target_col = "ASR" if "ASR" in df.columns else df.columns[0]
    
    rows = []
    
    # 3. 遍历数据处理
    for idx, row in df.iterrows():
        raw_text = str(row[target_col])
        
        # 调用底层纯净引擎，拿到 { "safe_text": "...", "mappings": {...} }
        result = desensitizer_service.process(raw_text)
        
        safe_text = result.get("safe_text", "")
        mappings = result.get("mappings", {})
        
        # ---------------------------------------------------------
        # API 层的业务补全逻辑：根据原项目复刻“数量”和“类型”计算
        # ---------------------------------------------------------
        sensitive_count = len(mappings)
        
        desensitized_types = []
        for key in mappings.keys():
            key_upper = key.upper()
            if "ACCOUNT" in key_upper:
                desensitized_types.append("账号")
            elif "PASSWORD" in key_upper:
                desensitized_types.append("密码")
            elif "ORDER_ID" in key_upper:
                desensitized_types.append("订单号")
            elif "PRICE" in key_upper:
                desensitized_types.append("金额")
            elif "PHONE" in key_upper:
                desensitized_types.append("电话")
            elif "EMPLOYEE_ID" in key_upper:
                desensitized_types.append("人员编号")
            else:
                desensitized_types.append("其他敏感信息")
                
        # 去重并拼接成字符串
        desensitized_types_str = ", ".join(list(set(desensitized_types))) if desensitized_types else "无"
        
        # 4. 组装成原项目所需要的 5 列数据格式
        rows.append({
            "ASR原文": raw_text,
            "脱敏后文本": safe_text,
            "脱敏字段数量": sensitive_count,
            "脱敏类型": desensitized_types_str,
            "敏感信息映射": str(mappings)  # 原项目要求存为字符串形式
        })
        
    # 5. 生成结果 DataFrame 并输出为 Excel
    result_df = pd.DataFrame(rows)
    
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
    result_df.to_excel(temp_file.name, index=False)
    
    return FileResponse(
        path=temp_file.name, 
        filename=f"desensitization_{file.filename}",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )