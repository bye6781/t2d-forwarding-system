"""
租户上下文管理
基于 contextvars 实现请求级别的租户隔离
"""
from contextvars import ContextVar
from typing import Optional

_tenant_id: ContextVar[Optional[int]] = ContextVar("tenant_id", default=None)
_tenant_plan: ContextVar[Optional[str]] = ContextVar("tenant_plan", default=None)


class TenantContext:
    """请求级别的租户上下文"""

    @staticmethod
    def set(tenant_id: int, plan: str = "free"):
        _tenant_id.set(tenant_id)
        _tenant_plan.set(plan)

    @staticmethod
    def get() -> Optional[int]:
        return _tenant_id.get()

    @staticmethod
    def get_plan() -> str:
        return _tenant_plan.get() or "free"

    @staticmethod
    def clear():
        _tenant_id.set(None)
        _tenant_plan.set("free")

    @staticmethod
    def require() -> int:
        """获取租户 ID，如果未设置则抛出异常"""
        tid = _tenant_id.get()
        if tid is None:
            raise ValueError("Tenant context not set. Request must be authenticated.")
        return tid
