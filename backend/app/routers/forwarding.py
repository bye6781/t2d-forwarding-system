"""
转发引擎控制路由
"""
import logging
from fastapi import APIRouter, Depends, HTTPException

from app.core.database import database
from app.core.dependencies import get_current_user
from app.core.tenant_context import TenantContext
from app.services.forwarding_service import forwarding_service
from app.services.telegram_service import telegram_service
from app.services.quota_service import quota_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/forwarding", tags=["Forwarding"])


@router.get("/status")
async def get_status(user: dict = Depends(get_current_user)):
    """获取转发引擎状态"""
    tenant_id = TenantContext.get()

    accounts = await database.get_tg_accounts(tenant_id)
    account_status = []
    for acc in accounts:
        account_status.append({
            "id": acc["id"],
            "name": acc.get("name", ""),
            "phone": acc.get("phone", ""),
            "connected": telegram_service.is_connected(tenant_id, acc["id"]),
            "status": acc.get("status", "disconnected"),
        })

    usage = await quota_service.get_usage_summary(tenant_id)
    stats = forwarding_service.get_stats()
    records = await database.get_forward_records(tenant_id, limit=10)

    return {
        "success": True,
        "data": {
            "engine_running": forwarding_service._running,
            "accounts": account_status,
            "usage": usage,
            "stats": stats,
            "recent_records": records,
        }
    }


@router.post("/start")
async def start_engine(user: dict = Depends(get_current_user)):
    """启动转发引擎"""
    tenant_id = TenantContext.get()

    accounts = await database.get_tg_accounts(tenant_id)
    connected = [a for a in accounts if a.get("is_authorized")]
    if not connected:
        raise HTTPException(status_code=400, detail="没有已授权的 Telegram 账号，请先连接账号")

    mappings = await database.get_mappings(tenant_id)
    enabled_mappings = [m for m in mappings if m.get("enabled", True)]
    if not enabled_mappings:
        raise HTTPException(status_code=400, detail="没有启用的映射规则，请先配置映射")

    await forwarding_service.start()
    return {"success": True, "message": "转发引擎已启动"}


@router.post("/stop")
async def stop_engine(user: dict = Depends(get_current_user)):
    """停止转发引擎"""
    await forwarding_service.stop()
    return {"success": True, "message": "转发引擎已停止"}


@router.get("/records")
async def get_records(limit: int = 50, status: str = None, user: dict = Depends(get_current_user)):
    """获取转发记录"""
    tenant_id = TenantContext.get()
    records = await database.get_forward_records(tenant_id, limit=limit, status=status)
    return {"success": True, "data": records}


@router.get("/dashboard")
async def get_dashboard(user: dict = Depends(get_current_user)):
    """获取仪表盘统计数据"""
    tenant_id = TenantContext.get()
    stats = await database.get_dashboard_stats(tenant_id)
    return {"success": True, "data": stats}
