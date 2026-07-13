"""
认证路由：注册、登录、用户信息
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional

from app.core.security import hash_password, verify_password, create_access_token
from app.core.dependencies import get_current_user
from app.core.database import database
from app.core.tenant_context import TenantContext

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["认证"])


class RegisterRequest(BaseModel):
    team_name: str = Field(..., min_length=2, max_length=50, description="团队名称")
    username: str = Field(..., min_length=3, max_length=30, description="用户名")
    password: str = Field(..., min_length=6, max_length=50, description="密码")
    email: Optional[str] = Field(None, description="邮箱")


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=6, max_length=50)


@router.post("/register", response_model=TokenResponse)
async def register(req: RegisterRequest):
    """注册新租户（团队）"""
    # 检查用户名是否已存在（全局唯一）
    existing = await database.get_user_by_email(req.username)
    if not existing:
        existing = await database.fetchrow(
            "SELECT id FROM users WHERE username = $1", req.username
        )
    if existing:
        raise HTTPException(status_code=400, detail="用户名已存在")

    # 创建租户
    slug = req.team_name.lower().replace(" ", "-")[:50]
    # 确保 slug 唯一
    existing_tenant = await database.get_tenant_by_slug(slug)
    if existing_tenant:
        slug = f"{slug}-{int(__import__(time).time()) % 10000}"

    tenant_id = await database.create_tenant(req.team_name, slug)

    # 创建 owner 用户
    password_hash = hash_password(req.password)
    user_id = await database.create_user(
        tenant_id=tenant_id,
        username=req.username,
        password_hash=password_hash,
        email=req.email,
        role="owner"
    )

    # 创建免费订阅
    await database.create_subscription(
        tenant_id=tenant_id,
        plan="free",
        message_quota=100,
        tg_account_limit=1,
        mapping_limit=3,
    )

    logger.info(f"New tenant registered: {req.team_name} (id={tenant_id}), owner: {req.username}")

    # 返回 token
    token = create_access_token({"sub": str(user_id), "tenant_id": tenant_id})
    return TokenResponse(
        access_token=token,
        user={
            "id": user_id,
            "username": req.username,
            "role": "owner",
            "tenant_id": tenant_id,
            "team_name": req.team_name,
        }
    )


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest):
    """登录"""
    # 按用户名查找（全局查找，因为用户可能不记得自己的租户）
    user = await database.fetchrow(
        "SELECT * FROM users WHERE username = $1", req.username
    )
    if not user:
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    if not verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    if not user["is_active"]:
        raise HTTPException(status_code=403, detail="账户已被禁用")

    # 检查租户状态
    tenant = await database.get_tenant(user["tenant_id"])
    if not tenant or tenant["status"] != "active":
        raise HTTPException(status_code=403, detail="租户已停用")

    # 更新最后登录时间
    await database.update_last_login(user["id"])

    # 生成 token
    token = create_access_token({
        "sub": str(user["id"]),
        "tenant_id": user["tenant_id"]
    })

    return TokenResponse(
        access_token=token,
        user={
            "id": user["id"],
            "username": user["username"],
            "email": user["email"],
            "role": user["role"],
            "tenant_id": user["tenant_id"],
            "team_name": tenant["name"],
            "plan": tenant["plan"],
        }
    )


@router.get("/me")
async def get_me(user=Depends(get_current_user)):
    """获取当前用户信息"""
    tenant = await database.get_tenant(user["tenant_id"])
    return {
        "id": user["id"],
        "username": user["username"],
        "email": user["email"],
        "role": user["role"],
        "tenant_id": user["tenant_id"],
        "team_name": tenant["name"] if tenant else "",
        "plan": tenant["plan"] if tenant else "free",
    }


@router.put("/password")
async def change_password(req: ChangePasswordRequest, user=Depends(get_current_user)):
    """修改密码"""
    if not verify_password(req.old_password, user["password_hash"]):
        raise HTTPException(status_code=400, detail="原密码错误")

    new_hash = hash_password(req.new_password)
    await database.execute(
        "UPDATE users SET password_hash = $1 WHERE id = $2",
        new_hash, user["id"]
    )
    return {"message": "密码修改成功"}
