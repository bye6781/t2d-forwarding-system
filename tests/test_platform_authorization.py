import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock


def test_platform_service_manages_target_tenant_authorizations(monkeypatch):
    from app.modules.platform.repository import platform_repository
    from app.modules.platform.service import platform_service
    from app.modules.tenants.repository import tenant_repository

    monkeypatch.setattr(platform_repository, "tenant", AsyncMock(return_value={"id": 9}))
    create = AsyncMock(return_value={"id": 21, "role": "viewer"})
    update = AsyncMock(return_value={"id": 21, "role": "member"})
    delete = AsyncMock(return_value=21)
    monkeypatch.setattr(tenant_repository, "create_member", create)
    monkeypatch.setattr(tenant_repository, "update_member", update)
    monkeypatch.setattr(tenant_repository, "delete_member", delete)

    async def scenario():
        payload = SimpleNamespace(username="viewer9", password="StrongPass9", email=None, role="viewer")
        assert (await platform_service.create_member(9, payload))["role"] == "viewer"
        assert (await platform_service.update_member(9, 21, SimpleNamespace(role="member", is_active=True)))["role"] == "member"
        await platform_service.delete_member(9, 21)
        assert create.await_args.args[0] == 9
        assert update.await_args.args[:2] == (9, 21)
        assert delete.await_args.args == (9, 21)

    asyncio.run(scenario())
