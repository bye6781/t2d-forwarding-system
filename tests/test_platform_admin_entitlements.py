import asyncio
from unittest.mock import AsyncMock


def test_platform_admin_profile_and_usage_are_unlimited(monkeypatch):
    from app.modules.tenants.repository import tenant_repository
    from app.modules.tenants.service import tenant_service

    monkeypatch.setattr(tenant_repository, "profile", AsyncMock(return_value={
        "id": 0, "name": "Platform", "plan": "free", "status": "active",
    }))
    monkeypatch.setattr(tenant_repository, "active_subscription", AsyncMock(return_value=None))
    monkeypatch.setattr(tenant_repository, "today_usage", AsyncMock(return_value={
        "messages_count": 137, "translation_chars": 29,
    }))

    async def scenario():
        user = {"tenant_id": 0, "role": "owner", "is_platform_admin": True}
        profile = await tenant_service.profile(user)
        usage = await tenant_service.usage(user)
        assert profile["is_unlimited"] is True
        for key in ("message_quota", "tg_account_limit", "mapping_limit", "bot_limit", "member_limit"):
            assert profile[key] is None
        assert usage == {
            "plan": "free",
            "message_quota": None,
            "today_messages": 137,
            "today_translation_chars": 29,
            "remaining": None,
            "usage_percent": None,
            "is_unlimited": True,
        }

    asyncio.run(scenario())


def test_normal_tenant_quota_contract_is_unchanged(monkeypatch):
    from app.modules.tenants.repository import tenant_repository
    from app.modules.tenants.service import tenant_service

    monkeypatch.setattr(tenant_repository, "usage", AsyncMock(return_value={
        "plan": "free", "message_quota": 100,
        "today_messages": 25, "today_translation_chars": 0,
    }))

    async def scenario():
        usage = await tenant_service.usage({
            "tenant_id": 7, "role": "owner", "is_platform_admin": False,
        })
        assert usage["is_unlimited"] is False
        assert usage["message_quota"] == 100
        assert usage["remaining"] == 75
        assert usage["usage_percent"] == 25.0

    asyncio.run(scenario())


def test_tenant_owner_cannot_change_its_own_plan():
    from fastapi import HTTPException
    from app.modules.tenants.service import tenant_service

    async def scenario():
        try:
            await tenant_service.update_plan(
                {"tenant_id": 7, "role": "owner", "is_platform_admin": False}, "pro"
            )
        except HTTPException as exc:
            assert exc.status_code == 403
            assert "平台管理员" in str(exc.detail)
        else:
            raise AssertionError("tenant owners must not change plans")

    asyncio.run(scenario())


def test_platform_runtime_bypasses_message_and_resource_limits(monkeypatch):
    from app.modules.tenants.repository import tenant_repository
    from app.services.quota_service import quota_service

    subscription = AsyncMock(side_effect=AssertionError("platform quota must not query subscription"))
    monkeypatch.setattr(tenant_repository, "active_subscription", subscription)

    async def scenario():
        assert await quota_service.check_message_quota(0) is True
        assert await quota_service.check_resource_limit(0, "mapping", 999999) is True
        subscription.assert_not_awaited()

    asyncio.run(scenario())
