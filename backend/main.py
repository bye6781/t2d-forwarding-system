"""
T2D SaaS 主入口
多租户 Telegram → 钉钉消息转发平台
"""
import sys
import asyncio
import logging
from logging.handlers import RotatingFileHandler
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn

from app.core.config import settings
from app.core.database import database
from app.core.middleware import TenantContextMiddleware

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        RotatingFileHandler(
            f"{settings.LOGS_DIR}/t2d-saas.log",
            maxBytes=10*1024*1024,
            backupCount=5,
            encoding="utf-8"
        ),
    ],
)
logger = logging.getLogger("t2d-saas")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("T2D SaaS starting up...")

    # 初始化数据库连接池
    await database.init()
    logger.info("Database connection pool initialized")

    # 确保数据目录存在
    data_dir = Path("/app/data")
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "sessions").mkdir(parents=True, exist_ok=True)

    # 确保平台租户存在
    platform_tenant = await database.get_tenant(0)
    if not platform_tenant:
        await database.execute(
            "INSERT INTO tenants (id, name, slug, plan, status) VALUES (0, 'Platform', 'platform', 'free', 'active')"
        )
        logger.info("Platform tenant created")

    # 确保平台管理员存在
    admin_user = await database.fetchrow(
        "SELECT id FROM users WHERE username = 'admin' AND tenant_id = 0"
    )
    if not admin_user:
        from app.core.security import hash_password
        admin_id = await database.create_user(
            tenant_id=0,
            username="admin",
            password_hash=hash_password("admin123"),
            role="owner"
        )
        await database.execute(
            "INSERT INTO platform_admins (user_id) VALUES ($1)", admin_id
        )
        logger.info(f"Platform admin created (id={admin_id})")

    # 启动转发引擎
    from app.services.forwarding_service import forwarding_service
    await forwarding_service.start()
    logger.info("Forwarding engine started")

    # 自动连接所有已授权的 TG 账号
    tenants = await database.fetch("SELECT id FROM tenants WHERE status = 'active' AND id > 0")
    connected_count = 0
    for tenant in tenants:
        tid = tenant["id"]
        accounts = await database.get_tg_accounts(tid)
        for acc in accounts:
            if acc.get("is_authorized"):
                try:
                    from app.services.telegram_service import telegram_service
                    await telegram_service.connect_account(
                        tenant_id=tid,
                        account_db_id=acc["id"],
                        api_id=acc["api_id"],
                        api_hash=acc["api_hash"],
                        phone=acc["phone"],
                    )
                    connected_count += 1
                except Exception as e:
                    logger.warning(f"Auto-connect TG account {acc['id']} for tenant {tid} failed: {e}")

    logger.info(f"Auto-connected {connected_count} TG accounts")
    logger.info("T2D SaaS started successfully")

    yield

    # 关闭
    logger.info("T2D SaaS shutting down...")
    from app.services.forwarding_service import forwarding_service as fs
    await fs.stop()
    from app.services.telegram_service import telegram_service as ts
    await ts.disconnect_all()
    await database.close()
    logger.info("T2D SaaS stopped")


# 创建 FastAPI 应用
app = FastAPI(
    title="T2D SaaS",
    description="多租户 Telegram → 钉钉消息转发平台",
    version="2.0.0",
    lifespan=lifespan,
)

# 中间件
app.add_middleware(TenantContextMiddleware)

# 静态文件 - 租户媒体文件
app.mount("/static", StaticFiles(directory="/app/data"), name="static")

# 注册路由
from app.routers import auth, tenants, system, telegram_accounts, dingtalk_bots, mappings, forwarding

app.include_router(auth.router)
app.include_router(tenants.router)
app.include_router(system.router)
app.include_router(telegram_accounts.router)
app.include_router(dingtalk_bots.router)
app.include_router(mappings.router)
app.include_router(forwarding.router)


# 前端 SPA 路由
@app.get("/")
async def index():
    index_path = Path("/app/static/index.html")
    if index_path.exists():
        return FileResponse(str(index_path))
    return {"message": "T2D SaaS API is running", "version": "2.0.0"}


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.API_PORT,
        reload=False,
        log_level="info",
    )
