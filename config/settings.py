# 文件路径：config/settings.py
import os

# ==========================================
# 核心网络防御 (解决 502 报错)
# 强制 Python 的所有网络请求绕过本地系统代理，防止被 Clash/公司代理拦截
# ==========================================
os.environ["NO_PROXY"] = "192.168.0.80,localhost,127.0.0.1"

# 环境变量控制，默认开发环境 (本地私有化部署)
ENV = os.environ.get("QA_ENV", "DEV")  

if ENV == "DEV":
    # ------------------------------------------
    # 1. 通用文本大模型配置 (负责提炼、打分、脱敏)
    # ------------------------------------------
    TEXT_LLM_URL = "http://192.168.0.80:8020/v1" 
    TEXT_LLM_KEY = "dummy-key"
    TEXT_MODEL_NAME = "Qwen/Qwen3.6-35B-A3B-GPTQ-Int8"
    
    # ------------------------------------------
    # 2. 视觉大模型配置 (负责 Word 图文提炼)
    # ------------------------------------------
    VL_LLM_URL = "http://192.168.0.79:8002/v1"
    VL_LLM_KEY = "dummy-vl-key"
    VL_MODEL_NAME = "/data/home/wangshan/guowang_LLM/Qwen2-VL-7B-Instruct"
    
    # ------------------------------------------
    # 3. 向量大模型配置 (负责构建 FAISS 知识库)
    # ------------------------------------------
    EMBEDDING_URL = "http://192.168.0.79:8003/v1" 
    EMBEDDING_KEY = "dummy-embedding-key"
    EMBEDDING_MODEL = "/data/home/wangshan/guowang_LLM/bge-large-zh-v1.5"
    
    # ------------------------------------------
    # 4. ASR 语音转写服务配置
    # ------------------------------------------
    ASR_API_URL = "http://192.168.0.79:9000/api/v1/audio/transcribe" #79服务器部署 启动命令 python ars_server.py
    ASR_API_KEY = "dummy-asr-key"
    
    # DEV 环境无需网关鉴权
    SYSTEM_CODE = None 
    
elif ENV == "PROD":
    # ------------------------------------------
    # 生产环境：严格对齐甲方 SGCC 生产网关文档
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
    
    # 生产环境必须携带的鉴权 Header
    SYSTEM_CODE = "sgcc_prod_code_123"