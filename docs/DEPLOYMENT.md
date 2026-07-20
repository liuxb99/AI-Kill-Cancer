# 部署文档

> 最后更新：2026-07-20

## 当前部署

- **前端**：Vercel (https://ai-kill-cancer-zqpi.vercel.app)
- **API**：Vercel Serverless (`api/index.py`)
- **数据库**：未连接真实 PostgreSQL 实例

## 架构

```
Vercel Edge/Serverless
  ├── / (前端 SPA — React)
  ├── /api/* (FastAPI via ASGI)
  └── /assets/* (静态资源)
```

## Vercel 注意事项

### 冷启动
- Serverless 函数的冷启动时间约 1-5 秒
- PyTorch 模型加载会增加冷启动时间（~2-5 秒）
- 模型文件应保持 < 50MB 以避免超时

### 数据库
- Vercel Serverless 无法维护长连接
- 需要使用外部 PostgreSQL 实例（如 Supabase）
- 连接池配置需适配 serverless 环境

### 文件系统
- Vercel Serverless 使用临时文件系统（/tmp）
- 模型 checkpoint 应存储在外部存储（S3/GCS/Supabase Storage）
- 不支持本地文件持久化

### 静态前端
- `src/frontend/dist/` 构建后由 FastAPI 静态文件服务
- Vercel 配置见 `vercel.json`
- SPA fallback 通过 catch-all 路由实现

## 环境变量

| 变量 | 必填 | 说明 |
|------|------|------|
| `APP_MODE` | 否 | demo / research / production（默认 demo） |
| `DEBUG` | 否 | 调试模式 |
| `CORS_ORIGINS` | 否 | 逗号分隔，production 必须明确指定 |
| `DATABASE_URL` | 否 | PostgreSQL 连接字符串 |
| `MODEL_PATH` | 否 | 模型 checkpoint 路径 |
| `MODEL_ENABLED` | 否 | 是否启用模型加载 |
| `LOG_LEVEL` | 否 | 日志级别 |

## Health 端点

| 端点 | 用途 |
|------|------|
| `GET /api/v1/health` | 简单健康检查 |
| `GET /api/v1/health/live` | Liveness probe（K8s） |
| `GET /api/v1/health/ready` | Readiness probe（含依赖状态） |
| `GET /api/v1/health/dependencies` | 依赖详情 |

## 本地开发

```bash
# 安装依赖
pip install -r requirements.txt
pip install -r requirements-ai.txt

# 运行 API
cd src/backend
uvicorn main:app --reload

# 运行前端
cd src/frontend
npm install
npm run dev
```
