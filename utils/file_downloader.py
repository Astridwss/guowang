import shutil
import httpx

async def download_file(url: str, local_path: str):
    """通用异步文件下载/拷贝助手"""
    if url.startswith("http://") or url.startswith("https://"):
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(url, timeout=60.0)
            response.raise_for_status()
            with open(local_path, "wb") as f:
                f.write(response.content)
    else:
        shutil.copy(url, local_path)