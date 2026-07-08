# 文件路径：core/config.py
import os

from httpx import request
from core import settings

# ==========================================
# 1. 核心路径计算与安全防护
# ==========================================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# WORK_DIR = os.path.join(BASE_DIR, "data", "workspace")
# DB_DIR = os.path.join(BASE_DIR, "database")

# os.makedirs(WORK_DIR, exist_ok=True)
# os.makedirs(DB_DIR, exist_ok=True)

# ==========================================
# 2. 统一暴露降级配置
# ==========================================
# ENV = settings.ENV

# Text LLM
TEXT_LLM_URL = settings.TEXT_LLM_URL
TEXT_LLM_KEY = settings.TEXT_LLM_KEY
TEXT_MODEL_NAME = settings.TEXT_MODEL_NAME

# VL LLM
VL_LLM_URL = settings.VL_LLM_URL
VL_LLM_KEY = settings.VL_LLM_KEY
VL_MODEL_NAME = settings.VL_MODEL_NAME

# Embedding
EMBEDDING_URL = settings.EMBEDDING_URL
EMBEDDING_KEY = settings.EMBEDDING_KEY
EMBEDDING_MODEL = settings.EMBEDDING_MODEL

# ASR
ASR_API_URL = settings.ASR_API_URL
ASR_API_KEY = settings.ASR_API_KEY

# 全局鉴权 Header
#GLOBAL_HEADERS = settings.GLOBAL_HEADERS