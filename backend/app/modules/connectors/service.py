from fastapi import HTTPException

from app.modules.connectors.repository import connector_repository
from app.modules.tenants.entitlements import require_feature
from app.modules.tenants.service import tenant_service
from app.services.dingtalk_service import dingtalk_service
from app.services.telegram_service import telegram_service


class ConnectorService:
    @staticmethod
    def _public_telegram(row: dict) -> dict:
        row = dict(row)
        row.pop("api_hash", None)
        return row

    @staticmethod
    def _public_bot(row: dict) -> dict:
        row = dict(row)
        webhook = row.pop("webhook", "")
        row.pop("secret", None)
        if "access_token=" in webhook:
            row["webhook_masked"] = webhook.split("access_token=", 1)[0] + "access_token=••••" + webhook.rsplit("access_token=", 1)[1][-6:]
        else:
            row["webhook_masked"] = (webhook[:12] + "••••") if webhook else ""
        return row

    async def telegram_accounts(self, user: dict):
        require_feature(user, "telegram")
        rows = await connector_repository.telegram_accounts(user["tenant_id"])
        for row in rows:
            row["connected"] = telegram_service.is_connected(user["tenant_id"], row["id"])
        return [self._public_telegram(row) for row in rows]

    async def create_telegram(self, user: dict, payload):
        require_feature(user, "telegram")
        existing = await connector_repository.telegram_accounts(user["tenant_id"])
        profile = await tenant_service.profile(user)
        if profile["tg_account_limit"] is not None and len(existing) >= profile["tg_account_limit"]:
            raise HTTPException(403, "Telegram 账号数量已达套餐上限")
        return self._public_telegram(await connector_repository.create_telegram(user["tenant_id"], payload))

    async def telegram_action(self, user: dict, account_id: int, action: str, payload):
        require_feature(user, "telegram")
        account = await connector_repository.telegram_account(user["tenant_id"], account_id)
        if not account:
            raise HTTPException(404, "Telegram 账号不存在")
        if action == "send-code":
            result = await telegram_service.send_code(
                user["tenant_id"], account_id, account["api_id"], account["api_hash"], account["phone"]
            )
            if not result.get("success"):
                raise HTTPException(502, result.get("error", "Telegram 验证码发送失败"))
            return result
        if action == "verify":
            if not payload.code:
                raise HTTPException(422, "验证码不能为空")
            result = await telegram_service.verify_code(
                user["tenant_id"], account_id, account["api_id"], account["api_hash"],
                account["phone"], payload.code, payload.password,
            )
            if not result.get("success"):
                raise HTTPException(400, result.get("error", "Telegram 验证失败"))
            await connector_repository.telegram_status(user["tenant_id"], account_id, "connected", True)
            return {"message": "Telegram 账号已连接"}
        if action == "disconnect":
            await telegram_service.disconnect_account(user["tenant_id"], account_id)
            await connector_repository.telegram_status(user["tenant_id"], account_id, "disconnected", False)
            return {"message": "Telegram 账号已断开"}
        if action == "dialogs":
            return await telegram_service.get_dialogs(user["tenant_id"], account_id)
        raise HTTPException(404, "不支持的操作")

    async def delete_telegram(self, user: dict, account_id: int):
        require_feature(user, "telegram")
        if not await connector_repository.telegram_account(user["tenant_id"], account_id):
            raise HTTPException(404, "Telegram 账号不存在")
        await telegram_service.disconnect_account(user["tenant_id"], account_id)
        await connector_repository.delete_telegram(user["tenant_id"], account_id)

    async def bots(self, user: dict):
        require_feature(user, "dingtalk")
        return [self._public_bot(row) for row in await connector_repository.bots(user["tenant_id"])]

    async def create_bot(self, user: dict, payload):
        require_feature(user, "dingtalk")
        existing = await connector_repository.bots(user["tenant_id"])
        profile = await tenant_service.profile(user)
        if profile["bot_limit"] is not None and len(existing) >= profile["bot_limit"]:
            raise HTTPException(403, "钉钉机器人数量已达套餐上限")
        return self._public_bot(await connector_repository.create_bot(user["tenant_id"], payload))

    async def update_bot(self, user: dict, bot_db_id: int, payload):
        require_feature(user, "dingtalk")
        row = await connector_repository.update_bot(
            user["tenant_id"], bot_db_id, payload.model_dump(exclude_none=True)
        )
        if not row:
            raise HTTPException(404, "钉钉机器人不存在")
        return self._public_bot(row)

    async def delete_bot(self, user: dict, bot_db_id: int):
        require_feature(user, "dingtalk")
        if not await connector_repository.delete_bot(user["tenant_id"], bot_db_id):
            raise HTTPException(404, "钉钉机器人不存在")

    async def test_bot(self, user: dict, bot_db_id: int, message: str):
        require_feature(user, "dingtalk")
        bot = await connector_repository.bot(user["tenant_id"], bot_db_id)
        if not bot:
            raise HTTPException(404, "钉钉机器人不存在")
        result = await dingtalk_service.send_text(
            webhook=bot["webhook"], content=message, secret=bot.get("secret", ""), bot_id=bot["bot_id"]
        )
        if result.get("errcode") != 0:
            raise HTTPException(502, result.get("errmsg", "钉钉测试发送失败"))
        return result


connector_service = ConnectorService()
