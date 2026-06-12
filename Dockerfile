# 1. 使用华为云的开源镜像加速拉取基础环境
FROM swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/python:3.12-slim
#FROM swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/python:3.12-slim-linuxarm64

# 2. 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_NO_CACHE=1 

# 3. 更换 apt 源为清华大学源，并增加 --fix-missing
RUN sed -i 's/deb.debian.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list.d/debian.sources && \
    apt-get update && \
    apt-get install -y --no-install-recommends --fix-missing build-essential && \
    rm -rf /var/lib/apt/lists/*

# 4. 【关键修改】使用阿里云源，并强制设置 1000 秒超时时间防断线
RUN pip install --default-timeout=1000 -i https://mirrors.aliyun.com/pypi/simple/ uv

# 5. 设置工作目录
WORKDIR /app

# 6. 先拷贝 TOML 依赖文件
COPY requirements.txt .

# 7. 【关键修改】使用 uv 极速安装，同样指向阿里云源
RUN uv pip install --system -r requirements.txt --index-url https://mirrors.aliyun.com/pypi/simple/
# 8. 拷贝所有业务代码到容器内（此时因为有 .dockerignore，拷贝速度会是毫秒级）
COPY . .

# 9. 暴露端口
EXPOSE 8080

# 10. 切换当前工作目录到 api 文件夹 (相当于 cd api/)
WORKDIR /app/api

# 11. 使用 exec 模式启动 uvicorn
# 必须加上 --host 0.0.0.0，否则 Docker 外部无法访问！
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]