# 珠科百事通 Dockerfile
# 用法：
#   docker build -t zhike-baishitong .
#   docker run -p 8000:8000 --env-file .env -v $(pwd)/data:/app/data zhike-baishitong
# 评委一键启动：
#   docker run -p 8000:8000 --env-file .env -v ./data:/app/data zhike-baishitong

FROM python:3.12-slim

WORKDIR /app

# 系统依赖（lxml 需要 libxml2/libxslt）
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libxml2-dev libxslt1-dev \
    && rm -rf /var/lib/apt/lists/*

# 先装依赖（利用 Docker 层缓存）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制代码
COPY api/ api/
COPY crawler/ crawler/
COPY retrieval/ retrieval/
COPY evaluation/ evaluation/
COPY web/ web/
COPY start.py .

# data/ 不入镜像，运行时挂载
VOLUME /app/data

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
