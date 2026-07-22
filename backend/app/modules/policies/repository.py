from app.core.database import database


class PolicyRepository:
    async def default_template_for_forwarding(self, tenant_id: int):
        return await database.fetchrow(
            """SELECT * FROM message_templates
               WHERE tenant_id=$1 AND enabled=TRUE AND is_default=TRUE LIMIT 1""",
            tenant_id,
        )

    async def media_for_forwarding(self, tenant_id: int):
        return await database.fetchrow("SELECT * FROM media_configs WHERE tenant_id=$1", tenant_id)

    async def filters(self, tenant_id: int):
        return await database.fetch(
            "SELECT * FROM filter_rules WHERE tenant_id=$1 ORDER BY priority,id", tenant_id
        )

    async def create_filter(self, tenant_id: int, payload):
        return await database.fetchrow(
            """INSERT INTO filter_rules
               (tenant_id,name,rule_type,config,description,priority,enabled)
               VALUES($1,$2,$3,$4::jsonb,$5,$6,$7) RETURNING *""",
            tenant_id, payload.name, payload.rule_type, payload.config,
            payload.description, payload.priority, payload.enabled,
        )

    async def update_filter(self, tenant_id: int, rule_id: int, payload):
        return await database.fetchrow(
            """UPDATE filter_rules SET name=$3,rule_type=$4,config=$5::jsonb,
               description=$6,priority=$7,enabled=$8,updated_at=NOW()
               WHERE tenant_id=$1 AND id=$2 RETURNING *""",
            tenant_id, rule_id, payload.name, payload.rule_type, payload.config,
            payload.description, payload.priority, payload.enabled,
        )

    async def delete_filter(self, tenant_id: int, rule_id: int):
        return await database.fetchval(
            "DELETE FROM filter_rules WHERE tenant_id=$1 AND id=$2 RETURNING id", tenant_id, rule_id
        )

    async def templates(self, tenant_id: int):
        return await database.fetch(
            "SELECT * FROM message_templates WHERE tenant_id=$1 ORDER BY is_default DESC,created_at DESC",
            tenant_id,
        )

    async def template(self, tenant_id: int, template_id: int):
        return await database.fetchrow(
            "SELECT * FROM message_templates WHERE tenant_id=$1 AND id=$2", tenant_id, template_id
        )

    async def create_template(self, tenant_id: int, payload):
        async with database.transaction() as connection:
            if payload.is_default:
                await connection.execute(
                    "UPDATE message_templates SET is_default=FALSE,updated_at=NOW() WHERE tenant_id=$1",
                    tenant_id,
                )
            row = await connection.fetchrow(
                """INSERT INTO message_templates
                   (tenant_id,name,template_text,time_format,enabled,is_default)
                   VALUES($1,$2,$3,$4,$5,$6) RETURNING *""",
                tenant_id, payload.name, payload.template_text, payload.time_format,
                payload.enabled, payload.is_default,
            )
        return dict(row)

    async def update_template(self, tenant_id: int, template_id: int, payload):
        async with database.transaction() as connection:
            if payload.is_default:
                await connection.execute(
                    "UPDATE message_templates SET is_default=FALSE,updated_at=NOW() WHERE tenant_id=$1",
                    tenant_id,
                )
            row = await connection.fetchrow(
                """UPDATE message_templates SET name=$3,template_text=$4,time_format=$5,
                   enabled=$6,is_default=$7,updated_at=NOW()
                   WHERE tenant_id=$1 AND id=$2 RETURNING *""",
                tenant_id, template_id, payload.name, payload.template_text,
                payload.time_format, payload.enabled, payload.is_default,
            )
        return dict(row) if row else None

    async def default_template(self, tenant_id: int, template_id: int):
        async with database.transaction() as connection:
            exists = await connection.fetchval(
                "SELECT id FROM message_templates WHERE tenant_id=$1 AND id=$2", tenant_id, template_id
            )
            if not exists:
                return None
            await connection.execute(
                "UPDATE message_templates SET is_default=FALSE,updated_at=NOW() WHERE tenant_id=$1",
                tenant_id,
            )
            row = await connection.fetchrow(
                """UPDATE message_templates SET is_default=TRUE,enabled=TRUE,updated_at=NOW()
                   WHERE tenant_id=$1 AND id=$2 RETURNING *""",
                tenant_id, template_id,
            )
        return dict(row)

    async def delete_template(self, tenant_id: int, template_id: int):
        return await database.fetchval(
            "DELETE FROM message_templates WHERE tenant_id=$1 AND id=$2 RETURNING id",
            tenant_id, template_id,
        )

    async def media(self, tenant_id: int):
        await database.execute(
            "INSERT INTO media_configs(tenant_id) VALUES($1) ON CONFLICT(tenant_id) DO NOTHING",
            tenant_id,
        )
        return await database.fetchrow("SELECT * FROM media_configs WHERE tenant_id=$1", tenant_id)

    async def save_media(self, tenant_id: int, payload):
        return await database.fetchrow(
            """INSERT INTO media_configs
               (tenant_id,max_file_size_bytes,allowed_types,thumbnail_enabled,
                thumbnail_max_width,thumbnail_quality,forward_as_link)
               VALUES($1,$2,$3::jsonb,$4,$5,$6,$7)
               ON CONFLICT(tenant_id) DO UPDATE SET
                 max_file_size_bytes=EXCLUDED.max_file_size_bytes,
                 allowed_types=EXCLUDED.allowed_types,
                 thumbnail_enabled=EXCLUDED.thumbnail_enabled,
                 thumbnail_max_width=EXCLUDED.thumbnail_max_width,
                 thumbnail_quality=EXCLUDED.thumbnail_quality,
                 forward_as_link=EXCLUDED.forward_as_link,updated_at=NOW()
               RETURNING *""",
            tenant_id, payload.max_file_size_bytes, payload.allowed_types,
            payload.thumbnail_enabled, payload.thumbnail_max_width,
            payload.thumbnail_quality, payload.forward_as_link,
        )

    async def translation(self, tenant_id: int):
        return await database.fetchrow(
            "SELECT * FROM translation_configs WHERE tenant_id=$1", tenant_id
        )

    async def save_translation(self, tenant_id: int, payload):
        return await database.fetchrow(
            """INSERT INTO translation_configs(tenant_id,api_key,base_url,model,enabled)
               VALUES($1,$2,$3,$4,$5)
               ON CONFLICT(tenant_id) DO UPDATE SET api_key=EXCLUDED.api_key,
                 base_url=EXCLUDED.base_url,model=EXCLUDED.model,enabled=EXCLUDED.enabled,
                 updated_at=NOW() RETURNING *""",
            tenant_id, payload.api_key, payload.base_url, payload.model, payload.enabled,
        )


policy_repository = PolicyRepository()
