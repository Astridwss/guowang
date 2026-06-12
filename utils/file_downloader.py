# import shutil
# import httpx

# async def download_file(url: str, local_path: str):
#     """通用异步文件下载/拷贝助手"""
#     if url.startswith("http://") or url.startswith("https://"):
#         async with httpx.AsyncClient(follow_redirects=True) as client:
#             response = await client.get(url, timeout=60.0)
#             response.raise_for_status()
#             with open(local_path, "wb") as f:
#                 f.write(response.content)
#     else:
#         shutil.copy(url, local_path)
# 文件路径：utils/file_downloader.py
import os
import shutil
import httpx
import asyncio
import urllib.parse

async def download_file(url: str, target_dir: str, timeout: float = 60.0) -> str:
    """
    云原生沙盒标准：动态归置文件下载器
    入参：
        url: 下载链接或本地物理路径
        target_dir: 严格限定的任务沙盒目录 (例如: data/workspace/task_001/)
    返回值：
        str: 最终在本地落地文件的绝对物理路径
    """
    # 1. 确保任务沙盒目录物理存在
    if not os.path.exists(target_dir):
        os.makedirs(target_dir, exist_ok=True)

    final_filename = ""
    local_path = ""

    # 2. 处理网络文件下载
    if url.startswith("http://") or url.startswith("https://"):
        async with httpx.AsyncClient(follow_redirects=True) as client:
            async with client.stream("GET", url, timeout=timeout) as response:
                response.raise_for_status()
                
                # 💡 核心：优先从 HTTP 响应头里抓取真实的原始文件名（针对云存储预签名 URL 极其有效）
                content_disp = response.headers.get("Content-Disposition")
                if content_disp and "filename=" in content_disp:
                    for part in content_disp.split(";"):
                        if "filename=" in part:
                            final_filename = part.split("=")[1].strip('"\'')
                            # 处理可能存在的 URL 编码（如中文名）
                            final_filename = urllib.parse.unquote(final_filename)
                            break
                
                # 如果响应头没有，则从 URL 字符串切片中提取
                if not final_filename:
                    pure_url_path = url.split("?")[0] # 剔除 Token 参数
                    final_filename = os.path.basename(pure_url_path)
                
                # 终极兜底名
                if not final_filename:
                    final_filename = "downloaded_source_file.tmp"

                local_path = os.path.join(target_dir, final_filename)
                
                # 流式分块写入，稳如磐石
                with open(local_path, "wb") as f:
                    async for chunk in response.iter_bytes(chunk_size=8192):
                        f.write(chunk)
                        
    # 3. 处理本地文件拷贝跨越
    else:
        if not os.path.exists(url):
            raise FileNotFoundError(f"[下载器] 传入的本地源路径不存在: {url}")
            
        final_filename = os.path.basename(url)
        local_path = os.path.join(target_dir, final_filename)
        
        # 线程池异步拷贝，不卡死主循环
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, shutil.copy, url, local_path)

    # 返回最终文件的绝对路径，供下游业务精准读取
    return os.path.abspath(local_path)