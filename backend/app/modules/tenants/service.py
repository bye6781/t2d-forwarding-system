from fastapi import HTTPException

from app.core.config import settings
from app.core.security import hash_password
from app.modules.tenants.entitlements import require_authorization_admin, require_feature, resolve_entitlements
from app.modules.tenants.repository import tenant_repository


class TenantService:
    @staticmethod
    def _require_manager(user: dict) -> None:
        require_authorization_admin(user)

    async def profile(self, user: dict):
        row = await tenant_repository.profile(user["tenant_id"])
        if not row:
            raise HTTPException(404, "租户不存在")
        row = dict(row)
        plan = row.get("plan") or "free"
        return {
            **row,
            "plan": plan,
            "role": user.get("role", "member"),
            "is_platform_admin": bool(user.get("is_platform_admin")),
            **resolve_entitlements(user, plan).as_dict(),
        }

    async def members(self, user: dict):
        require_feature(user, "organization")
        return await tenant_repository.members(user["tenant_id"])

    async def create_member(self, user: dict, payload):
        require_feature(user, "organization")
        self._require_manager(user)
        current = await tenant_repository.members(user["tenant_id"])
        profile = await self.profile(user)
        if profile["member_limit"] is not None and len(current) >= profile["member_limit"]:
            raise HTTPException(403, "成员数量已达套餐上限")
        try:
            return await tenant_repository.create_member(
                user["tenant_id"], payload.username, hash_password(payload.password), payload.email, payload.role
            )
        except Exception as exc:
            if "unique" in str(exc).lower():
                raise HTTPException(409, "用户名或邮箱已存在") from exc
            raise

    async def update_member(self, user: dict, member_id: int, payload):
        require_feature(user, "organization")
        self._require_manager(user)
        row = await tenant_repository.update_member(
            user["tenant_id"], member_id, payload.role, payload.is_active
        )
        if not row:
            raise HTTPException(404, "成员不存在或不能修改 owner")
        return row

    async def delete_member(self, user: dict, member_id: int):
        require_feature(user, "organization")
        self._require_manager(user)
        if not await tenant_repository.delete_member(user["tenant_id"], member_id):
            raise HTTPException(404, "成员不存在或不能删除 owner")

    async def usage(self, user: dict):
        if user.get("is_platform_admin"):
            actual = await tenant_repository.today_usage(user["tenant_id"])
            return {
                "plan": "free",
                "message_quota": None,
                "today_messages": actual["messages_count"],
                "today_translation_chars": actual["translation_chars"],
                "remaining": None,
                "usage_percent": None,
                "is_unlimited": True,
            }
        row = await tenant_repository.usage(user["tenant_id"]) or {
            "plan": "free", "message_quota": settings.PLAN_LIMITS["free"]["message_quota"],
            "today_messages": 0, "today_translation_chars": 0,
        }
        row = dict(row)
        entitlement = resolve_entitlements(user, row["plan"])
        if entitlement.is_unlimited:
            if not row.get("today_messages") and not row.get("today_translation_chars"):
                actual = await tenant_repository.today_usage(user["tenant_id"])
                row["today_messages"] = actual["messages_count"]
                row["today_translation_chars"] = actual["translation_chars"]
            return {
                **row,
                "message_quota": None,
                "remaining": None,
                "usage_percent": None,
                "is_unlimited": True,
            }
        quota = row["message_quota"]
        return {**row, "remaining": max(0, quota-row["today_messages"]), "usage_percent": round(row["today_messages"]/quota*100, 1) if quota else 0, "is_unlimited": False}

    async def update_plan(self, user: dict, plan: str):
        raise HTTPException(403, "只有平台管理员可以调整套餐")


tenant_service = TenantService()
