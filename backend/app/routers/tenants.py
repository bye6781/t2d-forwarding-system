"""
租户管理路由：团队管理、成员管理、用量查看
"""
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

from app.core.dependencies import get_current_user, require_role
from app.core.database import database
from app.core.security import hash_password
from app.services.quota_service import quota_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/tenant", tags=["租户管理"])


class InviteMemberRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=30)
    password: str = Field(..., min_length=6, max_length=50)
    email: Optional[str] = None
    role: str = Field("member", pattern="^(admin|member|viewer)$")


class UpdateMemberRequest(BaseModel):
    role: Optional[str] = Field(None, pattern="^(admin|member|viewer)$")
    is_active: Optional[bool] = None


# ---- 团队信息 ----

@router.get("/info")
async def get_tenant_info(user=Depends(get_current_user)):
    """获取当前租户信息"""
    tenant = await database.get_tenant(user["tenant_id"])
    usage = await quota_service.get_usage_summary(user["tenant_id"])
    return {
        "id": tenant["id"],
        "name": tenant["name"],
        "slug": tenant["slug"],
        "plan": tenant["plan"],
        "status": tenant["status"],
        "created_at": tenant["created_at"].isoformat() if tenant["created_at"] else None,
        "usage": usage,
    }


# ---- 成员管理 ----

@router.get("/members")
async def list_members(user=Depends(get_current_user)):
    """获取团队成员列表"""
    members = await database.get_users_by_tenant(user["tenant_id"])
    return [
        {
            "id": m["id"],
            "username": m["username"],
            "email": m["email"],
            "role": m["role"],
            "is_active": m["is_active"],
            "created_at": m["created_at"].isoformat() if m["created_at"] else None,
            "last_login": m["last_login"].isoformat() if m["last_login"] else None,
        }
        for m in members
    ]


@router.post("/members")
async def invite_member(req: InviteMemberRequest, user=Depends(get_current_user)):
    """邀请新成员（需要 owner/admin 权限）"""
    if user["role"] not in ("owner", "admin"):
        raise HTTPException(status_code=403, detail="需要管理员权限")

    # 检查成员数限制
    members = await database.get_users_by_tenant(user["tenant_id"])
    from app.core.config import settings
    plan_limits = settings.PLAN_LIMITS.get(
        await database.pool.fetchval("SELECT plan FROM tenants WHERE id = $1", user["tenant_id"]) or "free",
        settings.PLAN_LIMITS["free"]
    )
    if len(members) >= plan_limits["member_limit"]:
        raise HTTPException(status_code=400, detail=f"成员数已达上限（{plan_limits["member_limit"]}人），请升级套餐")

    # 检查用户名唯一
    existing = await database.pool.fetchrow(
        "SELECT id FROM users WHERE username = $1", req.username
    )
    if existing:
        raise HTTPException(status_code=400, detail="用户名已存在")

    user_id = await database.create_user(
        tenant_id=user["tenant_id"],
        username=req.username,
        password_hash=hash_password(req.password),
        email=req.email,
        role=req.role,
    )

    # 审计日志
    await database.add_audit_log(
        user["tenant_id"], user["id"], "invite_member",
        detail=f"邀请了成员 {req.username} (角色: {req.role})"
    )

    return {"id": user_id, "username": req.username, "role": req.role, "message": "成员邀请成功"}


@router.put("/members/{member_id}")
async def update_member(member_id: int, req: UpdateMemberRequest, user=Depends(get_current_user)):
    """更新成员信息"""
    if user["role"] not in ("owner", "admin"):
        raise HTTPException(status_code=403, detail="需要管理员权限")

    if req.role:
        await database.pool.execute(
            "UPDATE users SET role = $1 WHERE id = $2 AND tenant_id = $3",
            req.role, member_id, user["tenant_id"]
        )
    if req.is_active is not None:
        # 不能禁用自己
        if member_id == user["id"]:
            raise HTTPException(status_code=400, detail="不能禁用自己的账户")
        await database.pool.execute(
            "UPDATE users SET is_active = $1 WHERE id = $2 AND tenant_id = $3",
            req.is_active, member_id, user["tenant_id"]
        )

    return {"message": "更新成功"}


@router.delete("/members/{member_id}")
async def remove_member(member_id: int, user=Depends(get_current_user)):
    """移除成员"""
    if user["role"] != "owner":
        raise HTTPException(status_code=403, detail="需要 owner 权限")

    if member_id == user["id"]:
        raise HTTPException(status_code=400, detail="不能删除自己")

    await database.pool.execute(
        "DELETE FROM users WHERE id = $1 AND tenant_id = $2",
        member_id, user["tenant_id"]
    )

    await database.add_audit_log(
        user["tenant_id"], user["id"], "remove_member",
        detail=f"移除了成员 ID={member_id}"
    )

    return {"message": "成员已移除"}


# ---- 用量统计 ----

@router.get("/usage")
async def get_usage(user=Depends(get_current_user)):
    """获取当前用量"""
    return await quota_service.get_usage_summary(user["tenant_id"])


# ---- 注册 ----

class RegisterRequest(BaseModel):
    tenant_name: str = Field(..., min_length=1, max_length=100)
    username: str = Field(..., min_length=3, max_length=30)
    password: str = Field(..., min_length=6, max_length=50)


@router.post("/register")
async def register_tenant(req: RegisterRequest):
    """自助注册新租户"""
    import re
    # 生成 slug
    slug = re.sub(r"[^a-z0-9]+", "-", req.tenant_name.lower()).strip("-")[:50]
    if not slug:
        slug = "team"

    # 检查 slug 唯一
    existing = await database.get_tenant_by_slug(slug)
    if existing:
        slug = slug + "-" + str(int(datetime.now().timestamp()) % 10000)

    # 检查用户名唯一（全局）
    dup = await database.pool.fetchrow("SELECT id FROM users WHERE username = $1", req.username)
    if dup:
        raise HTTPException(status_code=400, detail="用户名已存在")

    # 创建租户
    tenant_id = await database.create_tenant(name=req.tenant_name, slug=slug)

    # 创建 owner 用户
    user_id = await database.create_user(
        tenant_id=tenant_id,
        username=req.username,
        password_hash=hash_password(req.password),
        role="owner",
    )

    # 创建免费订阅（使用免费套餐配额）
    from app.core.config import settings
    free_limits = settings.PLAN_LIMITS.get("free", {})
    await database.create_subscription(
        tenant_id=tenant_id,
        plan="free",
        message_quota=free_limits.get("daily_message_limit", 100),
        tg_account_limit=free_limits.get("tg_account_limit", 1),
        mapping_limit=free_limits.get("mapping_limit", 3),
    )

    return {"tenant_id": tenant_id, "user_id": user_id, "message": "注册成功"}


# ---- 自助升降级 ----

class ChangePlanRequest(BaseModel):
    plan: str = Field(..., pattern="^(free|basic|pro|enterprise)$")


@router.post("/change-plan")
async def change_plan(req: ChangePlanRequest, user=Depends(get_current_user)):
    """租户自助变更套餐（仅 owner）"""
    if user["role"] != "owner":
        raise HTTPException(status_code=403, detail="需要 owner 权限才能变更套餐")

    from app.core.config import settings
    new_plan = req.plan
    plan_limits = settings.PLAN_LIMITS.get(new_plan, settings.PLAN_LIMITS["free"])

    # 检查是否超出限制（降级时）
    current_members = await database.pool.fetch(
        "SELECT id FROM users WHERE tenant_id = $1", user["tenant_id"]
    )
    if len(current_members) > plan_limits["member_limit"]:
        raise HTTPException(
            status_code=400,
            detail=f"当前成员数({len(current_members)})超出目标套餐上限({plan_limits[member_limit]})，请先移除多余成员"
        )

    await database.update_tenant_plan(user["tenant_id"], new_plan)

    # 更新订阅记录
    await database.pool.execute(
        "UPDATE subscriptions SET plan = $1, message_quota = $2, tg_account_limit = $3, mapping_limit = $4 WHERE tenant_id = $5 AND status = active",
        new_plan,
        plan_limits.get("message_quota", 100),
        plan_limits.get("tg_account_limit", 1),
        plan_limits.get("mapping_limit", 3),
        user["tenant_id"]
    )

    await database.add_audit_log(
        user["tenant_id"], user["id"], "change_plan",
        detail=f"套餐变更为 {new_plan}"
    )

    return {"message": f"套餐已变更为 {new_plan}", "plan": new_plan, "limits": plan_limits}
