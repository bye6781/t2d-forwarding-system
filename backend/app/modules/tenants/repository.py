from app.core.database import database


class TenantRepository:
    async def active_context(self, tenant_id: int):
        return await database.fetchrow(
            """SELECT t.status,COALESCE(s.plan,'free') AS plan
               FROM tenants t LEFT JOIN LATERAL (
                 SELECT plan FROM subscriptions WHERE tenant_id=t.id AND status='active'
                 ORDER BY created_at DESC LIMIT 1
               ) s ON TRUE WHERE t.id=$1""",
            tenant_id,
        )

    async def active_subscription(self, tenant_id: int):
        return await database.fetchrow(
            """SELECT * FROM subscriptions WHERE tenant_id=$1 AND status='active'
               ORDER BY created_at DESC LIMIT 1""",
            tenant_id,
        )

    async def today_usage(self, tenant_id: int):
        return await database.fetchrow(
            """SELECT messages_count,translation_chars FROM usage_records
               WHERE tenant_id=$1 AND date=CURRENT_DATE""",
            tenant_id,
        ) or {"messages_count": 0, "translation_chars": 0}

    async def increment_usage(self, tenant_id: int, messages: int, translation_chars: int):
        await database.execute(
            """INSERT INTO usage_records(tenant_id,date,messages_count,translation_chars)
               VALUES($1,CURRENT_DATE,$2,$3)
               ON CONFLICT(tenant_id,date) DO UPDATE SET
                 messages_count=usage_records.messages_count+EXCLUDED.messages_count,
                 translation_chars=usage_records.translation_chars+EXCLUDED.translation_chars""",
            tenant_id, messages, translation_chars,
        )

    async def profile(self, tenant_id: int):
        return await database.fetchrow(
            """SELECT t.id,t.name,t.slug,t.status,t.created_at,s.plan,s.message_quota,
                      s.tg_account_limit,s.mapping_limit
               FROM tenants t LEFT JOIN LATERAL (
                 SELECT * FROM subscriptions WHERE tenant_id=t.id AND status='active'
                 ORDER BY created_at DESC LIMIT 1
               ) s ON TRUE WHERE t.id=$1""", tenant_id,
        )

    async def members(self, tenant_id: int):
        return await database.fetch(
            """SELECT id,username,email,role,is_active,created_at,last_login
               FROM users WHERE tenant_id=$1 ORDER BY created_at""", tenant_id,
        )

    async def create_member(self, tenant_id: int, username: str, password_hash: str, email: str | None, role: str):
        return await database.fetchrow(
            """INSERT INTO users(tenant_id,username,password_hash,email,role)
               VALUES($1,$2,$3,$4,$5) RETURNING id,username,email,role,is_active,created_at,last_login""",
            tenant_id, username, password_hash, email, role,
        )

    async def update_member(self, tenant_id: int, member_id: int, role: str | None, is_active: bool | None):
        return await database.fetchrow(
            """UPDATE users SET role=COALESCE($3,role),is_active=COALESCE($4,is_active)
               WHERE tenant_id=$1 AND id=$2 AND role<>'owner'
               RETURNING id,username,email,role,is_active,created_at,last_login""",
            tenant_id, member_id, role, is_active,
        )

    async def delete_member(self, tenant_id: int, member_id: int):
        return await database.fetchval(
            "DELETE FROM users WHERE tenant_id=$1 AND id=$2 AND role<>'owner' RETURNING id",
            tenant_id, member_id,
        )

    async def usage(self, tenant_id: int):
        return await database.fetchrow(
            """SELECT s.plan,s.message_quota,COALESCE(u.messages_count,0) today_messages,
                      COALESCE(u.translation_chars,0) today_translation_chars
               FROM subscriptions s LEFT JOIN usage_records u
                 ON u.tenant_id=s.tenant_id AND u.date=CURRENT_DATE
               WHERE s.tenant_id=$1 AND s.status='active'
               ORDER BY s.created_at DESC LIMIT 1""", tenant_id,
        )

    async def update_plan(self, tenant_id: int, plan: str, limits: dict[str, int]):
        async with database.transaction() as connection:
            await connection.execute("UPDATE tenants SET plan=$2,updated_at=NOW() WHERE id=$1", tenant_id, plan)
            row = await connection.fetchrow(
                """UPDATE subscriptions SET plan=$2,message_quota=$3,tg_account_limit=$4,
                       mapping_limit=$5
                   WHERE id=(SELECT id FROM subscriptions WHERE tenant_id=$1 AND status='active'
                             ORDER BY created_at DESC LIMIT 1) RETURNING *""",
                tenant_id, plan, limits["message_quota"], limits["tg_account_limit"], limits["mapping_limit"],
            )
        return dict(row) if row else None


tenant_repository = TenantRepository()
