# AI数智化资产管理系统 - 后端Dockerfile
# 支持信创环境：多架构构建(linux/amd64, linux/arm64)
FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖（信创环境可能需要额外配置源）
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc default-libmysqlclient-dev pkg-config \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

COPY . .

RUN mkdir -p reports

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
