"""
PostgreSQL 数据库连接层
支持租户隔离的查询封装
"""
import os
import logging
from typing import Optional, List, Dict, Any, Sequence
from datetime import datetime, date

import asyncpg

from app.core.tenant_context import TenantContext

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://t2d:t2d-saas-2026@localhost:5432/t2d_saas"
)


class Database:
    """PostgreSQL 数据库管理器"""

    def __init__(self):
        self._pool: Optional[asyncpg.Pool] = None

    async def init(self):
        """初始化连接池"""
        self._pool = await asyncpg.create_pool(
            DATABASE_URL,
            min_size=2,
            max_size=20,
            command_timeout=30,
        )
        logger.info("Database connection pool created")

    async def close(self):
        """关闭连接池"""
        if self._pool:
            await self._pool.close()
            logger.info("Database connection pool closed")

    @property
    def pool(self) -> asyncpg.Pool:
        if not self._pool:
            raise RuntimeError("Database not initialized. Call init() first.")
        return self._pool

    # ---- 租户隔离查询 ----

    async def t_execute(self, query: str, *args, tenant_id: Optional[int] = None):
        """执行写操作（INSERT/UPDATE/DELETE），自动注入 tenant_id"""
        tid = tenant_id or TenantContext.require()
        return await self.pool.execute(query, tid, *args)

    async def t_fetch(self, query: str, *args, tenant_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """查询多行，自动注入 tenant_id"""
        tid = tenant_id or TenantContext.require()
        rows = await self.pool.fetch(query, tid, *args)
        return [dict(r) for r in rows]

    async def t_fetchrow(self, query: str, *args, tenant_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """查询单行，自动注入 tenant_id"""
        tid = tenant_id or TenantContext.require()
        row = await self.pool.fetchrow(query, tid, *args)
        return dict(row) if row else None

    async def t_fetchval(self, query: str, *args, tenant_id: Optional[int] = None):
        """查询单值，自动注入 tenant_id"""
        tid = tenant_id or TenantContext.require()
        return await self.pool.fetchval(query, tid, *args)

    # ---- 全局查询（不需要租户隔离） ----

    async def execute(self, query: str, *args):
        return await self.pool.execute(query, *args)

    async def fetch(self, query: str, *args) -> List[Dict[str, Any]]:
        rows = await self.pool.fetch(query, *args)
        return [dict(r) for r in rows]

    async def fetchrow(self, query: str, *args) -> Optional[Dict[str, Any]]:
        row = await self.pool.fetchrow(query, *args)
        return dict(row) if row else None

    async def fetchval(self, query: str, *args):
        return await self.pool.fetchval(query, *args)

    # ---- 用户操作 ----

    async def get_user_by_username(self, username: str, tenant_id: int) -> Optional[Dict]:
        return await self.t_fetchrow(
            "SELECT * FROM users WHERE username = $1 AND tenant_id = $2",
            username, tenant_id=tenant_id
        )

    async def get_user_by_email(self, email: str) -> Optional[Dict]:
        return await self.fetchrow(
            "SELECT * FROM users WHERE email = $1",
            email
        )

    async def create_user(self, tenant_id: int, username: str, password_hash: str,
                          email: Optional[str] = None, role: str = "member") -> int:
        return await self.pool.fetchval(
            """INSERT INTO users (tenant_id, username, password_hash, email, role)
               VALUES ($1, $2, $3, $4, $5) RETURNING id""",
            tenant_id, username, password_hash, email, role
        )

    async def update_last_login(self, user_id: int):
        await self.pool.execute(
            "UPDATE users SET last_login = NOW() WHERE id = $1",
            user_id
        )

    async def get_users_by_tenant(self, tenant_id: int) -> List[Dict]:
        return await self.t_fetch(
            "SELECT id, username, email, role, is_active, created_at, last_login FROM users WHERE tenant_id = $1 ORDER BY created_at",
            tenant_id=tenant_id
        )

    async def toggle_user(self, user_id: int, tenant_id: int):
        await self.t_execute(
            "UPDATE users SET is_active = NOT is_active WHERE id = $1 AND tenant_id = $2",
            user_id, tenant_id=tenant_id
        )

    # ---- 租户操作 ----

    async def create_tenant(self, name: str, slug: str) -> int:
        return await self.pool.fetchval(
            "INSERT INTO tenants (name, slug) VALUES ($1, $2) RETURNING id",
            name, slug
        )

    async def get_tenant(self, tenant_id: int) -> Optional[Dict]:
        return await self.fetchrow(
            "SELECT * FROM tenants WHERE id = $1",
            tenant_id
        )

    async def get_tenant_by_slug(self, slug: str) -> Optional[Dict]:
        return await self.fetchrow(
            "SELECT * FROM tenants WHERE slug = $1",
            slug
        )

    async def update_tenant_plan(self, tenant_id: int, plan: str):
        await self.pool.execute(
            "UPDATE tenants SET plan = $1 WHERE id = $2",
            plan, tenant_id
        )

    # ---- 订阅操作 ----

    async def create_subscription(self, tenant_id: int, plan: str,
                                   message_quota: int, tg_account_limit: int,
                                   mapping_limit: int) -> int:
        return await self.pool.fetchval(
            """INSERT INTO subscriptions (tenant_id, plan, message_quota, tg_account_limit, mapping_limit, current_period_start, current_period_end)
               VALUES ($1, $2, $3, $4, $5, NOW(), NOW() + INTERVAL '30 days') RETURNING id""",
            tenant_id, plan, message_quota, tg_account_limit, mapping_limit
        )

    async def get_subscription(self, tenant_id: int) -> Optional[Dict]:
        return await self.fetchrow(
            "SELECT * FROM subscriptions WHERE tenant_id = $1 ORDER BY created_at DESC LIMIT 1",
            tenant_id
        )

    # ---- 用量操作 ----

    async def increment_usage(self, tenant_id: int, messages: int = 1, translation_chars: int = 0):
        today = date.today()
        await self.pool.execute(
            """INSERT INTO usage_records (tenant_id, date, messages_count, translation_chars)
               VALUES ($1, $2, $3, $4)
               ON CONFLICT (tenant_id, date)
               DO UPDATE SET messages_count = usage_records.messages_count + $3,
                             translation_chars = usage_records.translation_chars + $4""",
            tenant_id, today, messages, translation_chars
        )

    async def get_today_usage(self, tenant_id: int) -> Dict:
        today = date.today()
        row = await self.fetchrow(
            "SELECT messages_count, translation_chars FROM usage_records WHERE tenant_id = $1 AND date = $2",
            tenant_id, today
        )
        return row or {"messages_count": 0, "translation_chars": 0}

    # ---- Telegram 账号操作 ----

    async def get_tg_accounts(self, tenant_id: int) -> List[Dict]:
        return await self.t_fetch(
            "SELECT * FROM telegram_accounts WHERE tenant_id = $1 ORDER BY created_at",
            tenant_id=tenant_id
        )

    async def get_tg_account(self, account_id: int, tenant_id: int) -> Optional[Dict]:
        return await self.t_fetchrow(
            "SELECT * FROM telegram_accounts WHERE id = $1 AND tenant_id = $2",
            account_id, tenant_id=tenant_id
        )

    async def create_tg_account(self, tenant_id: int, name: str, api_id: int,
                                 api_hash: str, phone: str) -> int:
        return await self.pool.fetchval(
            """INSERT INTO telegram_accounts (tenant_id, name, api_id, api_hash, phone)
               VALUES ($1, $2, $3, $4, $5) RETURNING id""",
            tenant_id, name, api_id, api_hash, phone
        )

    async def update_tg_account_status(self, account_id: int, tenant_id: int,
                                        status: str, is_authorized: bool = None):
        if is_authorized is not None:
            await self.t_execute(
                "UPDATE telegram_accounts SET status = $1, is_authorized = $2 WHERE id = $3 AND tenant_id = $4",
                status, is_authorized, account_id, tenant_id=tenant_id
            )
        else:
            await self.t_execute(
                "UPDATE telegram_accounts SET status = $1 WHERE id = $2 AND tenant_id = $3",
                status, account_id, tenant_id=tenant_id
            )

    async def update_tg_account_session(self, account_id: int, tenant_id: int, session_file: str):
        await self.t_execute(
            "UPDATE telegram_accounts SET session_file = $1 WHERE id = $2 AND tenant_id = $3",
            session_file, account_id, tenant_id=tenant_id
        )

    async def delete_tg_account(self, account_id: int, tenant_id: int):
        await self.t_execute(
            "DELETE FROM telegram_accounts WHERE id = $1 AND tenant_id = $2",
            account_id, tenant_id=tenant_id
        )

    # ---- 钉钉 Bot 操作 ----

    async def get_dingtalk_bots(self, tenant_id: int) -> List[Dict]:
        return await self.t_fetch(
            "SELECT * FROM dingtalk_bots WHERE tenant_id = $1 ORDER BY created_at",
            tenant_id=tenant_id
        )

    async def get_dingtalk_bot(self, bot_id: str, tenant_id: int) -> Optional[Dict]:
        return await self.t_fetchrow(
            "SELECT * FROM dingtalk_bots WHERE bot_id = $1 AND tenant_id = $2",
            bot_id, tenant_id=tenant_id
        )

    async def create_dingtalk_bot(self, tenant_id: int, bot_id: str, name: str,
                                    webhook: str, secret: str = "") -> int:
        return await self.pool.fetchval(
            """INSERT INTO dingtalk_bots (tenant_id, bot_id, name, webhook, secret)
               VALUES ($1, $2, $3, $4, $5) RETURNING id""",
            tenant_id, bot_id, name, webhook, secret
        )

    async def update_dingtalk_bot(self, tenant_id: int, bot_id: str, **kwargs):
        sets = ", ".join(f"{k} = ${i+3}" for i, k in enumerate(kwargs.keys()))
        vals = list(kwargs.values())
        await self.t_execute(
            f"UPDATE dingtalk_bots SET {sets} WHERE bot_id = $1 AND tenant_id = $2",
            bot_id, tenant_id, *vals
        )

    async def delete_dingtalk_bot(self, bot_id: str, tenant_id: int):
        await self.t_execute(
            "DELETE FROM dingtalk_bots WHERE bot_id = $1 AND tenant_id = $2",
            bot_id, tenant_id=tenant_id
        )

    # ---- 映射操作 ----

    async def get_mappings(self, tenant_id: int) -> List[Dict]:
        return await self.t_fetch(
            "SELECT * FROM mappings WHERE tenant_id = $1 ORDER BY created_at",
            tenant_id=tenant_id
        )

    async def create_mapping(self, tenant_id: int, source_chat_id: int,
                              target_bot_ids: list, translation_enabled: bool = True,
                              filter_enabled: bool = True, enabled: bool = True) -> int:
        import json
        return await self.pool.fetchval(
            """INSERT INTO mappings (tenant_id, source_chat_id, target_bot_ids, translation_enabled, filter_enabled, enabled)
               VALUES ($1, $2, $3::jsonb, $4, $5, $6) RETURNING id""",
            tenant_id, source_chat_id, json.dumps(target_bot_ids),
            translation_enabled, filter_enabled, enabled
        )

    async def update_mapping(self, mapping_id: int, tenant_id: int, **kwargs):
        import json
        if "target_bot_ids" in kwargs:
            kwargs["target_bot_ids"] = json.dumps(kwargs["target_bot_ids"])
        sets = ", ".join(f"{k} = ${i+3}" for i, k in enumerate(kwargs.keys()))
        vals = list(kwargs.values())
        await self.t_execute(
            f"UPDATE mappings SET {sets} WHERE id = $2 AND tenant_id = $1",
            mapping_id, *vals, tenant_id=tenant_id
        )

    async def delete_mapping(self, mapping_id: int, tenant_id: int):
        await self.t_execute(
            "DELETE FROM mappings WHERE id = $1 AND tenant_id = $2",
            mapping_id, tenant_id=tenant_id
        )

    # ---- 转发记录 ----

    async def add_forward_record(self, tenant_id: int, chat_id: int, message_id: int,
                                   bot_id: str, msg_type: str, preview: str,
                                   status: str, error: str = None, time_ms: int = 0):
        await self.pool.execute(
            """INSERT INTO forward_records
               (tenant_id, telegram_chat_id, telegram_message_id, dingtalk_bot_id,
                message_type, content_preview, status, error_message, processing_time_ms)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)""",
            tenant_id, chat_id, message_id, bot_id, msg_type, preview,
            status, error, time_ms
        )

    async def get_forward_records(self, tenant_id: int, limit: int = 50,
                                    offset: int = 0, status: str = None) -> List[Dict]:
        if status:
            return await self.t_fetch(
                """SELECT * FROM forward_records
                   WHERE tenant_id = $1 AND status = $2
                   ORDER BY created_at DESC LIMIT $3 OFFSET $4""",
                status, limit, offset, tenant_id=tenant_id
            )
        return await self.t_fetch(
            """SELECT * FROM forward_records
               WHERE tenant_id = $1
               ORDER BY created_at DESC LIMIT $2 OFFSET $3""",
            limit, offset, tenant_id=tenant_id
        )

    # ---- 统计 ----

    async def get_dashboard_stats(self, tenant_id: int) -> Dict:
        stats = await self.t_fetchrow(
            """SELECT
                COALESCE(SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END), 0) as successful_forwards,
                COALESCE(SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END), 0) as failed_forwards,
                COUNT(*) as total_messages
               FROM forward_records WHERE tenant_id = $1 AND created_at > NOW() - INTERVAL '24 hours'""",
            tenant_id=tenant_id
        )
        bot_count = await self.t_fetchrow(
            "SELECT COUNT(*) as total, COALESCE(SUM(CASE WHEN enabled THEN 1 ELSE 0 END), 0) as active FROM dingtalk_bots WHERE tenant_id = $1",
            tenant_id=tenant_id
        )
        mapping_count = await self.t_fetchval(
            "SELECT COUNT(*) FROM mappings WHERE tenant_id = $1 AND enabled = TRUE",
            tenant_id=tenant_id
        )
        return {
            "total_messages": stats["total_messages"],
            "successful_forwards": stats["successful_forwards"],
            "failed_forwards": stats["failed_forwards"],
            "total_bots": bot_count["total"],
            "active_bots": bot_count["active"],
            "active_mappings": mapping_count or 0,
        }

    # ---- 审计日志 ----

    async def add_audit_log(self, tenant_id: int, user_id: int, action: str,
                             target: str = None, detail: str = None):
        await self.pool.execute(
            """INSERT INTO audit_logs (tenant_id, user_id, action, target, detail)
               VALUES ($1, $2, $3, $4, $5)""",
            tenant_id, user_id, action, target, detail
        )

    # ---- 过滤配置 ----

    async def get_filter_config(self, tenant_id: int) -> Optional[Dict]:
        row = await self.t_fetchrow(
            "SELECT config FROM filter_configs WHERE tenant_id = $1",
            tenant_id=tenant_id
        )
        return row["config"] if row else None

    async def save_filter_config(self, tenant_id: int, config: dict):
        import json
        await self.pool.execute(
            """INSERT INTO filter_configs (tenant_id, config, updated_at)
               VALUES ($1, $2::jsonb, NOW())
               ON CONFLICT (tenant_id) DO UPDATE SET config = $2::jsonb, updated_at = NOW()""",
            tenant_id, json.dumps(config)
        )

    # ---- 翻译配置 ----

    async def get_translation_config(self, tenant_id: int) -> Optional[Dict]:
        return await self.t_fetchrow(
            "SELECT * FROM translation_configs WHERE tenant_id = $1",
            tenant_id=tenant_id
        )

    async def save_translation_config(self, tenant_id: int, api_key: str,
                                       base_url: str = "https://api.deepseek.com/v1",
                                       model: str = "deepseek-chat",
                                       enabled: bool = True):
        await self.pool.execute(
            """INSERT INTO translation_configs (tenant_id, api_key, base_url, model, enabled, updated_at)
               VALUES ($1, $2, $3, $4, $5, NOW())
               ON CONFLICT (tenant_id) DO UPDATE SET api_key = $2, base_url = $3, model = $4, enabled = $5, updated_at = NOW()""",
            tenant_id, api_key, base_url, model, enabled
        )


# 全局单例
database = Database()
