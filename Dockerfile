# ============================================================
# 第一階段：建構環境
# ============================================================
FROM python:3.11-slim-bookworm AS builder

WORKDIR /build

# 安裝系統依賴（PostgreSQL 客戶端庫編譯需要）
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 複製依賴清單
COPY requirements.txt .

# 安裝 Python 依賴到指定目錄
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ============================================================
# 第二階段：生產映像
# ============================================================
FROM python:3.11-slim-bookworm

WORKDIR /app

# 只安裝運行時需要的系統庫
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libpq5 \
    && rm -rf /var/lib/apt/lists/*

# 從建構階段複製已編譯的 Python 套件
COPY --from=builder /install /usr/local

# 複製應用程式碼
COPY app/ ./app/
COPY main.py .

# 建立非特權使用者
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

# 切換到非 root 使用者
USER appuser

# 暴露端口
EXPOSE 5001

# 健康檢查
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5001/health').read()" || exit 1

# 啟動指令（生產環境用 Gunicorn）
CMD ["gunicorn", \
     "--bind", "0.0.0.0:5001", \
     "--workers", "4", \
     "--worker-class", "sync", \
     "--timeout", "120", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "main:app"]
