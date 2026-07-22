import os
import time
import logging
import asyncio
import base64
import httpx
import traceback
import json

from core import settings

# 强行使用系统日志格式，输出 INFO/WARN 级别的调测信息
logger = logging.getLogger("LLMHealthChecker")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# 1像素透明极小 JPEG 图片 Base64，用于兜底保护
FALLBACK_TINY_IMAGE = "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAP//////////////////////////////////////////////////////////////////////////////////////wgALCAABAAEBAREA/8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQABPxA="


def load_vllm_check_image_base64() -> str:
    """
    动态安全加载自检图片 Base64，绝对定位 core/vllm_picture.png
    """
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        local_image_path = os.path.join(current_dir, "vllm_picture.png")

        if os.path.exists(local_image_path):
            with open(local_image_path, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
                ext = "png" if local_image_path.lower().endswith(".png") else "jpeg"
                return f"data:image/{ext};base64,{encoded_string}"
        else:
            logger.warning(f"⚠️ 未找到本地自检图片 [{local_image_path}]，自动启用内置极小图片兜底")
            return FALLBACK_TINY_IMAGE
    except Exception as e:
        logger.warning(f"⚠️ 加载本地自检图片失败: {e}，自动启用内置极小图片兜底")
        return FALLBACK_TINY_IMAGE


def _format_response_body(res_text: str) -> str:
    """格式化响应体，过长时截断"""
    if not res_text:
        return "<空响应>"
    try:
        # 尝试 JSON 美化
        parsed = json.loads(res_text)
        formatted = json.dumps(parsed, ensure_ascii=False, indent=2)
        if len(formatted) > 2000:
            return formatted[:2000] + f"\n... (截断，共 {len(formatted)} 字符)"
        return formatted
    except json.JSONDecodeError:
        if len(res_text) > 2000:
            return res_text[:2000] + f"\n... (截断，共 {len(res_text)} 字符)"
        return res_text


def _extract_model_reply(res_text: str) -> str:
    """从大模型响应中提取 assistant 的回复内容"""
    try:
        parsed = json.loads(res_text)
        # 平台网关格式
        if "choices" in parsed and len(parsed["choices"]) > 0:
            choice = parsed["choices"][0]
            if "message" in choice and "content" in choice["message"]:
                return choice["message"]["content"]
            # OpenAI 流式/标准格式
            if "delta" in choice and "content" in choice["delta"]:
                return choice["delta"]["content"]
        # 其他可能的格式
        if "content" in parsed:
            return parsed["content"]
        if "text" in parsed:
            return parsed["text"]
        if "result" in parsed:
            return str(parsed["result"])
        return "<无法提取回复内容>"
    except Exception:
        return "<响应解析失败>"


def _extract_error_reason(res_text: str, status_code: int) -> str:
    """从错误响应中提取具体失败原因"""
    reasons = []
    reasons.append(f"HTTP状态码: {status_code}")

    try:
        parsed = json.loads(res_text)

        # 常见错误字段提取
        if "detail" in parsed:
            reasons.append(f"错误详情: {parsed['detail']}")
        if "error" in parsed:
            err = parsed["error"]
            if isinstance(err, dict):
                if "message" in err:
                    reasons.append(f"错误消息: {err['message']}")
                if "type" in err:
                    reasons.append(f"错误类型: {err['type']}")
                if "code" in err:
                    reasons.append(f"错误代码: {err['code']}")
            else:
                reasons.append(f"错误: {err}")
        if "message" in parsed:
            reasons.append(f"消息: {parsed['message']}")
        if "code" in parsed:
            reasons.append(f"代码: {parsed['code']}")

        # 根据状态码给出常见原因提示
        if status_code == 401:
            reasons.append("💡 可能原因: API Key 无效或缺失，请检查 Authorization 头")
        elif status_code == 403:
            reasons.append("💡 可能原因: 权限不足，API Key 无访问该模型的权限")
        elif status_code == 404:
            reasons.append("💡 可能原因: URL 路径错误，或服务未启动，或模型不存在")
        elif status_code == 429:
            reasons.append("💡 可能原因: 请求频率过高，触发限流")
        elif status_code == 500:
            reasons.append("💡 可能原因: 服务端内部错误，模型推理异常")
        elif status_code == 502:
            reasons.append("💡 可能原因: 网关错误，后端服务未响应")
        elif status_code == 503:
            reasons.append("💡 可能原因: 服务暂时不可用，模型正在加载中")

    except json.JSONDecodeError:
        reasons.append(f"原始响应: {res_text[:500]}")

    return " | ".join(reasons)


async def check_text_llm_connectivity():
    """
    语义文本大模型 (CHAT) 连通性与鉴权自检
    """
    start_time = time.time()
    try:
        url = getattr(settings, "TEXT_LLM_URL", "http://25.222.64.60:80/lmp-cloud-ias-server/api/llm/chat/completions/V2")
        api_key = getattr(settings, "TEXT_LLM_KEY", "fd5dac19a44d43468dd31c96a65610e3")
        model_name = getattr(settings, "TEXT_MODEL_NAME", "SGGM-NLP-80B-R")

        headers = {
            "Content-Type": "application/json;charset=utf-8",
            "Authorization": api_key
        }

        payload = {
            "model": model_name,
            "messages": [
                {
                    "role": "user",
                    "content": "你好，介绍下北京"
                }
            ],
            "stream": False,
            "temperature": 0.95,
            "top_p": 0.7,
            "presence_penalty": 1,
            "modelVersion": ""
        }

        logger.info(f"🔍 [LLM 连通性自检拉起] 目标地址: {url} | 校验模型: {model_name}")

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            elapsed = time.time() - start_time
            res_text = response.text

            if response.status_code == 200:
                # ✅ 成功：打印模型返回的回复内容
                reply = _extract_model_reply(res_text)
                usage_info = ""
                try:
                    parsed = json.loads(res_text)
                    if "usage" in parsed and parsed["usage"]:
                        usage = parsed["usage"]
                        if isinstance(usage, dict):
                            usage_info = f" | Token消耗: prompt={usage.get('prompt_tokens', '?')}, completion={usage.get('completion_tokens', '?')}, total={usage.get('total_tokens', '?')}"
                        else:
                            usage_info = f" | Token消耗: {usage}"
                except Exception:
                    pass

                logger.info(
                    f"✅ [LLM 连通性自检成功] 状态码: 200 | 耗时: {elapsed:.2f}s | 模型: {model_name}{usage_info}\n"
                    f"   ├─ 模型回复: {reply}\n"
                    f"   └─ 完整响应: {_format_response_body(res_text)}"
                )
            else:
                # ❌ 失败：打印详细错误原因
                error_reason = _extract_error_reason(res_text, response.status_code)
                logger.warning(
                    f"⚠️ [LLM 连通性自检异常] 耗时: {elapsed:.2f}s\n"
                    f"   ├─ 失败原因: {error_reason}\n"
                    f"   ├─ 请求 URL: {url}\n"
                    f"   ├─ 请求模型: {model_name}\n"
                    f"   ├─ 请求 Body: {json.dumps(payload, ensure_ascii=False)}\n"
                    f"   └─ 完整响应 Body: {_format_response_body(res_text)}"
                )

    except httpx.TimeoutException as e:
        elapsed = time.time() - start_time
        logger.warning(
            f"⚠️ [LLM 连通性自检超时] 请求超时 | 耗时: {elapsed:.2f}s (超过 10s 超时阈值)\n"
            f"   ├─ 目标地址: {url}\n"
            f"   ├─ 可能原因: 网络不通、服务未启动、或模型加载过慢\n"
            f"   └─ 异常信息: {str(e)}"
        )
    except httpx.ConnectError as e:
        elapsed = time.time() - start_time
        logger.warning(
            f"⚠️ [LLM 连通性自检连接失败] 无法建立连接 | 耗时: {elapsed:.2f}s\n"
            f"   ├─ 目标地址: {url}\n"
            f"   ├─ 可能原因: 服务未启动、IP/端口错误、防火墙阻断\n"
            f"   └─ 异常信息: {str(e)}"
        )
    except Exception as e:
        elapsed = time.time() - start_time
        logger.warning(
            f"⚠️ [LLM 连通性自检阻断] 发生未知异常 | 耗时: {elapsed:.2f}s\n"
            f"   ├─ 异常类型: {type(e).__name__}\n"
            f"   ├─ 异常信息: {str(e)}\n"
            f"   └─ 堆栈跟踪:\n{traceback.format_exc()}"
        )


async def check_vlm_connectivity():
    """
    多模态视觉大模型 (VLLM) 连通性与鉴权自检
    """
    start_time = time.time()
    try:
        url = getattr(settings, "VL_LLM_URL", "http://25.222.64.60:80/lmp-cloud-ias-server/api/vlm/chat/completions/V2")
        api_key = getattr(settings, "VL_LLM_KEY", "fd5dac19a44d43468dd31c96a65610e3")
        model_name = getattr(settings, "VL_MODEL_NAME", "SGGM-VL-27B-R")

        check_image_base64 = load_vllm_check_image_base64()

        headers = {
            "Content-Type": "application/json;charset=utf-8",
            "Authorization": api_key
        }

        payload = {
            "model": model_name,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "图片是什么？"},
                        {"type": "image_base64", "image": check_image_base64}
                    ]
                }
            ],
            "stream": False,
            "temperature": 0.9,
            "top_p": 0.8,
            "presence_penalty": 1,
            "modelVersion": ""
        }

        logger.info(f"🔍 [VLLM 连通性自检拉起] 目标地址: {url} | 校验模型: {model_name}")

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            elapsed = time.time() - start_time
            res_text = response.text

            if response.status_code == 200:
                # ✅ 成功：打印模型返回的回复内容
                reply = _extract_model_reply(res_text)
                usage_info = ""
                try:
                    parsed = json.loads(res_text)
                    if "usage" in parsed and parsed["usage"]:
                        usage = parsed["usage"]
                        if isinstance(usage, dict):
                            usage_info = f" | Token消耗: prompt={usage.get('prompt_tokens', '?')}, completion={usage.get('completion_tokens', '?')}, total={usage.get('total_tokens', '?')}"
                        else:
                            usage_info = f" | Token消耗: {usage}"
                except Exception:
                    pass

                logger.info(
                    f"✅ [VLLM 连通性自检成功] 状态码: 200 | 耗时: {elapsed:.2f}s | 模型: {model_name}{usage_info}\n"
                    f"   ├─ 模型回复: {reply}\n"
                    f"   └─ 完整响应: {_format_response_body(res_text)}"
                )
            else:
                # ❌ 失败：打印详细错误原因
                error_reason = _extract_error_reason(res_text, response.status_code)
                logger.warning(
                    f"⚠️ [VLLM 连通性自检异常] 耗时: {elapsed:.2f}s\n"
                    f"   ├─ 失败原因: {error_reason}\n"
                    f"   ├─ 请求 URL: {url}\n"
                    f"   ├─ 请求模型: {model_name}\n"
                    f"   ├─ 请求 Body 摘要: model={model_name}, image_size={len(check_image_base64)} chars\n"
                    f"   └─ 完整响应 Body: {_format_response_body(res_text)}"
                )

    except httpx.TimeoutException as e:
        elapsed = time.time() - start_time
        logger.warning(
            f"⚠️ [VLLM 连通性自检超时] 请求超时 | 耗时: {elapsed:.2f}s (超过 10s 超时阈值)\n"
            f"   ├─ 目标地址: {url}\n"
            f"   ├─ 可能原因: 网络不通、服务未启动、或模型加载过慢\n"
            f"   └─ 异常信息: {str(e)}"
        )
    except httpx.ConnectError as e:
        elapsed = time.time() - start_time
        logger.warning(
            f"⚠️ [VLLM 连通性自检连接失败] 无法建立连接 | 耗时: {elapsed:.2f}s\n"
            f"   ├─ 目标地址: {url}\n"
            f"   ├─ 可能原因: 服务未启动、IP/端口错误、防火墙阻断\n"
            f"   └─ 异常信息: {str(e)}"
        )
    except Exception as e:
        elapsed = time.time() - start_time
        logger.warning(
            f"⚠️ [VLLM 连通性自检阻断] 发生未知异常 | 耗时: {elapsed:.2f}s\n"
            f"   ├─ 异常类型: {type(e).__name__}\n"
            f"   ├─ 异常信息: {str(e)}\n"
            f"   └─ 堆栈跟踪:\n{traceback.format_exc()}"
        )


async def run_all_llm_health_checks():
    """
    异步并发执行全部自检，绝对不阻塞 FastAPI 服务的启动
    """
    logger.info("🚀 [大模型服务探针] 正在后台发起大模型连通性与鉴权探针巡检...")
    results = await asyncio.gather(
        check_text_llm_connectivity(),
        check_vlm_connectivity(),
        return_exceptions=True
    )
    for res in results:
        if isinstance(res, Exception):
            logger.warning(
                f"⚠️ [大模型服务探针] 探针任务内部抛出未捕获异常\n"
                f"   ├─ 异常类型: {type(res).__name__}\n"
                f"   ├─ 异常信息: {str(res)}\n"
                f"   └─ 堆栈跟踪:\n{traceback.format_exception(res)}"
            )
    logger.info("🏁 [大模型服务探针] 探针巡检全流程执行完毕，已将完整日志物理落盘/控制台输出。")