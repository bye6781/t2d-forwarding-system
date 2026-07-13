"""
配额管理服务
"""
import logging
from datetime import date

from app.core.database import database
from app.core.config import settings

logger = logging.getLogger(__name__)


class QuotaService:
    """配额管理服务"""

    async def check_message_quota(self, tenant_id: int) -> bool:
        """检查消息配额是否足够（付费版不限制）"""
        tenant = await database.get_tenant(tenant_id)
        plan = tenant.get("plan", "free") if tenant else "free"

        # 付费版不做任何限制
        if plan == "paid":
            return True

        # 免费版检查配额
        limits = settings.PLAN_LIMITS.get(plan, settings.PLAN_LIMITS["free"])
        quota = limits.get("message_quota", 100)

        today = date.today()
        usage = await database.pool.fetchval(
            "SELECT messages_count FROM usage_records WHERE tenant_id = $1 AND date = $2",
            tenant_id, today
        )
        usage = usage or 0
        return usage < quota

    async def increment_usage(self, tenant_id: int, count: int = 1):
        """增加用量记录"""
        today = date.today()
        await database.pool.execute(
            """INSERT INTO usage_records (tenant_id, date, messages_count)
               VALUES ($1, $2, $3)
               ON CONFLICT (tenant_id, date)
               DO UPDATE SET messages_count = usage_records.messages_count + $3, updated_at = NOW()""",
            tenant_id, today, count
        )

    async def check_resource_limit(self, tenant_id: int, resource_type: str, current_count: int) -> bool:
        """检查资源是否超限（付费版不限制）"""
        tenant = await database.get_tenant(tenant_id)
        plan = tenant.get("plan", "free") if tenant else "free"

        # 付费版不做任何限制
        if plan == "paid":
            return True

        limits = settings.PLAN_LIMITS.get(plan, settings.PLAN_LIMITS["free"])
        limit_key = {
            "tg_account": "tg_account_limit",
            "mapping": "mapping_limit",
            "bot": "bot_limit",
            "member": "member_limit",
        }.get(resource_type)

        if not limit_key:
            return True

        limit = limits.get(limit_key, 0)
        return current_count < limit

    async def get_usage_summary(self, tenant_id: int) -> dict:
        """获取用量摘要"""
        tenant = await database.get_tenant(tenant_id)
        plan = tenant.get("plan", "free") if tenant else "free"
        limits = settings.PLAN_LIMITS.get(plan, settings.PLAN_LIMITS["free"])

        today = date.today()
        today_messages = await database.pool.fetchval(
            "SELECT messages_count FROM usage_records WHERE tenant_id = $1 AND date = $2",
            tenant_id, today
        ) or 0

        quota = limits.get("message_quota", 100)
        usage_percent = (today_messages / quota * 100) if quota > 0 and quota < 999999 else 0

        return {
            "plan": plan,
            "daily_quota": quota,
            "today_messages": today_messages,
            "remaining": max(0, quota - today_messages) if quota < 999999 else 999999,
            "usage_percent": round(min(usage_percent, 100), 1),
        }


quota_service = QuotaService()
