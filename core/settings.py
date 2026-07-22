
import os


# os.environ["NO_PROXY"] = "192.168.0.80,192.168.0.79,localhost,127.0.0.1,25.222.64.60"


# TEXT_LLM_URL = "http://192.168.0.80:8020/v1" 
# TEXT_LLM_KEY = "dummy-key"
# TEXT_MODEL_NAME = "Qwen/Qwen3.6-35B-A3B-GPTQ-Int8"

# VL_LLM_URL = "http://192.168.0.79:8002/v1"
# VL_LLM_KEY = "dummy-vl-key"
# VL_MODEL_NAME = "/data/home/wangshan/guowang_LLM/Qwen2-VL-7B-Instruct"

# EMBEDDING_URL = "http://192.168.0.79:8003/v1" 
# EMBEDDING_KEY = "dummy-embedding-key"
# EMBEDDING_MODEL = "/data/home/wangshan/guowang_LLM/bge-large-zh-v1.5"

# ASR_API_URL = "http://192.168.0.79:9000/api/v1/audio/transcribe"
# ASR_API_KEY = "dummy-asr-key"



TEXT_LLM_URL = "http://25.222.64.60:80/lmp-cloud-ias-server/api/llm/chat/completions/V2"
TEXT_LLM_KEY = "fd5dac19a44d43468dd31c96a65610e3"
TEXT_MODEL_NAME = "SGGM-NLP-80B-R"

VL_LLM_URL = "http://25.222.64.60:80/lmp-cloud-ias-server/api/vlm/chat/completions/V2"
VL_LLM_KEY = "fd5dac19a44d43468dd31c96a65610e3"
VL_MODEL_NAME = "SGGM-VL-27B-R"

EMBEDDING_URL = "http://egw.jn.js.sgcc.com.cn/gte/v1"
EMBEDDING_KEY = "YOUR_SGCC_PROD_KEY"
EMBEDDING_MODEL = "gte-large"

ASR_API_URL = "http://egw.jn.js.sgcc.com.cn/asr/v1/transcribe"
ASR_API_KEY = "YOUR_SGCC_PROD_KEY"

