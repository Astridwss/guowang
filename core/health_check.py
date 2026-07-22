# health_check.py
import os
import time
import logging
import asyncio
import base64
import traceback

from core import settings

logger = logging.getLogger("LLMHealthChecker")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

FALLBACK_TINY_IMAGE = "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAP//////////////////////////////////////////////////////////////////////////////////////wgALCAABAAEBAREA/8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQABPxA="


def _detect_api_format(url: str) -> str:
    """根据 URL 特征自动判断 API 格式"""
    if not url:
        return "unknown"
    if "/v1" in url or ":8000" in url or ":8002" in url or ":8020" in url:
        # 本地 vLLM / OpenAI 兼容服务
        return "openai"
    if "lmp-cloud-ias-server" in url or "/api/llm/" in url or "/api/vlm/" in url:
        # 平台网关
        return "gateway"
    return "unknown"


def load_vllm_check_image_base64() -> str:
    """动态安全加载自检图片 Base64"""
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        local_image_path = os.path.join(current_dir, "vllm_picture.png")
        if os.path.exists(local_image_path):
            with open(local_image_path, "rb") as image_file:
                encoded = base64.b64encode(image_file.read()).decode("utf-8")
                ext = "png" if local_image_path.lower().endswith(".png") else "jpeg"
                return f"data:image/{ext};base64,{encoded}"
        logger.warning(f"⚠️ 未找到本地自检图片 [{local_image_path}]，启用内置兜底")
        return FALLBACK_TINY_IMAGE
    except Exception as e:
        logger.warning(f"⚠️ 加载本地自检图片失败: {e}，启用内置兜底")
        return FALLBACK_TINY_IMAGE


def _format_response_for_log(content: str) -> str:
    """截断过长的响应内容用于日志"""
    if not content:
        return "<空响应>"
    content = content.strip()
    if len(content) > 500:
        return content[:500] + f"... (截断，共 {len(content)} 字符)"
    return content


# ============ 根据配置动态导入对应的 client ============
_api_format = _detect_api_format(getattr(settings, "TEXT_LLM_URL", ""))

if _api_format == "gateway":
    from llm_clients.llm_client_bk import UnifiedLLMClient
    logger.info(f"[连通性测试] 检测到平台网关格式，使用平台网关 (requests 原生)")
    _IMAGE_NEEDS_PREFIX = True  # 平台网关需要 data:image 前缀
else:
    from llm_clients.llm_client import UnifiedLLMClient
    logger.info(f"[连通性测试] 检测到 OpenAI 兼容格式，使用 OpenAI SDK")
    _IMAGE_NEEDS_PREFIX = False  # OpenAI 格式需要纯 base64


async def check_text_llm_connectivity():
    """通过 UnifiedLLMClient.chat_text() 验证文本大模型连通性"""
    start_time = time.time()
    url = getattr(settings, "TEXT_LLM_URL", "unknown")
    model_name = getattr(settings, "TEXT_MODEL_NAME", "unknown")

    try:
        logger.info(f"🔍 [LLM 连通性自检拉起] 目标地址: {url} | 校验模型: {model_name} | 格式: {_api_format}")

        client = UnifiedLLMClient(model_type="text")

        result = await asyncio.wait_for(
            asyncio.to_thread(
                client.chat_text,
                prompt="你好",
                system_prompt="你是一个 helpful assistant，请用一句话回复。"
            ),
            timeout=10.0
        )

        elapsed = time.time() - start_time

        if result and result.strip():
            logger.info(
                f"✅ [LLM 连通性自检成功] 耗时: {elapsed:.2f}s | 模型: {model_name}\n"
                f"   ├─ 模型回复: {_format_response_for_log(result)}\n"
                f"   └─ 说明: client.chat_text() 调用链路完整通畅"
            )
        else:
            logger.warning(
                f"⚠️ [LLM 连通性自检异常] 耗时: {elapsed:.2f}s | 模型: {model_name}\n"
                f"   ├─ 异常原因: client.chat_text() 返回空字符串\n"
                f"   ├─ 可能原因: 模型返回异常、鉴权失败被静默处理、或响应解析失败\n"
                f"   └─ 建议: 检查 llm_client 内部日志，确认服务端是否返回了有效内容"
            )

    except asyncio.TimeoutError:
        elapsed = time.time() - start_time
        logger.warning(
            f"⚠️ [LLM 连通性自检超时] 耗时: {elapsed:.2f}s \n"
            f"   ├─ 目标地址: {url}\n"
            f"   ├─ 校验模型: {model_name}\n"
            f"   ├─ 异常原因: client.chat_text() 调用超时\n"
            f"   └─ 可能原因: 网络不通、服务未启动、模型加载中、或业务超时设置过长"
        )
    except Exception as e:
        elapsed = time.time() - start_time
        logger.warning(
            f"⚠️ [LLM 连通性自检阻断] 耗时: {elapsed:.2f}s\n"
            f"   ├─ 目标地址: {url}\n"
            f"   ├─ 校验模型: {model_name}\n"
            f"   ├─ 异常类型: {type(e).__name__}\n"
            f"   ├─ 异常信息: {str(e)}\n"
            f"   └─ 堆栈跟踪:\n{traceback.format_exc()}"
        )


async def check_vlm_connectivity():
    """通过 UnifiedLLMClient.chat_vision() 验证视觉大模型连通性"""
    start_time = time.time()
    url = getattr(settings, "VL_LLM_URL", "unknown")
    model_name = getattr(settings, "VL_MODEL_NAME", "unknown")

    try:
        logger.info(f"🔍 [VLLM 连通性自检拉起] 目标地址: {url} | 校验模型: {model_name} | 格式: {_api_format}")

        check_image_base64 = load_vllm_check_image_base64()

        # 根据 API 格式决定是否去掉 data:image 前缀
        if _IMAGE_NEEDS_PREFIX:
            pure_base64 = check_image_base64  # 平台网关需要完整前缀
            logger.info(f"🔍 [图片格式]: 平台网关格式 (带 data:image 前缀, {len(pure_base64)} 字符)")
        else:
            pure_base64 = check_image_base64.split(",", 1)[1] if "," in check_image_base64 else check_image_base64
            logger.info(f"🔍 [图片格式]: OpenAI 兼容格式 (纯 base64, {len(pure_base64)} 字符)")

        client = UnifiedLLMClient(model_type="vision")

        result = await asyncio.wait_for(
            asyncio.to_thread(
                client.chat_vision,
                prompt="这张图片是什么？",
                image_base64=pure_base64,
                system_prompt="你是一个视觉助手，请用一句话描述图片。"
            ),
            timeout=15.0
        )

        elapsed = time.time() - start_time

        if result and result.strip():
            logger.info(
                f"✅ [VLLM 连通性自检成功] 耗时: {elapsed:.2f}s | 模型: {model_name}\n"
                f"   ├─ 模型回复: {_format_response_for_log(result)}\n"
                f"   └─ 说明: client.chat_vision() 调用链路完整通畅"
            )
        else:
            logger.warning(
                f"⚠️ [VLLM 连通性自检异常] 耗时: {elapsed:.2f}s | 模型: {model_name}\n"
                f"   ├─ 异常原因: client.chat_vision() 返回空字符串\n"
                f"   ├─ 可能原因: 模型返回异常、图片格式不被接受、或响应解析失败\n"
                f"   └─ 建议: 检查 llm_client 内部日志，确认图片 base64 格式是否符合模型要求"
            )

    except asyncio.TimeoutError:
        elapsed = time.time() - start_time
        logger.warning(
            f"⚠️ [VLLM 连通性自检超时] 耗时: {elapsed:.2f}s\n"
            f"   ├─ 目标地址: {url}\n"
            f"   ├─ 校验模型: {model_name}\n"
            f"   ├─ 异常原因: client.chat_vision() 调用超时\n"
            f"   └─ 可能原因: 网络不通、服务未启动、模型加载中、或 VLM 推理耗时过长"
        )
    except Exception as e:
        elapsed = time.time() - start_time
        logger.warning(
            f"⚠️ [VLLM 连通性自检阻断] 耗时: {elapsed:.2f}s\n"
            f"   ├─ 目标地址: {url}\n"
            f"   ├─ 校验模型: {model_name}\n"
            f"   ├─ 异常类型: {type(e).__name__}\n"
            f"   ├─ 异常信息: {str(e)}\n"
            f"   └─ 堆栈跟踪:\n{traceback.format_exc()}"
        )


async def run_all_llm_health_checks():
    """异步并发执行全部自检，绝对不阻塞 FastAPI 服务的启动"""
    logger.info(" [大模型连通性测试] 正在后台发起大模型连通性与鉴权测试...")
    results = await asyncio.gather(
        check_text_llm_connectivity(),
        check_vlm_connectivity(),
        return_exceptions=True
    )
    for res in results:
        if isinstance(res, Exception):
            logger.warning(
                f"⚠️ [大模型连通性测试] 测试任务内部抛出未捕获异常\n"
                f"   ├─ 异常类型: {type(res).__name__}\n"
                f"   ├─ 异常信息: {str(res)}\n"
                f"   └─ 堆栈跟踪:\n{traceback.format_exc()}"
            )
    logger.info("[大模型连通性测试] 测试完毕。")