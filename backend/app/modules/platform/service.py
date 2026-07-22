from fastapi import HTTPException

from app.core.config import settings
from app.core.security import hash_password
from app.modules.platform.repository import platform_repository
from app.modules.tenants.repository import tenant_repository


class PlatformService:
    async def _require_tenant(self, tenant_id: int):
        row = await platform_repository.tenant(tenant_id)
        if not row:
            raise HTTPException(404, "租户不存在")
        return row

    async def stats(self):
        return await platform_repository.stats()

    async def tenants(self):
        return await platform_repository.tenants()

    async def update_plan(self, tenant_id: int, plan: str):
        row = await tenant_repository.update_plan(tenant_id, plan, settings.PLAN_LIMITS[plan])
        if not row:
            raise HTTPException(404, "租户或活跃订阅不存在")
        return row

    async def update_status(self, tenant_id: int, status: str):
        row = await platform_repository.update_status(tenant_id, status)
        if not row:
            raise HTTPException(404, "租户不存在")
        return row

    async def members(self, tenant_id: int):
        await self._require_tenant(tenant_id)
        return await tenant_repository.members(tenant_id)

    async def create_member(self, tenant_id: int, payload):
        await self._require_tenant(tenant_id)
        try:
            return await tenant_repository.create_member(
                tenant_id, payload.username, hash_password(payload.password), payload.email, payload.role
            )
        except Exception as exc:
            if "unique" in str(exc).lower():
                raise HTTPException(409, "用户名或邮箱已存在") from exc
            raise

    async def update_member(self, tenant_id: int, member_id: int, payload):
        await self._require_tenant(tenant_id)
        row = await tenant_repository.update_member(tenant_id, member_id, payload.role, payload.is_active)
        if not row:
            raise HTTPException(404, "成员不存在或不能修改 owner")
        return row

    async def delete_member(self, tenant_id: int, member_id: int):
        await self._require_tenant(tenant_id)
        if not await tenant_repository.delete_member(tenant_id, member_id):
            raise HTTPException(404, "成员不存在或不能删除 owner")


platform_service = PlatformService()
