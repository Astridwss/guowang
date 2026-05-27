import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core_clients.asr_client import ASRClient

class AudioConversationParserService:
    """
    音频转写组件 (纯粹积木)
    输入：本地 .wav 音频路径
    输出：带角色分离的对话纯文本
    """
    def __init__(self):
        self.asr_client = ASRClient()

    def process(self, audio_file_path: str) -> str:
        if not os.path.exists(audio_file_path):
            print(f"[ASR_Service] 找不到音频文件: {audio_file_path}")
            return ""
            
        print(f"[ASR_Service] 正在请求音频转写: {os.path.basename(audio_file_path)}")
        raw_text = self.asr_client.transcribe(audio_file_path)
        return raw_text.strip() if raw_text else ""