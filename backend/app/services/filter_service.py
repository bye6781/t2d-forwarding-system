"""
过滤引擎 - 多租户版
每个租户独立配置过滤规则
"""
import logging

from app.core.database import database
from app.core.tenant_context import TenantContext
from app.modules.policies.filters import evaluate_filter_rules

logger = logging.getLogger(__name__)


class FilterService:
    """消息过滤服务（多租户版）"""

    def invalidate_cache(self, tenant_id: int = None):
        return None

    async def should_filter(self, message: dict) -> tuple:
        """
        检查消息是否应被过滤
        返回 (是否过滤, 原因)
        """
        tenant_id = TenantContext.get()
        rules = await database.fetch(
            "SELECT * FROM filter_rules WHERE tenant_id = $1 ORDER BY priority, id",
            tenant_id,
        )
        matched, reason = evaluate_filter_rules(rules, message)
        if matched:
            return True, reason

        return False, ""


filter_service = FilterService()
