import asyncio
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_v2_response_helpers_have_one_envelope():
    from app.shared.responses import page, success

    assert success({"id": 7}) == {"data": {"id": 7}}
    assert page([{"id": 7}], total=1, limit=20, offset=0) == {
        "data": {"items": [{"id": 7}], "total": 1, "limit": 20, "offset": 0}
    }


def test_forwarding_runtime_state_is_tenant_scoped():
    from app.modules.forwarding.runtime import InMemoryRuntimeStore, TenantRuntimeState

    async def scenario():
        runtime = TenantRuntimeState(InMemoryRuntimeStore())
        await runtime.start(11)
        assert await runtime.is_running(11) is True
        assert await runtime.is_running(12) is False
        await runtime.stop(12)
        assert await runtime.is_running(11) is True
        await runtime.stop(11)
        assert await runtime.is_running(11) is False

    asyncio.run(scenario())


def test_message_policies_live_in_their_domain_services():
    from app.modules.policies.filters import evaluate_filter_rules
    from app.modules.policies.media import evaluate_media_policy
    from app.modules.policies.templates import render_message_template

    rules = [{
        "name": "广告过滤",
        "rule_type": "keyword_exclude",
        "config": {"keywords": ["广告"]},
        "priority": 10,
        "enabled": True,
    }]
    assert evaluate_filter_rules(rules, {"text": "这是一条广告"}) == (True, "广告过滤")
    assert render_message_template("{sender}: {content}", {"sender": "Alice", "content": "Hi"}) == "Alice: Hi"
    assert evaluate_media_policy(
        {"allowed_types": ["photo"], "max_file_size_bytes": 100}, "video", 20
    )[0] is False


def test_migrated_legacy_filter_config_keeps_filtering_behavior():
    from app.modules.policies.filters import evaluate_filter_rules

    legacy = [{
        "name": "旧版过滤配置",
        "rule_type": "legacy_config",
        "config": {
            "enabled": True,
            "blocklist": {"keywords": ["推广"], "users": ["91"], "chats": ["-1008"]},
            "content_filter": {"enabled": True, "min_length": 3, "max_length": 20},
        },
        "enabled": True,
    }]
    assert evaluate_filter_rules(legacy, {"text": "推广内容"})[0] is True
    assert evaluate_filter_rules(legacy, {"text": "正常消息", "user_id": 91})[0] is True
    assert evaluate_filter_rules(legacy, {"text": "正常消息", "chat_id": -1008})[0] is True


def test_migrated_legacy_filter_config_remains_editable():
    source = (ROOT / "backend" / "app" / "modules" / "policies" / "schemas.py").read_text(encoding="utf-8")
    assert "legacy_config" in source


def test_v2_routes_replace_legacy_api_contract():
    source = (ROOT / "backend" / "main.py").read_text(encoding="utf-8")

    for prefix in (
        "/api/v2/auth",
        "/api/v2/tenant",
        "/api/v2/platform",
        "/api/v2/connectors",
        "/api/v2/forwarding",
        "/api/v2/policies",
        "/api/v2/audit",
    ):
        assert prefix in source
    assert "app.include_router(auth.router)" not in source
    assert 'path.startswith("api/")' in source
    assert 'status_code=200 if status == "healthy" else 503' in source


def test_sessions_are_not_inside_public_static_directory():
    config = (ROOT / "backend" / "app" / "core" / "config.py").read_text(encoding="utf-8")
    main = (ROOT / "backend" / "main.py").read_text(encoding="utf-8")

    assert "PRIVATE_DATA_DIR" in config
    assert "PUBLIC_MEDIA_DIR" in config
    assert 'StaticFiles(directory=settings.PUBLIC_MEDIA_DIR)' in main
    assert 'StaticFiles(directory="/app/data")' not in main
    telegram = (ROOT / "backend" / "app" / "services" / "telegram_service.py").read_text(encoding="utf-8")
    assert "/app/data/sessions" not in telegram


def test_alembic_migration_normalizes_targets_and_removes_legacy_filters():
    migration_dir = ROOT / "backend" / "alembic" / "versions"
    migrations = list(migration_dir.glob("*.py")) if migration_dir.exists() else []
    source = "\n".join(path.read_text(encoding="utf-8") for path in migrations)

    assert "mapping_targets" in source
    assert "postgresql.JSONB" in source
    assert "jsonb_agg" in source
    assert "filter_configs" in source
    assert "drop_table" in source


def test_frontend_is_a_vite_typescript_application():
    package = (ROOT / "frontend" / "package.json").read_text(encoding="utf-8")
    source_dir = ROOT / "frontend" / "src"

    assert '"vite"' in package
    assert '"typescript"' in package
    assert (source_dir / "main.ts").exists()
    assert (source_dir / "router" / "index.ts").exists()
    assert (source_dir / "stores" / "auth.ts").exists()


def test_connector_and_route_schemas_use_database_ids():
    from app.modules.connectors.schemas import BotUpdate
    from app.modules.forwarding.schemas import RouteCreate

    route = RouteCreate(source_chat_id=-100123, target_bot_ids=[3, 8])
    assert route.target_bot_ids == [3, 8]
    assert BotUpdate(name="ops").name == "ops"


def test_v2_routers_do_not_execute_sql_directly():
    module_root = ROOT / "backend" / "app" / "modules"
    for router in module_root.glob("*/router.py"):
        source = router.read_text(encoding="utf-8")
        assert "database.execute" not in source
        assert "database.fetch" not in source
        assert "database.pool" not in source


def test_docker_builds_frontend_and_keeps_private_sessions_private():
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")

    assert "FROM node:" in dockerfile
    assert "npm run build" in dockerfile
    assert "COPY --from=web-build" in dockerfile
    assert "PRIVATE_DATA_DIR=/app/private" in compose
    assert "PUBLIC_MEDIA_DIR=/app/public-media" in compose
    assert "./frontend:/app/static" not in compose


def test_legacy_root_patch_files_are_removed():
    for name in (
        "config.py", "system.py", "tenants.py", "quota_service.py",
        "update_subscription.py", "patch_frontend.py",
    ):
        assert not (ROOT / name).exists()


def test_database_core_is_connection_management_only():
    source = (ROOT / "backend" / "app" / "core" / "database.py").read_text(encoding="utf-8")

    for old_domain_method in (
        "get_tg_accounts", "get_dingtalk_bots", "get_mappings",
        "get_filter_config", "get_translation_config", "get_dashboard_stats",
    ):
        assert f"def {old_domain_method}" not in source
