from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import tempfile
import os
import shutil
from services.audio_conversation_parser import AudioConversationParserService

router = APIRouter(prefix="/api/v1/asr", tags=["音频转写"])

# 实例化核心服务
parser_service = AudioConversationParserService()

@router.post("/parse_single")
async def parse_single_audio(audio_file: UploadFile = File(...)):
    """
    单音频转写接口：接收前端上传的 .wav 文件，返回角色分离的对话文本。
    """
    # 1. 校验文件类型 (防御性编程)
    if not audio_file.filename.endswith((".wav", ".WAV")):
        raise HTTPException(status_code=400, detail="只支持 .wav 格式的音频文件")

    # 2. 将上传的文件保存到服务器的临时路径
    # 因为底层的 ASRClient (funasr/pyannote) 需要一个物理路径来读取音频
    try:
        # 创建带有 .wav 后缀的临时文件
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:
            #TODO:同样的问题，释放磁盘，清理临时文件。
            shutil.copyfileobj(audio_file.file, temp_audio)
            temp_path = temp_audio.name
    except Exception as e:
         raise HTTPException(status_code=500, detail=f"文件保存失败: {str(e)}")

    try:
        # 3. 调用底层解耦的服务引擎
        # 传入物理文件路径
        transcribed_text = parser_service.process(temp_path)
        
        # 4. 返回结构化 JSON 响应
        return JSONResponse(content={
            "filename": audio_file.filename, ##TODO:同样的问题，释放磁盘，上传文件仓库，写数据库，清理临时文件。
            "transcription": transcribed_text,
            "status": "success"
        })
    except Exception as e:
        # 如果模型崩溃，返回 500 错误
        raise HTTPException(status_code=500, detail=f"转写过程出错: {str(e)}")
    finally:
        # 5. 清理战场：不管成功还是失败，都必须删除临时音频文件，防止磁盘塞满
        if os.path.exists(temp_path):
            os.remove(temp_path)