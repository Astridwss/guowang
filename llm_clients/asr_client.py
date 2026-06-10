# 本地路径：core_clients/asr_client.py
import requests
import os
from core.settings import ASR_API_URL

class ASRClient:
    """
    底层 ASR 通信客户端
    """
    # 👇 增加动态参数接收口
    def __init__(self, api_url=None):
        # 优先使用动态 url，否则使用 settings 的兜底
        self.api_url = api_url or ASR_API_URL

    def transcribe(self, audio_file_path: str) -> str:
        if not os.path.exists(audio_file_path):
            print(f"[ASRClient] 本地文件不存在: {audio_file_path}")
            return ""

        try:
            with open(audio_file_path, "rb") as f:
                files = {"file": (os.path.basename(audio_file_path), f, "audio/wav")}
                response = requests.post(self.api_url, files=files, timeout=300) 
                
                response.raise_for_status()
                data = response.json()
                
                if data.get("code") == 200:
                    return data.get("text", "")
                else:
                    print(f"[ASRClient] 服务器端处理报错: {data.get('error')}")
                    return ""
                    
        except requests.exceptions.RequestException as e:
            print(f"[ASRClient] 请求 79 服务器 ASR 接口失败: {e}")
            return ""