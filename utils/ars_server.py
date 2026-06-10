from fastapi import FastAPI, UploadFile, File
import uvicorn
import os
import tempfile
from funasr import AutoModel

app = FastAPI(title="本地纯离线 ASR 引擎")

print("正在通过代理拉取并装载音频三剑客至 GPU 0...")

# 究极重构：只用 FunASR 官方注册的短名称！
# 只要有网，FunASR 就会自动去 ModelScope 拉取最完美的代码和权重，彻底告别路径报错
model = AutoModel(
    model="paraformer-zh",   # 官方原生支持的短名称
    vad_model="fsmn-vad",      # 官方原生支持的短名称
    spk_model="campplus",      # 官方原生支持的短名称
    punc_model="ct-punc",      # 🌟 新增：标点符号恢复 (专治 punc_res 报错)
    trust_remote_code=True,
    device="cuda:0",
)

print("装载完成！接口服务待命。")

@app.post("/api/v1/audio/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    """接收客户端上传的音频文件并进行离线转写"""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:
        temp_audio.write(await file.read())
        temp_audio_path = temp_audio.name

    # try:
    #     res = model.generate(
    #         input=temp_audio_path,
    #         cache={}, language="zh", use_itn=True, batch_size_s=60, merge_vad=True, merge_length_s=15
    #     )

    #     raw_text = res[0].get("text", "") if res else ""
    #     clean_text = raw_text.replace("<|SPEAKER_00|>", "\n客服: ") \
    #                          .replace("<|SPEAKER_01|>", "\n客户: ") \
    #                          .replace("<|SPEAKER_02|>", "\n第三方: ")

    #     return {"code": 200, "text": clean_text.strip()}
    # except Exception as e:
    #     return {"code": 500, "error": str(e)}
    try:
        # 这一步将极其丝滑，Paraformer 会输出完美的时间戳和说话人数组
        res = model.generate(
            input=temp_audio_path,
            cache={}, language="zh", use_itn=True, batch_size_s=60, merge_vad=True, merge_length_s=15
        )
        
        # === 适配 Paraformer 工业级解析逻辑 ===
        # 提取结构化数组，里面包含了每一句话的文本 (text)、开始时间 (start)、结束时间 (end) 和 说话人 (spk)
        sentence_info = res[0].get("sentence_info", [])
        
        if sentence_info:
            clean_text = ""
            for item in sentence_info:
                spk = item.get("spk", 0)    # 获取说话人编号，默认为 0
                text = item.get("text", "") # 获取这一句的纯文本
                
                # 动态拼接带角色的文本
                if spk == 0:
                    clean_text += f"\n客服: {text}"
                elif spk == 1:
                    clean_text += f"\n客户: {text}"
                elif spk == 2:
                    clean_text += f"\n第三方: {text}"
                else:
                    clean_text += f"\n未知角色{spk}: {text}"
        else:
            # 降级防御：如果某种原因没有生成 sentence_info，直接返回纯文本
            clean_text = res[0].get("text", "")
            
        return {"code": 200, "text": clean_text.strip()}
        
    except Exception as e:
        import traceback
        traceback.print_exc() 
        return {"code": 500, "error": str(e)}
    finally:
        os.remove(temp_audio_path)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=9000)