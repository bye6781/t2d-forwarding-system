import re
import secrets

from fastapi import HTTPException

from app.core.config import settings
from app.core.security import create_access_token, hash_password, verify_password
from app.modules.auth.repository import auth_repository


class AuthService:
    @staticmethod
    def _slug(name: str) -> str:
        base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:42] or "team"
        return f"{base}-{secrets.token_hex(3)}"

    async def register(self, request) -> dict:
        if await auth_repository.find_by_username(request.username):
            raise HTTPException(409, "用户名已存在")
        tenant_id, user_id = await auth_repository.register(
            tenant_name=request.tenant_name,
            slug=self._slug(request.tenant_name),
            username=request.username,
            password_hash=hash_password(request.password),
            email=request.email,
            limits=settings.PLAN_LIMITS["free"],
        )
        user = {
            "id": user_id, "tenant_id": tenant_id, "username": request.username,
            "role": "owner", "is_platform_admin": False,
        }
        return {"access_token": create_access_token({"sub": str(user_id), "tenant_id": tenant_id}), "token_type": "bearer", "user": user}

    async def login(self, request, *, ip_address: str | None, user_agent: str | None) -> dict:
        user = await auth_repository.find_by_username(request.username)
        if not user or not verify_password(request.password, user["password_hash"]):
            await auth_repository.record_login(
                username=request.username, success=False, user=user,
                ip_address=ip_address, user_agent=user_agent, reason="invalid_credentials",
            )
            raise HTTPException(401, "用户名或密码错误")
        if not user.get("is_active", True):
            raise HTTPException(403, "账号已停用")
        admin = await auth_repository.is_platform_admin(user["id"])
        await auth_repository.update_last_login(user["id"])
        await auth_repository.record_login(
            username=request.username, success=True, user=user,
            ip_address=ip_address, user_agent=user_agent,
        )
        public_user = {
            "id": user["id"], "tenant_id": user["tenant_id"], "username": user["username"],
            "email": user.get("email"), "role": user["role"], "is_platform_admin": admin,
        }
        return {"access_token": create_access_token({"sub": str(user["id"]), "tenant_id": user["tenant_id"]}), "token_type": "bearer", "user": public_user}

    async def me(self, user: dict) -> dict:
        return {
            "id": user["id"], "tenant_id": user["tenant_id"], "username": user["username"],
            "email": user.get("email"), "role": user["role"],
            "is_platform_admin": await auth_repository.is_platform_admin(user["id"]),
        }

    async def change_password(self, user: dict, request) -> None:
        if not verify_password(request.old_password, user["password_hash"]):
            raise HTTPException(400, "原密码错误")
        await auth_repository.update_password(user["id"], hash_password(request.new_password))


auth_service = AuthService()
