import pytest
from fastapi import HTTPException


def test_only_platform_admin_and_pro_plan_are_unlimited():
    from app.modules.tenants.entitlements import resolve_entitlements

    for user, plan in [
        ({"role": "member", "is_platform_admin": True}, "free"),
        ({"role": "member", "is_platform_admin": False}, "pro"),
    ]:
        entitlement = resolve_entitlements(user, plan)
        assert entitlement.is_unlimited is True
        assert entitlement.message_quota is None
        assert entitlement.bot_limit is None
        assert entitlement.mapping_limit is None


def test_viewer_cap_takes_precedence_over_pro_plan():
    from app.modules.tenants.entitlements import resolve_entitlements

    entitlement = resolve_entitlements(
        {"role": "viewer", "is_platform_admin": False}, "pro"
    )
    assert entitlement.is_unlimited is False
    assert entitlement.bot_limit == 1
    assert entitlement.mapping_limit == 1
    assert entitlement.tg_account_limit == 1
    assert entitlement.member_limit == 0


def test_free_owner_keeps_plan_limits():
    from app.core.config import settings
    from app.modules.tenants.entitlements import resolve_entitlements

    entitlement = resolve_entitlements(
        {"role": "owner", "is_platform_admin": False}, "free"
    )
    assert entitlement.is_unlimited is False
    assert entitlement.message_quota == settings.PLAN_LIMITS["free"]["message_quota"]
    assert entitlement.bot_limit == settings.PLAN_LIMITS["free"]["bot_limit"]


def test_viewer_only_has_test_connectors_and_routes():
    from app.modules.tenants.entitlements import require_feature

    user = {"role": "viewer", "is_platform_admin": False}
    for feature in ("dashboard", "telegram", "dingtalk", "routes"):
        require_feature(user, feature)
    for feature in ("runtime", "policies", "audit", "organization"):
        with pytest.raises(HTTPException) as exc:
            require_feature(user, feature)
        assert exc.value.status_code == 403


def test_only_platform_admin_can_change_authorizations():
    from app.modules.tenants.entitlements import require_authorization_admin

    require_authorization_admin({"role": "owner", "is_platform_admin": True})
    for role in ("owner", "admin", "member", "viewer"):
        with pytest.raises(HTTPException) as exc:
            require_authorization_admin({"role": role, "is_platform_admin": False})
        assert exc.value.status_code == 403
