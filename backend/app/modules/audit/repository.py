from datetime import date, timedelta

from app.core.database import database


class AuditRepository:
    async def record_api_request(
        self, *, tenant_id: int, user_id: int, method: str, path: str,
        status_code: int, duration_ms: int, ip_address: str | None,
        user_agent: str | None,
    ) -> None:
        await database.execute(
            """INSERT INTO api_logs
               (tenant_id,user_id,method,path,status_code,duration_ms,ip_address,user_agent)
               VALUES($1,$2,$3,$4,$5,$6,$7,$8)""",
            tenant_id, user_id, method, path, status_code, duration_ms,
            ip_address, user_agent,
        )

    async def operations(self, tenant_id: int, limit: int, offset: int, action: str | None = None):
        values: list = [tenant_id]
        conditions = ["a.tenant_id=$1"]
        if action:
            values.append(f"%{action}%")
            conditions.append(f"a.action ILIKE ${len(values)}")
        count = await database.fetchval(
            f"SELECT COUNT(*) FROM audit_logs a WHERE {' AND '.join(conditions)}", *values
        )
        values.extend([limit, offset])
        rows = await database.fetch(
            f"""SELECT a.*,u.username FROM audit_logs a LEFT JOIN users u ON u.id=a.user_id
                WHERE {' AND '.join(conditions)} ORDER BY a.created_at DESC
                LIMIT ${len(values)-1} OFFSET ${len(values)}""", *values,
        )
        return rows, count

    async def logins(self, tenant_id: int, limit: int, offset: int):
        rows = await database.fetch(
            """SELECT *,CASE WHEN success THEN 'login_success' ELSE 'login_failed' END AS action,
                      reason AS detail FROM login_logs WHERE tenant_id=$1
               ORDER BY created_at DESC LIMIT $2 OFFSET $3""", tenant_id, limit, offset,
        )
        count = await database.fetchval("SELECT COUNT(*) FROM login_logs WHERE tenant_id=$1", tenant_id)
        return rows, count

    async def api(self, tenant_id: int, limit: int, offset: int):
        rows = await database.fetch(
            """SELECT a.*,a.status_code AS response_status,u.username FROM api_logs a
               LEFT JOIN users u ON u.id=a.user_id WHERE a.tenant_id=$1
               ORDER BY a.created_at DESC LIMIT $2 OFFSET $3""", tenant_id, limit, offset,
        )
        count = await database.fetchval("SELECT COUNT(*) FROM api_logs WHERE tenant_id=$1", tenant_id)
        return rows, count

    async def summary(self, tenant_id: int, days: int):
        return await database.fetchrow(
            """SELECT
              (SELECT COUNT(*) FROM audit_logs WHERE tenant_id=$1 AND created_at>=NOW()-make_interval(days=>$2)) total_operations,
              (SELECT COUNT(*) FROM login_logs WHERE tenant_id=$1 AND created_at>=NOW()-make_interval(days=>$2)) total_logins,
              (SELECT COUNT(*) FROM login_logs WHERE tenant_id=$1 AND NOT success AND created_at>=NOW()-make_interval(days=>$2)) failed_logins,
              (SELECT COUNT(*) FROM api_logs WHERE tenant_id=$1 AND created_at>=NOW()-make_interval(days=>$2)) total_api_calls,
              (SELECT COALESCE(AVG(duration_ms),0)::INTEGER FROM api_logs WHERE tenant_id=$1 AND created_at>=NOW()-make_interval(days=>$2)) avg_api_duration_ms""",
            tenant_id, days,
        )


audit_repository = AuditRepository()
