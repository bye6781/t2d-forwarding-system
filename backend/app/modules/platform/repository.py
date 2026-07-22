from app.core.database import database


class PlatformRepository:
    async def tenant(self, tenant_id: int):
        return await database.fetchrow("SELECT id,name,slug,status FROM tenants WHERE id=$1 AND id>0", tenant_id)

    async def stats(self):
        return await database.fetchrow(
            """SELECT
              (SELECT COUNT(*) FROM tenants WHERE id>0) total_tenants,
              (SELECT COUNT(*) FROM users WHERE tenant_id>0 AND is_active) active_users,
              (SELECT COALESCE(SUM(messages_count),0) FROM usage_records WHERE tenant_id>0 AND date=CURRENT_DATE) today_messages,
              (SELECT COUNT(*) FROM subscriptions WHERE tenant_id>0 AND status='active') active_subscriptions"""
        )

    async def tenants(self):
        return await database.fetch(
            """SELECT t.id,t.name,t.slug,t.status,t.created_at,
                      COALESCE(s.plan,'free') plan,COUNT(u.id) user_count
               FROM tenants t
               LEFT JOIN LATERAL (SELECT plan FROM subscriptions WHERE tenant_id=t.id AND status='active' ORDER BY created_at DESC LIMIT 1) s ON TRUE
               LEFT JOIN users u ON u.tenant_id=t.id
               WHERE t.id>0 GROUP BY t.id,s.plan ORDER BY t.created_at DESC"""
        )

    async def update_status(self, tenant_id: int, status: str):
        return await database.fetchrow(
            "UPDATE tenants SET status=$2,updated_at=NOW() WHERE id=$1 AND id>0 RETURNING *",
            tenant_id, status,
        )


platform_repository = PlatformRepository()
