"""
FastAPI 依赖注入（多租户版）
"""
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.security import decode_access_token
from app.core.tenant_context import TenantContext
from app.core.database import database

security = HTTPBearer(auto_error=False)


async def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    """获取当前用户，同时设置租户上下文"""
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未提供认证凭据")

    payload = decode_access_token(credentials.credentials)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效或过期的令牌")

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的令牌内容")

    user = await database.fetchrow("SELECT * FROM users WHERE id = $1", int(user_id))
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在")

    if not user["is_active"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账户已被禁用")

    # 设置租户上下文
    tenant = await database.get_tenant(user["tenant_id"])
    if not tenant or tenant["status"] != "active":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="租户已停用")

    TenantContext.set(user["tenant_id"], tenant["plan"])

    return dict(user)


async def get_optional_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    """可选认证，不强制"""
    if credentials is None:
        return None
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None


async def require_role(*roles: str):
    """角色权限检查"""
    role_list = list(roles)
    async def checker(user=Depends(get_current_user)):
        if user["role"] not in role_list:
            allowed = ", ".join(role_list)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"需要 {allowed} 角色权限"
            )
        return user
    return checker


async def get_platform_admin(user=Depends(get_current_user)):
    """平台管理员检查"""
    is_admin = await database.fetchrow(
        "SELECT 1 FROM platform_admins WHERE user_id = $1", user["id"]
    )
    if not is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要平台管理员权限")
    return user
