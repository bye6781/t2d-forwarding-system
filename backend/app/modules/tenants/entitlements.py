from dataclasses import asdict, dataclass

from fastapi import HTTPException

from app.core.config import settings


@dataclass(frozen=True)
class Entitlements:
    is_unlimited: bool
    message_quota: int | None
    tg_account_limit: int | None
    mapping_limit: int | None
    bot_limit: int | None
    member_limit: int | None

    def as_dict(self) -> dict:
        return asdict(self)


VIEWER_FEATURES = {"dashboard", "telegram", "dingtalk", "routes"}
UNLIMITED_PLANS = {"pro", "enterprise"}


def resolve_entitlements(user: dict, plan: str) -> Entitlements:
    role = user.get("role", "member")
    if role == "viewer" and not user.get("is_platform_admin", False):
        plan_limits = settings.PLAN_LIMITS.get(plan, settings.PLAN_LIMITS["free"])
        return Entitlements(False, plan_limits["message_quota"], 1, 1, 1, 0)

    unlimited = bool(user.get("is_platform_admin")) or plan in UNLIMITED_PLANS
    if unlimited:
        return Entitlements(True, None, None, None, None, None)

    limits = settings.PLAN_LIMITS.get(plan, settings.PLAN_LIMITS["free"])
    return Entitlements(False, **limits)


def require_feature(user: dict, feature: str) -> None:
    if user.get("is_platform_admin") or user.get("role") != "viewer":
        return
    if feature not in VIEWER_FEATURES:
        raise HTTPException(403, "观察者无权访问此功能")


def require_authorization_admin(user: dict) -> None:
    if not user.get("is_platform_admin"):
        raise HTTPException(403, "只有平台管理员可以变更授权")
