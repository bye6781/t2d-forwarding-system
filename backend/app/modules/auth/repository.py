from typing import Any

from app.core.database import database


class AuthRepository:
    async def user(self, user_id: int) -> dict[str, Any] | None:
        return await database.fetchrow("SELECT * FROM users WHERE id=$1", user_id)

    async def find_by_username(self, username: str) -> dict[str, Any] | None:
        return await database.fetchrow("SELECT * FROM users WHERE username=$1", username)

    async def is_platform_admin(self, user_id: int) -> bool:
        return bool(await database.fetchval(
            "SELECT EXISTS(SELECT 1 FROM platform_admins WHERE user_id=$1)", user_id
        ))

    async def platform_tenant_exists(self) -> bool:
        return bool(await database.fetchval("SELECT EXISTS(SELECT 1 FROM tenants WHERE id=0)"))

    async def register(
        self, *, tenant_name: str, slug: str, username: str,
        password_hash: str, email: str | None, limits: dict[str, int]
    ) -> tuple[int, int]:
        async with database.transaction() as connection:
            tenant_id = await connection.fetchval(
                "INSERT INTO tenants(name, slug, plan, status) VALUES($1,$2,'free','active') RETURNING id",
                tenant_name, slug,
            )
            user_id = await connection.fetchval(
                """INSERT INTO users(tenant_id, username, password_hash, email, role)
                   VALUES($1,$2,$3,$4,'owner') RETURNING id""",
                tenant_id, username, password_hash, email,
            )
            await connection.execute(
                """INSERT INTO subscriptions
                   (tenant_id, plan, status, message_quota, tg_account_limit, mapping_limit,
                    current_period_start, current_period_end)
                   VALUES($1,'free','active',$2,$3,$4,NOW(),NOW()+INTERVAL '30 days')""",
                tenant_id, limits["message_quota"], limits["tg_account_limit"], limits["mapping_limit"],
            )
        return tenant_id, user_id

    async def record_login(
        self, *, username: str, success: bool, user: dict | None,
        ip_address: str | None, user_agent: str | None, reason: str = ""
    ) -> None:
        await database.execute(
            """INSERT INTO login_logs
               (tenant_id,user_id,username,success,ip_address,user_agent,reason)
               VALUES($1,$2,$3,$4,$5,$6,$7)""",
            user.get("tenant_id") if user else None,
            user.get("id") if user else None,
            username, success, ip_address, user_agent, reason,
        )

    async def update_last_login(self, user_id: int) -> None:
        await database.execute("UPDATE users SET last_login=NOW() WHERE id=$1", user_id)

    async def update_password(self, user_id: int, password_hash: str) -> None:
        await database.execute("UPDATE users SET password_hash=$2 WHERE id=$1", user_id, password_hash)


auth_repository = AuthRepository()
