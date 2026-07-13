# 收费5000搭建转发系统

Telegram → DingTalk 多租户消息转发平台 (T2D SaaS)

## 功能
- 多租户隔离架构
- Telegram 消息采集 → DingTalk 回调转发
- 消息过滤规则引擎（黑名单/白名单/关键词）
- 租户管理（团队/成员/权限控制）
- 用量统计与配额管理
- 平台管理员套餐变更
- Vue 3 + Element Plus 前端
- FastAPI + PostgreSQL 后端
- Docker 容器化部署

## 技术栈
- **后端**: Python 3.11 + FastAPI + asyncpg
- **前端**: Vue 3 + Element Plus (CDN SPA)
- **数据库**: PostgreSQL 16
- **部署**: Docker + Docker Compose + Nginx

## 部署
```bash
docker-compose up -d
```

## 默认账户
- 平台管理员: admin / admin123
- 测试用户: testuser / test123456
