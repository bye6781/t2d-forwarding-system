"""T2D V2 domain-modular application entrypoint."""
import asyncio
import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.database import database
from app.core.middleware import AuditLogMiddleware, TenantContextMiddleware
from app.core.security import hash_password
from app.modules.auth import router as auth
from app.modules.auth.repository import auth_repository
from app.modules.audit import router as audit
from app.modules.connectors import router as connectors
from app.modules.connectors.repository import connector_repository
from app.modules.forwarding import router as forwarding
from app.modules.forwarding.runtime import redis_client, tenant_runtime
from app.modules.platform import router as platform
from app.modules.policies import router as policies
from app.modules.tenants import router as tenants


def configure_logging() -> None:
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]
    try:
        Path(settings.LOGS_DIR).mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(Path(settings.LOGS_DIR) / "t2d-saas.log", encoding="utf-8"))
    except OSError:
        pass
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=handlers,
    )


configure_logging()
logger = logging.getLogger("t2d-saas")


async def bootstrap_accounts() -> None:
    if not await auth_repository.platform_tenant_exists():
        await database.execute(
            "INSERT INTO tenants(id,name,slug,plan,status) VALUES(0,'Platform','platform','free','active')"
        )
    admin = await database.fetchrow(
        "SELECT id FROM users WHERE tenant_id=0 AND username=$1", settings.PLATFORM_ADMIN_USERNAME
    )
    if not admin:
        if not settings.PLATFORM_ADMIN_PASSWORD:
            raise RuntimeError("PLATFORM_ADMIN_PASSWORD must be set for initial deployment")
        async with database.transaction() as connection:
            user_id = await connection.fetchval(
                """INSERT INTO users(tenant_id,username,password_hash,role)
                   VALUES(0,$1,$2,'owner') RETURNING id""",
                settings.PLATFORM_ADMIN_USERNAME, hash_password(settings.PLATFORM_ADMIN_PASSWORD),
            )
            await connection.execute("INSERT INTO platform_admins(user_id) VALUES($1)", user_id)

    if settings.TEST_TENANT_USERNAME and settings.TEST_TENANT_PASSWORD:
        exists = await database.fetchval(
            "SELECT id FROM users WHERE username=$1", settings.TEST_TENANT_USERNAME
        )
        if not exists:
            limits = settings.PLAN_LIMITS["free"]
            async with database.transaction() as connection:
                tenant_id = await connection.fetchval(
                    "INSERT INTO tenants(name,slug,plan,status) VALUES($1,$2,'free','active') RETURNING id",
                    settings.TEST_TENANT_NAME or "T2D Test Tenant", "t2d-test",
                )
                await connection.execute(
                    """INSERT INTO users(tenant_id,username,password_hash,role)
                       VALUES($1,$2,$3,'owner')""",
                    tenant_id, settings.TEST_TENANT_USERNAME, hash_password(settings.TEST_TENANT_PASSWORD),
                )
                await connection.execute(
                    """INSERT INTO subscriptions
                       (tenant_id,plan,status,message_quota,tg_account_limit,mapping_limit,
                        current_period_start,current_period_end)
                       VALUES($1,'free','active',$2,$3,$4,NOW(),NOW()+INTERVAL '30 days')""",
                    tenant_id, limits["message_quota"], limits["tg_account_limit"], limits["mapping_limit"],
                )


async def connect_authorized_accounts() -> None:
    from app.services.telegram_service import telegram_service

    accounts = await connector_repository.authorized_accounts_for_startup()
    for account in accounts:
        try:
            connected = await telegram_service.connect_account(
                tenant_id=account["tenant_id"], account_db_id=account["id"],
                api_id=account["api_id"], api_hash=account["api_hash"], phone=account["phone"],
                request_code=False,
            )
            if connected is True:
                await tenant_runtime.start(account["tenant_id"])
            elif connected == "unauthorized":
                logger.warning(
                    "Telegram account %s requires manual authorization; no code was requested",
                    account["id"],
                )
        except Exception:
            logger.exception("Failed to auto-connect Telegram account %s", account["id"])


async def monitor_telegram_connections() -> None:
    while True:
        await asyncio.sleep(30)
        try:
            await connect_authorized_accounts()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Telegram connection health check failed")


@asynccontextmanager
async def lifespan(app: FastAPI):
    Path(settings.PRIVATE_DATA_DIR, "sessions").mkdir(parents=True, exist_ok=True)
    Path(settings.PUBLIC_MEDIA_DIR).mkdir(parents=True, exist_ok=True)
    await database.init()
    await bootstrap_accounts()
    from app.services.forwarding_service import forwarding_service
    await forwarding_service.start()
    await connect_authorized_accounts()
    telegram_monitor = asyncio.create_task(
        monitor_telegram_connections(), name="telegram-connection-monitor"
    )
    logger.info("T2D V2 started")
    try:
        yield
    finally:
        telegram_monitor.cancel()
        try:
            await telegram_monitor
        except asyncio.CancelledError:
            pass
    await forwarding_service.stop()
    from app.services.telegram_service import telegram_service
    from app.services.dingtalk_service import dingtalk_service
    await telegram_service.disconnect_all()
    await dingtalk_service.close()
    await redis_client.aclose()
    await database.close()


app = FastAPI(title="T2D Cloud API", version="2.0.0", lifespan=lifespan)
app.add_middleware(TenantContextMiddleware)
app.add_middleware(AuditLogMiddleware)


@app.exception_handler(HTTPException)
async def http_error(request: Request, exc: HTTPException):
    if isinstance(exc.detail, dict):
        detail = exc.detail
    else:
        detail = {"code": f"http_{exc.status_code}", "message": str(exc.detail)}
    return JSONResponse({"detail": detail}, status_code=exc.status_code, headers=exc.headers)


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    return JSONResponse(
        {"detail": {"code": "validation_error", "message": "请求参数无效", "fields": exc.errors()}},
        status_code=422,
    )


@app.get("/api/v2/system/health")
async def health():
    database_status = "ok"
    redis_status = "ok"
    try:
        await database.fetchval("SELECT 1")
    except Exception:
        database_status = "error"
    try:
        await redis_client.ping()
    except Exception:
        redis_status = "error"
    status = "healthy" if database_status == redis_status == "ok" else "degraded"
    payload = {"data": {"status": status, "database": database_status, "redis": redis_status, "version": "2.0.0"}}
    return JSONResponse(payload, status_code=200 if status == "healthy" else 503)


app.include_router(auth.router, prefix="/api/v2/auth")
app.include_router(tenants.router, prefix="/api/v2/tenant")
app.include_router(platform.router, prefix="/api/v2/platform")
app.include_router(connectors.router, prefix="/api/v2/connectors")
app.include_router(forwarding.router, prefix="/api/v2/forwarding")
app.include_router(policies.router, prefix="/api/v2/policies")
app.include_router(audit.router, prefix="/api/v2/audit")

Path(settings.PUBLIC_MEDIA_DIR).mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=settings.PUBLIC_MEDIA_DIR), name="media")
web_dir = Path("/app/web")
if not web_dir.exists():
    web_dir = Path(__file__).resolve().parents[1] / "frontend" / "dist"


@app.get("/{path:path}")
async def spa(path: str):
    if path == "api" or path.startswith("api/"):
        return JSONResponse(
            {"detail": {"code": "not_found", "message": "API endpoint not found"}},
            status_code=404,
        )
    candidate = web_dir / path
    if path and candidate.is_file():
        return FileResponse(candidate)
    index = web_dir / "index.html"
    if index.exists():
        return FileResponse(index)
    return JSONResponse({"detail": {"code": "frontend_unavailable", "message": "前端尚未构建"}}, status_code=503)


if __name__ == "__main__":
    uvicorn.run("main:app", host=settings.API_HOST, port=settings.API_PORT, log_level="info")
