"""
租户配置服务
从数据库加载租户配置，替代原来的 JSON 文件方式
"""
import logging
from typing import Optional, Dict, Any

from app.core.database import database

logger = logging.getLogger(__name__)


class TenantConfigService:
    """租户配置管理"""

    async def get_tenant_config(self, tenant_id: int) -> Dict[str, Any]:
        """获取租户完整配置（从 DB 聚合）"""
        tenant = await database.get_tenant(tenant_id)
        if not tenant:
            raise ValueError(f"Tenant {tenant_id} not found")

        subscription = await database.get_subscription(tenant_id)
        tg_accounts = await database.get_tg_accounts(tenant_id)
        dingtalk_bots = await database.get_dingtalk_bots(tenant_id)
        mappings = await database.get_mappings(tenant_id)
        filter_config = await database.get_filter_config(tenant_id)
        translation_config = await database.get_translation_config(tenant_id)

        return {
            "tenant": tenant,
            "subscription": subscription,
            "telegram_accounts": tg_accounts,
            "dingtalk_bots": dingtalk_bots,
            "mappings": mappings,
            "filter_config": filter_config or {},
            "translation_config": translation_config,
        }

    async def get_active_tenant_ids(self) -> list:
        """获取所有活跃租户 ID"""
        rows = await database.fetch(
            "SELECT id FROM tenants WHERE status = 'active'"
        )
        return [r["id"] for r in rows]

    async def tenant_has_telegram(self, tenant_id: int) -> bool:
        """检查租户是否已配置并授权 Telegram 账号"""
        accounts = await database.get_tg_accounts(tenant_id)
        return any(a["is_authorized"] and a["status"] == "connected" for a in accounts)

    async def tenant_has_dingtalk(self, tenant_id: int) -> bool:
        """检查租户是否已配置钉钉 Bot"""
        bots = await database.get_dingtalk_bots(tenant_id)
        return any(b["enabled"] for b in bots)


tenant_config_service = TenantConfigService()
