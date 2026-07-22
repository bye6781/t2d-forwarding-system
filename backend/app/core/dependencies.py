"""Authentication and tenant-context dependencies for the V2 API."""
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security import decode_access_token
from app.core.tenant_context import TenantContext
from app.modules.auth.repository import auth_repository
from app.modules.tenants.entitlements import require_feature
from app.modules.tenants.repository import tenant_repository

security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
):
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing credentials")

    payload = decode_access_token(credentials.credentials)
    if payload is None or payload.get("sub") is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    user = await auth_repository.user(int(payload["sub"]))
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    if not user["is_active"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled")

    tenant = await tenant_repository.active_context(user["tenant_id"])
    if not tenant or tenant["status"] != "active":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant disabled")

    TenantContext.set(user["tenant_id"], tenant["plan"])
    result = dict(user)
    result["is_platform_admin"] = await auth_repository.is_platform_admin(user["id"])
    return result


async def get_platform_admin(user=Depends(get_current_user)):
    if not user["is_platform_admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Platform administrator access required",
        )
    return user


def require_feature_access(feature: str):
    async def dependency(user=Depends(get_current_user)):
        require_feature(user, feature)
        return user

    return dependency
