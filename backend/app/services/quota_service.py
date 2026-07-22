"""
配额与用量管理服务
"""
import logging
from typing import Dict, Any

from app.core.config import settings
from app.core.database import database
from app.modules.tenants.repository import tenant_repository

logger = logging.getLogger(__name__)


class QuotaService:
    """配额管理"""

    async def check_message_quota(self, tenant_id: int) -> bool:
        """检查是否还有消息配额，返回 True 表示可用"""
        if tenant_id == 0:
            return True
        subscription = await tenant_repository.active_subscription(tenant_id)
        if not subscription:
            # 没有订阅记录，使用免费配额
            plan = "free"
            quota = settings.FREE_MESSAGE_QUOTA
        else:
            plan = subscription["plan"]
            quota = subscription["message_quota"]

        if plan in {"pro", "enterprise"}:
            return True

        usage = await tenant_repository.today_usage(tenant_id)
        return usage["messages_count"] < quota

    async def reserve_message(self, tenant_id: int) -> bool:
        """Atomically reserve and count one eligible source message."""
        if tenant_id == 0:
            return True
        async with database.transaction() as connection:
            subscription = await connection.fetchrow(
                """SELECT plan,message_quota FROM subscriptions
                   WHERE tenant_id=$1 AND status='active'
                   ORDER BY created_at DESC LIMIT 1 FOR UPDATE""", tenant_id
            )
            plan = subscription["plan"] if subscription else "free"
            quota = subscription["message_quota"] if subscription else settings.FREE_MESSAGE_QUOTA
            await connection.execute(
                """INSERT INTO usage_records(tenant_id,date,messages_count,translation_chars)
                   VALUES($1,CURRENT_DATE,0,0)
                   ON CONFLICT(tenant_id,date) DO NOTHING""", tenant_id
            )
            if plan in {"pro", "enterprise"}:
                await connection.execute(
                    """UPDATE usage_records SET messages_count=messages_count+1
                       WHERE tenant_id=$1 AND date=CURRENT_DATE""", tenant_id
                )
                return True
            row = await connection.fetchrow(
                """UPDATE usage_records SET messages_count=messages_count+1
                   WHERE tenant_id=$1 AND date=CURRENT_DATE AND messages_count < $2
                   RETURNING messages_count""", tenant_id, quota
            )
            return row is not None

    async def record_message(self, tenant_id: int, translation_chars: int = 0):
        """记录一条消息的用量"""
        await tenant_repository.increment_usage(tenant_id, messages=1, translation_chars=translation_chars)

    async def get_usage_summary(self, tenant_id: int) -> Dict[str, Any]:
        """获取用量摘要"""
        subscription = await tenant_repository.active_subscription(tenant_id)
        plan = subscription["plan"] if subscription else "free"
        quota = settings.PLAN_LIMITS.get(plan, {}).get("message_quota", 100)

        usage = await tenant_repository.today_usage(tenant_id)

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
        if tenant_id == 0:
            return True
        subscription = await tenant_repository.active_subscription(tenant_id)
        plan = subscription["plan"] if subscription else "free"

        if plan in {"pro", "enterprise"}:
            return True

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
