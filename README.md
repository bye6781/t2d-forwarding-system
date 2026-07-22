# T2D Cloud

多租户 Telegram 到钉钉消息转发平台。

## 架构

- Vue 3、Vite、TypeScript、Pinia、Element Plus
- FastAPI 领域模块单体
- PostgreSQL 业务数据与 Alembic 迁移
- Redis 租户运行状态、消息去重和分布式状态
- Docker 多阶段构建，Nginx 负责 HTTPS 反向代理

## 本地检查

```bash
cd frontend
npm ci
npm test
npm run build

cd ..
python -m pytest -q
python -m compileall -q backend
```

## 部署

生产密码、数据库地址和 JWT 密钥必须通过 `.env` 注入：

```bash
docker compose build
docker compose up -d
```

健康检查：`GET /api/v2/system/health`。

Telegram session 保存在私有卷 `data/private`，公开媒体保存在 `data/public-media`。
