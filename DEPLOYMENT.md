# 部署指南

## 本地開發環境

### 1. 使用 Docker Compose（推薦）

```bash
# 複製環境變數範本
cp .env.example .env

# 編輯 .env 填入你的配置
# 至少要改: POSTGRES_PASSWORD, SECRET_KEY

# 啟動所有服務（資料庫 + 應用）
docker-compose up -d

# 查看日誌
docker-compose logs -f app

# 停止服務
docker-compose down

# 完全清除（包含資料庫資料）
docker-compose down -v
```

訪問: http://localhost:8080

---

## 生產環境部署

### 方法一：使用 Docker

```bash
# 1. 建構映像
docker build -t my-accounting-app:latest .

# 2. 運行容器（需要外部 PostgreSQL）
docker run -d \
  --name accounting-app \
  -p 8080:8080 \
  -e DATABASE_URL="postgresql://user:pass@host:5432/db" \
  -e SECRET_KEY="your-secret-key-min-32-chars" \
  -e FLASK_ENV="production" \
  --restart unless-stopped \
  my-accounting-app:latest
```

### 方法二：推送到容器註冊表

```bash
# Docker Hub
docker tag my-accounting-app:latest username/my-accounting-app:latest
docker push username/my-accounting-app:latest

# Google Container Registry
docker tag my-accounting-app:latest gcr.io/project-id/my-accounting-app:latest
docker push gcr.io/project-id/my-accounting-app:latest

# AWS ECR
aws ecr get-login-password --region region | docker login --username AWS --password-stdin account.dkr.ecr.region.amazonaws.com
docker tag my-accounting-app:latest account.dkr.ecr.region.amazonaws.com/my-accounting-app:latest
docker push account.dkr.ecr.region.amazonaws.com/my-accounting-app:latest
```

---

## 平台特定部署

### Render.com

1. 連接 GitHub 儲存庫
2. 選擇 "Web Service"
3. 環境設定:
   - Build Command: 留空（使用 Dockerfile）
   - Start Command: 留空（使用 Dockerfile CMD）
4. 環境變數:
   ```
   DATABASE_URL=<從 Render PostgreSQL 複製>
   SECRET_KEY=<至少 32 字元隨機字串>
   FLASK_ENV=production
   ```

### Railway.app

1. 連接 GitHub 儲存庫
2. 新增 PostgreSQL 資料庫
3. 環境變數會自動設定 DATABASE_URL
4. 手動新增:
   ```
   SECRET_KEY=<至少 32 字元隨機字串>
   FLASK_ENV=production
   ```

### Fly.io

```bash
# 安裝 flyctl
curl -L https://fly.io/install.sh | sh

# 登入
flyctl auth login

# 初始化（會生成 fly.toml）
flyctl launch

# 設定密鑰
flyctl secrets set SECRET_KEY="your-secret-key"
flyctl secrets set DATABASE_URL="postgresql://..."

# 部署
flyctl deploy
```

### Google Cloud Run

```bash
# 建構並推送映像
gcloud builds submit --tag gcr.io/PROJECT_ID/my-accounting-app

# 部署
gcloud run deploy my-accounting-app \
  --image gcr.io/PROJECT_ID/my-accounting-app \
  --platform managed \
  --region asia-east1 \
  --allow-unauthenticated \
  --set-env-vars="DATABASE_URL=postgresql://...,SECRET_KEY=...,FLASK_ENV=production"
```

---

## 環境變數說明

### 必需

| 變數 | 說明 | 範例 |
|------|------|------|
| `DATABASE_URL` | PostgreSQL 連線字串 | `postgresql://user:pass@host:5432/db` |
| `SECRET_KEY` | Flask 密鑰（至少 32 字元） | `openssl rand -hex 32` 產生 |

### 可選

| 變數 | 說明 | 預設值 |
|------|------|--------|
| `FLASK_ENV` | 環境模式 | `production` |
| `WORKERS` | Gunicorn worker 數量 | `4` |
| `APP_PORT` | 應用監聽端口 | `8080` |

---

## 健康檢查

所有容器編排平台都需要健康檢查端點:

```bash
curl http://localhost:8080/health
# 回應: {"status":"healthy"}
```

---

## 注意事項

### 安全性

1. **絕對不要** 把 `.env` 提交到 Git
2. 生產環境 `SECRET_KEY` 至少 32 字元隨機字串:
   ```bash
   openssl rand -hex 32
   ```
3. 資料庫密碼要夠強

### 效能

- Gunicorn workers 數量 = `(2 × CPU 核心數) + 1`
- 記憶體需求: 約 512MB-1GB per worker

### 資料庫

- 確保 PostgreSQL 版本 ≥ 12
- 生產環境建議使用託管資料庫服務（Render PostgreSQL, AWS RDS, Google Cloud SQL）
