"""
系统路由：健康检查、平台管理
"""
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException

from app.core.dependencies import get_platform_admin, get_current_user
from app.core.database import database

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/system", tags=["系统"])


@router.get("/health")
async def health_check():
    """健康检查（无需认证）"""
    try:
        await database.fetchval("SELECT 1")
        db_status = "ok"
    except Exception as e:
        db_status = "error: " + str(e)

    return {
        "status": "healthy" if db_status == "ok" else "degraded",
        "timestamp": datetime.now().isoformat(),
        "database": db_status,
        "version": "2.0.0-saas",
    }


@router.get("/stats")
async def system_stats(user=Depends(get_platform_admin)):
    """平台全局统计（仅平台管理员）"""
    tenant_count = await database.fetchval("SELECT COUNT(*) FROM tenants WHERE status = 'active'")
    user_count = await database.fetchval("SELECT COUNT(*) FROM users")
    active_subscriptions = await database.fetchval(
        "SELECT COUNT(*) FROM subscriptions WHERE status = 'active'"
    )
    today_messages = await database.fetchval(
        "SELECT COALESCE(SUM(messages_count), 0) FROM usage_records WHERE date = CURRENT_DATE"
    )

    plan_dist = await database.fetch(
        "SELECT plan, COUNT(*) as count FROM tenants WHERE status = 'active' GROUP BY plan ORDER BY plan"
    )

    return {
        "total_tenants": tenant_count,
        "total_users": user_count,
        "active_subscriptions": active_subscriptions,
        "today_messages": today_messages,
        "plan_distribution": {r["plan"]: r["count"] for r in plan_dist},
    }


@router.get("/tenants")
async def list_tenants(user=Depends(get_platform_admin)):
    """列出所有租户（仅平台管理员）"""
    tenants = await database.fetch(
        "SELECT * FROM tenants WHERE id > 0 ORDER BY created_at DESC"
    )
    result = []
    for t in tenants:
        user_count = await database.fetchval(
            "SELECT COUNT(*) FROM users WHERE tenant_id = $1", t["id"]
        )
        result.append({
            **dict(t),
            "user_count": user_count,
            "created_at": t["created_at"].isoformat() if t["created_at"] else None,
        })
    return result


@router.put("/tenants/{tenant_id}/plan")
async def update_tenant_plan(tenant_id: int, plan: str, user=Depends(get_platform_admin)):
    """手动修改租户套餐（仅平台管理员）"""
    from app.core.config import settings
    valid_plans = list(settings.PLAN_LIMITS.keys())
    if plan not in valid_plans:
        raise HTTPException(status_code=400, detail="无效套餐，可选: " + ", ".join(valid_plans))

    await database.update_tenant_plan(tenant_id, plan)
    return {"message": "租户 " + str(tenant_id) + " 套餐已更新为 " + plan}


@router.put("/tenants/{tenant_id}/status")
async def update_tenant_status(tenant_id: int, status: str, user=Depends(get_platform_admin)):
    """启用/停用租户（仅平台管理员）"""
    if status not in ("active", "suspended"):
        raise HTTPException(status_code=400, detail="状态只能是 active 或 suspended")

    await database.execute(
        "UPDATE tenants SET status = $1 WHERE id = $2",
        status, tenant_id
    )
    return {"message": "租户 " + str(tenant_id) + " 状态已更新为 " + status}


from app.core.tenant_context import TenantContext
from pydantic import BaseModel
from typing import Optional


@router.get("/info")
async def get_current_tenant_info(user=Depends(get_current_user)):
    """获取当前登录用户所属租户信息（前端用）"""
    tenant_id = user["tenant_id"]
    tenant = await database.get_tenant(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="租户不存在")

    # 获取套餐限额
    from app.core.config import settings
    plan_limits = settings.PLAN_LIMITS.get(tenant["plan"], settings.PLAN_LIMITS["free"])

    return {
        "id": tenant["id"],
        "name": tenant["name"],
        "plan": tenant["plan"],
        "status": tenant["status"],
        "tg_account_limit": plan_limits.get("tg_account_limit", 1),
        "mapping_limit": plan_limits.get("mapping_limit", 3),
        "bot_limit": plan_limits.get("bot_limit", 3),
        "member_limit": plan_limits.get("member_limit", 5),
    }


class SettingsRequest(BaseModel):
    translation_enabled: Optional[bool] = None
    translation_api_key: Optional[str] = None
    translation_model: Optional[str] = None


@router.put("/settings")
async def save_settings(req: SettingsRequest, user=Depends(get_current_user)):
    """保存租户设置"""
    tenant_id = user["tenant_id"]
    updates = {}
    if req.translation_api_key is not None:
        updates["api_key"] = req.translation_api_key
    if req.translation_model is not None:
        updates["model"] = req.translation_model

    if updates:
        # 检查是否已有翻译配置
        existing = await database.fetchrow(
            "SELECT id FROM translation_configs WHERE tenant_id = $1", tenant_id
        )
        if existing:
            set_clause = ", ".join(f"{k} = ${i+2}" for i, k in enumerate(updates.keys()))
            vals = list(updates.values())
            await database.pool.execute(
                f"UPDATE translation_configs SET {set_clause} WHERE tenant_id = $1",
                tenant_id, *vals
            )
        else:
            await database.pool.execute(
                "INSERT INTO translation_configs (tenant_id, api_key, model) VALUES ($1, $2, $3)",
                tenant_id,
                updates.get("api_key", ""),
                updates.get("model", "deepseek-chat")
            )

    if req.translation_enabled is not None:
        await database.pool.execute(
            "UPDATE translation_configs SET enabled = $2 WHERE tenant_id = $1",
            tenant_id, req.translation_enabled
        )

    return {"message": "设置已保存"}
