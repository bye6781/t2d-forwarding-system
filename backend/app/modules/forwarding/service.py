from fastapi import HTTPException

from app.modules.forwarding.repository import forwarding_repository
from app.modules.forwarding.runtime import tenant_runtime
from app.modules.tenants.entitlements import require_feature
from app.modules.tenants.service import tenant_service
from app.services.telegram_service import telegram_service


class ForwardingDomainService:
    async def status(self, user: dict):
        accounts = await forwarding_repository.authorized_accounts(user["tenant_id"])
        for account in accounts:
            account["connected"] = telegram_service.is_connected(user["tenant_id"], account["id"])
        return {"running": await tenant_runtime.is_running(user["tenant_id"]), "accounts": accounts}

    async def start(self, user: dict):
        require_feature(user, "runtime")
        if not await forwarding_repository.authorized_accounts(user["tenant_id"]):
            raise HTTPException(400, "请先授权 Telegram 账号")
        if not any(row["enabled"] for row in await forwarding_repository.routes(user["tenant_id"])):
            raise HTTPException(400, "请先启用至少一条转发线路")
        await tenant_runtime.start(user["tenant_id"])

    async def stop(self, user: dict):
        require_feature(user, "runtime")
        await tenant_runtime.stop(user["tenant_id"])

    async def routes(self, user: dict):
        require_feature(user, "routes")
        return await forwarding_repository.routes(user["tenant_id"])

    async def create_route(self, user: dict, payload):
        require_feature(user, "routes")
        current = await forwarding_repository.routes(user["tenant_id"])
        profile = await tenant_service.profile(user)
        if profile["mapping_limit"] is not None and len(current) >= profile["mapping_limit"]:
            raise HTTPException(403, "转发线路数量已达套餐上限")
        row = await forwarding_repository.create_route(user["tenant_id"], payload)
        if not row:
            raise HTTPException(400, "目标机器人不存在或不属于当前租户")
        return row

    async def update_route(self, user: dict, route_id: int, payload):
        require_feature(user, "routes")
        row = await forwarding_repository.update_route(
            user["tenant_id"], route_id, payload.model_dump(exclude_none=True)
        )
        if not row:
            raise HTTPException(404, "线路不存在或目标机器人无效")
        return row

    async def delete_route(self, user: dict, route_id: int):
        require_feature(user, "routes")
        if not await forwarding_repository.delete_route(user["tenant_id"], route_id):
            raise HTTPException(404, "转发线路不存在")

    async def dashboard(self, user: dict):
        require_feature(user, "dashboard")
        aggregate = dict(await forwarding_repository.dashboard(user["tenant_id"]))
        runtime = await self.status(user)
        usage = await tenant_service.usage(user)
        aggregate["system_status"] = {
            "telegram_connected": sum(1 for account in runtime["accounts"] if account.get("connected")),
            "dingtalk_configured": aggregate.get("dingtalk_bots", 0),
            "runtime_running": runtime["running"],
        }
        aggregate["quota"] = usage
        return aggregate


forwarding_domain_service = ForwardingDomainService()
