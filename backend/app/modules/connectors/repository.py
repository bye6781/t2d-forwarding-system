from uuid import uuid4

from app.core.database import database


class ConnectorRepository:
    async def telegram_accounts(self, tenant_id: int):
        return await database.fetch(
            """SELECT id,tenant_id,name,phone,status,is_authorized,created_at,updated_at
               FROM telegram_accounts WHERE tenant_id=$1 ORDER BY created_at""", tenant_id
        )

    async def telegram_account(self, tenant_id: int, account_id: int):
        return await database.fetchrow(
            "SELECT * FROM telegram_accounts WHERE tenant_id=$1 AND id=$2", tenant_id, account_id
        )

    async def create_telegram(self, tenant_id: int, payload):
        return await database.fetchrow(
            """INSERT INTO telegram_accounts(tenant_id,name,api_id,api_hash,phone)
               VALUES($1,$2,$3,$4,$5) RETURNING *""",
            tenant_id, payload.name, payload.api_id, payload.api_hash, payload.phone,
        )

    async def telegram_status(self, tenant_id: int, account_id: int, status: str, authorized: bool):
        return await database.fetchrow(
            """UPDATE telegram_accounts SET status=$3,is_authorized=$4,updated_at=NOW()
               WHERE tenant_id=$1 AND id=$2 RETURNING *""",
            tenant_id, account_id, status, authorized,
        )

    async def delete_telegram(self, tenant_id: int, account_id: int):
        return await database.fetchval(
            "DELETE FROM telegram_accounts WHERE tenant_id=$1 AND id=$2 RETURNING id",
            tenant_id, account_id,
        )

    async def bots(self, tenant_id: int):
        return await database.fetch(
            "SELECT * FROM dingtalk_bots WHERE tenant_id=$1 ORDER BY created_at", tenant_id
        )

    async def authorized_accounts_for_startup(self):
        return await database.fetch(
            """SELECT a.* FROM telegram_accounts a JOIN tenants t ON t.id=a.tenant_id
               WHERE a.is_authorized AND t.status='active' AND t.id>0"""
        )

    async def bot(self, tenant_id: int, bot_db_id: int):
        return await database.fetchrow(
            "SELECT * FROM dingtalk_bots WHERE tenant_id=$1 AND id=$2", tenant_id, bot_db_id
        )

    async def create_bot(self, tenant_id: int, payload):
        bot_id = f"dingtalk-{uuid4().hex}"
        return await database.fetchrow(
            """INSERT INTO dingtalk_bots(tenant_id,bot_id,name,webhook,secret,enabled)
               VALUES($1,$2,$3,$4,$5,$6) RETURNING *""",
            tenant_id, bot_id, payload.name, payload.webhook, payload.secret, payload.enabled,
        )

    async def update_bot(self, tenant_id: int, bot_db_id: int, values: dict):
        allowed = {"name", "webhook", "secret", "enabled"}
        values = {key: value for key, value in values.items() if key in allowed and value is not None}
        if not values:
            return await self.bot(tenant_id, bot_db_id)
        assignments = ",".join(f"{key}=${index+3}" for index, key in enumerate(values))
        return await database.fetchrow(
            f"UPDATE dingtalk_bots SET {assignments},updated_at=NOW() WHERE tenant_id=$1 AND id=$2 RETURNING *",
            tenant_id, bot_db_id, *values.values(),
        )

    async def delete_bot(self, tenant_id: int, bot_db_id: int):
        return await database.fetchval(
            "DELETE FROM dingtalk_bots WHERE tenant_id=$1 AND id=$2 RETURNING id",
            tenant_id, bot_db_id,
        )


connector_repository = ConnectorRepository()
