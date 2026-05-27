# 本地路径：core_clients/asr_client.py
import requests
import os
from config.settings import ASR_API_URL

class ASRClient:
    """
    底层 ASR 通信客户端
    职责：将本地音频文件发往 79 服务器的模型网关，获取转写结果
    """
    def __init__(self):
        self.api_url = ASR_API_URL

    def transcribe(self, audio_file_path: str) -> str:
        if not os.path.exists(audio_file_path):
            print(f"[ASRClient] 本地文件不存在: {audio_file_path}")
            return ""

        try:
            # 以二进制流的方式打开本地音频，发送给服务器
            with open(audio_file_path, "rb") as f:
                files = {"file": (os.path.basename(audio_file_path), f, "audio/wav")}
                response = requests.post(self.api_url, files=files, timeout=300) # 音频处理可能较长，给 5 分钟超时
                
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