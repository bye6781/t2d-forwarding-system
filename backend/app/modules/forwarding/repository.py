from app.core.database import database


ROUTE_SELECT = """SELECT m.id,m.tenant_id,m.source_chat_id,m.translation_enabled,
                          m.filter_enabled,m.enabled,m.created_at,m.updated_at,
                          COALESCE(array_agg(mt.bot_id) FILTER (WHERE mt.bot_id IS NOT NULL),'{}') target_bot_ids
                   FROM mappings m LEFT JOIN mapping_targets mt ON mt.mapping_id=m.id"""


class ForwardingRepository:
    async def add_record(
        self, *, tenant_id: int, chat_id: int, message_id: int, bot_id: str,
        message_type: str, content_preview: str, status: str,
        error_message: str | None = None, processing_time_ms: int = 0,
    ) -> None:
        await database.execute(
            """INSERT INTO forward_records
               (tenant_id,telegram_chat_id,telegram_message_id,dingtalk_bot_id,
                message_type,content_preview,status,error_message,processing_time_ms)
               VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9)""",
            tenant_id, chat_id, message_id, bot_id, message_type, content_preview,
            status, error_message, processing_time_ms,
        )

    async def routes(self, tenant_id: int):
        return await database.fetch(
            ROUTE_SELECT + " WHERE m.tenant_id=$1 GROUP BY m.id ORDER BY m.created_at", tenant_id
        )

    async def route(self, tenant_id: int, route_id: int):
        return await database.fetchrow(
            ROUTE_SELECT + " WHERE m.tenant_id=$1 AND m.id=$2 GROUP BY m.id", tenant_id, route_id
        )

    async def create_route(self, tenant_id: int, payload):
        async with database.transaction() as connection:
            valid_count = await connection.fetchval(
                "SELECT COUNT(*) FROM dingtalk_bots WHERE tenant_id=$1 AND id=ANY($2::bigint[])",
                tenant_id, payload.target_bot_ids,
            )
            if valid_count != len(set(payload.target_bot_ids)):
                return None
            route_id = await connection.fetchval(
                """INSERT INTO mappings(tenant_id,source_chat_id,translation_enabled,filter_enabled,enabled)
                   VALUES($1,$2,$3,$4,$5) RETURNING id""",
                tenant_id, payload.source_chat_id, payload.translation_enabled,
                payload.filter_enabled, payload.enabled,
            )
            await connection.executemany(
                "INSERT INTO mapping_targets(mapping_id,bot_id) VALUES($1,$2)",
                [(route_id, bot_id) for bot_id in set(payload.target_bot_ids)],
            )
        return await self.route(tenant_id, route_id)

    async def update_route(self, tenant_id: int, route_id: int, values: dict):
        allowed = {"source_chat_id", "translation_enabled", "filter_enabled", "enabled"}
        scalar = {key: value for key, value in values.items() if key in allowed and value is not None}
        targets = values.get("target_bot_ids")
        async with database.transaction() as connection:
            exists = await connection.fetchval(
                "SELECT id FROM mappings WHERE tenant_id=$1 AND id=$2", tenant_id, route_id
            )
            if not exists:
                return None
            if scalar:
                assignments = ",".join(f"{key}=${index+3}" for index, key in enumerate(scalar))
                await connection.execute(
                    f"UPDATE mappings SET {assignments},updated_at=NOW() WHERE tenant_id=$1 AND id=$2",
                    tenant_id, route_id, *scalar.values(),
                )
            if targets is not None:
                valid_count = await connection.fetchval(
                    "SELECT COUNT(*) FROM dingtalk_bots WHERE tenant_id=$1 AND id=ANY($2::bigint[])",
                    tenant_id, targets,
                )
                if valid_count != len(set(targets)):
                    return None
                await connection.execute("DELETE FROM mapping_targets WHERE mapping_id=$1", route_id)
                await connection.executemany(
                    "INSERT INTO mapping_targets(mapping_id,bot_id) VALUES($1,$2)",
                    [(route_id, bot_id) for bot_id in set(targets)],
                )
        return await self.route(tenant_id, route_id)

    async def delete_route(self, tenant_id: int, route_id: int):
        return await database.fetchval(
            "DELETE FROM mappings WHERE tenant_id=$1 AND id=$2 RETURNING id", tenant_id, route_id
        )

    async def authorized_accounts(self, tenant_id: int):
        return await database.fetch(
            "SELECT id,name,phone,status,is_authorized FROM telegram_accounts WHERE tenant_id=$1 AND is_authorized",
            tenant_id,
        )

    async def records(self, tenant_id: int, limit: int, offset: int, status: str | None):
        condition = " AND status=$4" if status else ""
        values = [tenant_id, limit, offset] + ([status] if status else [])
        rows = await database.fetch(
            f"SELECT * FROM forward_records WHERE tenant_id=$1{condition} ORDER BY created_at DESC LIMIT $2 OFFSET $3",
            *values,
        )
        total = await database.fetchval(
            "SELECT COUNT(*) FROM forward_records WHERE tenant_id=$1" + (" AND status=$2" if status else ""),
            tenant_id, *([status] if status else []),
        )
        return rows, total

    async def dashboard(self, tenant_id: int):
        summary = await database.fetchrow(
            """SELECT
              COUNT(*) FILTER(WHERE created_at::date=CURRENT_DATE) AS today_messages,
              COUNT(*) FILTER(WHERE status='success' AND created_at::date=CURRENT_DATE) AS successful_forwards,
              COUNT(*) FILTER(WHERE status='failed' AND created_at::date=CURRENT_DATE) AS failed_forwards,
              (SELECT COUNT(*) FROM telegram_accounts WHERE tenant_id=$1) AS tg_accounts,
              (SELECT COUNT(*) FROM dingtalk_bots WHERE tenant_id=$1 AND enabled) AS dingtalk_bots,
              (SELECT COUNT(*) FROM mappings WHERE tenant_id=$1 AND enabled) AS active_routes
              FROM forward_records WHERE tenant_id=$1""",
            tenant_id,
        )
        trend = await database.fetch(
            """WITH days AS (
                 SELECT generate_series(CURRENT_DATE-INTERVAL '6 days',CURRENT_DATE,INTERVAL '1 day')::date AS day
               ), totals AS (
                 SELECT created_at::date AS day,
                        COUNT(DISTINCT (telegram_chat_id,telegram_message_id)) AS received,
                        COUNT(*) FILTER(WHERE status='success') AS forwarded
                 FROM forward_records WHERE tenant_id=$1 AND created_at>=CURRENT_DATE-INTERVAL '6 days'
                 GROUP BY created_at::date
               )
               SELECT days.day AS date,COALESCE(totals.received,0) AS received,
                      COALESCE(totals.forwarded,0) AS forwarded
               FROM days LEFT JOIN totals USING(day) ORDER BY days.day""",
            tenant_id,
        )
        type_distribution = await database.fetch(
            """SELECT message_type AS type,COUNT(*) AS count
               FROM forward_records WHERE tenant_id=$1 AND created_at>=CURRENT_DATE-INTERVAL '6 days'
               GROUP BY message_type ORDER BY count DESC""",
            tenant_id,
        )
        activity_rows = await database.fetch(
            """SELECT id,status,message_type,content_preview,created_at
               FROM forward_records WHERE tenant_id=$1 ORDER BY created_at DESC LIMIT 8""",
            tenant_id,
        )
        return {
            **dict(summary),
            "trend": [
                {**dict(row), "date": row["date"].isoformat() if hasattr(row["date"], "isoformat") else str(row["date"])}
                for row in trend
            ],
            "type_distribution": [dict(row) for row in type_distribution],
            "recent_activity": [
                {
                    "id": row["id"],
                    "type": "forward",
                    "title": row.get("content_preview") or f"{row.get('message_type', 'message')} message",
                    "status": row["status"],
                    "created_at": row["created_at"],
                }
                for row in activity_rows
            ],
        }


forwarding_repository = ForwardingRepository()
