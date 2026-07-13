"""
配额与用量管理服务
"""
import logging
from typing import Dict, Any

from app.core.database import database
from app.core.config import settings

logger = logging.getLogger(__name__)


class QuotaService:
    """配额管理"""

    async def check_message_quota(self, tenant_id: int) -> bool:
        """检查是否还有消息配额，返回 True 表示可用"""
        subscription = await database.get_subscription(tenant_id)
        if not subscription:
            # 没有订阅记录，使用免费配额
            plan = "free"
            quota = settings.FREE_MESSAGE_QUOTA
        else:
            plan = subscription["plan"]
            quota = subscription["message_quota"]

        if plan == "enterprise":
            return True  # 企业版无限制

        usage = await database.get_today_usage(tenant_id)
        return usage["messages_count"] < quota

    async def record_message(self, tenant_id: int, translation_chars: int = 0):
        """记录一条消息的用量"""
        await database.increment_usage(tenant_id, messages=1, translation_chars=translation_chars)

    async def get_usage_summary(self, tenant_id: int) -> Dict[str, Any]:
        """获取用量摘要"""
        subscription = await database.get_subscription(tenant_id)
        plan = subscription["plan"] if subscription else "free"
        quota = settings.PLAN_LIMITS.get(plan, {}).get("message_quota", 100)

        usage = await database.get_today_usage(tenant_id)

        return {
            "plan": plan,
            "daily_quota": quota,
            "today_messages": usage["messages_count"],
            "today_translation_chars": usage["translation_chars"],
            "remaining": max(0, quota - usage["messages_count"]),
            "usage_percent": round(usage["messages_count"] / quota * 100, 1) if quota > 0 else 0,
        }

    async def check_resource_limit(self, tenant_id: int, resource: str, current_count: int) -> bool:
        """检查资源是否达到上限（TG 账号数、映射数等）"""
        subscription = await database.get_subscription(tenant_id)
        plan = subscription["plan"] if subscription else "free"

        limits = settings.PLAN_LIMITS.get(plan, settings.PLAN_LIMITS["free"])
        limit_key_map = {
            "telegram_account": "tg_account_limit",
            "mapping": "mapping_limit",
            "bot": "bot_limit",
            "member": "member_limit",
        }
        limit_key = limit_key_map.get(resource)
        if not limit_key:
            return True

        return current_count < limits[limit_key]


quota_service = QuotaService()
