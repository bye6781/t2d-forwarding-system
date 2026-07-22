from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_platform_admin_keeps_complete_tenant_navigation():
    navigation = (ROOT / "frontend" / "src" / "router" / "navigation.ts").read_text(encoding="utf-8")

    for label in (
        "仪表盘",
        "Telegram 账号",
        "钉钉机器人",
        "转发映射",
        "转发控制",
        "平台管理",
        "过滤规则",
    ):
        assert label in navigation


def test_platform_admin_identity_drives_default_admin_page():
    auth_source = (ROOT / "backend" / "app" / "modules" / "auth" / "service.py").read_text(encoding="utf-8")
    login = (ROOT / "frontend" / "src" / "views" / "LoginView.vue").read_text(encoding="utf-8")

    assert auth_source.count('"is_platform_admin"') >= 2
    assert "auth.user?.is_platform_admin ? '/platform' : '/dashboard'" in login


def test_frontend_plan_values_match_backend_plan_enum():
    source = (ROOT / "frontend" / "src" / "views" / "OrganizationView.vue").read_text(encoding="utf-8")

    assert "'paid'" not in source
    assert "'pro'" in source
    assert "'enterprise'" in source
