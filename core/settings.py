# 文件路径：core/settings.py
import os

# ==========================================
# 核心网络防御 (解决 502 报错)
# ==========================================
os.environ["NO_PROXY"] = "192.168.0.80,localhost,127.0.0.1"

# 环境变量控制，默认开发环境
ENV = os.environ.get("QA_ENV", "DEV")  

if ENV == "DEV":
    # ------------------------------------------
    # DEV 环境配置
    # ------------------------------------------
    TEXT_LLM_URL = "http://192.168.0.80:8020/v1" 
    TEXT_LLM_KEY = "dummy-key"
    TEXT_MODEL_NAME = "Qwen/Qwen3.6-35B-A3B-GPTQ-Int8"
    
    VL_LLM_URL = "http://192.168.0.79:8002/v1"
    VL_LLM_KEY = "dummy-vl-key"
    VL_MODEL_NAME = "/data/home/wangshan/guowang_LLM/Qwen2-VL-7B-Instruct"
    
    EMBEDDING_URL = "http://192.168.0.79:8003/v1" 
    EMBEDDING_KEY = "dummy-embedding-key"
    EMBEDDING_MODEL = "/data/home/wangshan/guowang_LLM/bge-large-zh-v1.5"
    
    ASR_API_URL = "http://192.168.0.79:9000/api/v1/audio/transcribe"
    ASR_API_KEY = "dummy-asr-key"
    
    # DEV 环境无网关鉴权，Header 为空
    GLOBAL_HEADERS = {}
    
elif ENV == "PROD":
    # ------------------------------------------
    # PROD 生产环境配置
    # ------------------------------------------
    TEXT_LLM_URL = "http://egw.jn.js.sgcc.com.cn/qwen3/32b/v1"
    TEXT_LLM_KEY = "YOUR_SGCC_PROD_KEY"
    TEXT_MODEL_NAME = "Qwen3-32B"
    
    VL_LLM_URL = "http://egw.jn.js.sgcc.com.cn/qwen-vl/v1"
    VL_LLM_KEY = "YOUR_SGCC_PROD_KEY"
    VL_MODEL_NAME = "Qwen-VL-Pro"
    
    EMBEDDING_URL = "http://egw.jn.js.sgcc.com.cn/gte/v1"
    EMBEDDING_KEY = "YOUR_SGCC_PROD_KEY"
    EMBEDDING_MODEL = "gte-large"
    
    ASR_API_URL = "http://egw.jn.js.sgcc.com.cn/asr/v1/transcribe"
    ASR_API_KEY = "YOUR_SGCC_PROD_KEY"
    
    SYSTEM_CODE = "sgcc_prod_code_123"
    
    # 生产环境必须携带的鉴权 Header (这里需要你替换成局方要求的真实 Header 字段名)
    GLOBAL_HEADERS = {
        "X-System-Code": SYSTEM_CODE,           # 假设局方要求的键名是 X-System-Code
        # "Authorization": f"Bearer {TEXT_LLM_KEY}" # 如果有些接口要求 Token 放 Header 也可以塞这里
    }