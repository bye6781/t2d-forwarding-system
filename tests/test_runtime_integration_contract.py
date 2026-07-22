from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_bootstrap_credentials_come_from_environment():
    config = (ROOT / "backend" / "app" / "core" / "config.py").read_text(encoding="utf-8")
    main = (ROOT / "backend" / "main.py").read_text(encoding="utf-8")

    assert "PLATFORM_ADMIN_PASSWORD" in config
    assert "TEST_TENANT_PASSWORD" in config
    assert "admin123" not in main


def test_login_and_api_audit_are_connected_to_request_flow():
    auth = (ROOT / "backend" / "app" / "modules" / "auth" / "repository.py").read_text(encoding="utf-8")
    middleware = (ROOT / "backend" / "app" / "core" / "middleware.py").read_text(encoding="utf-8")
    main = (ROOT / "backend" / "main.py").read_text(encoding="utf-8")

    assert "INSERT INTO login_logs" in auth
    assert "class AuditLogMiddleware" in middleware
    assert "AuditLogMiddleware" in main


def test_advanced_policies_are_connected_to_forwarding_runtime():
    filters = (ROOT / "backend" / "app" / "services" / "filter_service.py").read_text(encoding="utf-8")
    forwarding = (ROOT / "backend" / "app" / "services" / "forwarding_service.py").read_text(encoding="utf-8")

    assert "evaluate_filter_rules" in filters
    assert "SELECT * FROM filter_rules" in filters
    assert "policy_repository.default_template_for_forwarding" in forwarding
    assert "render_message_template" in forwarding
    assert "policy_repository.media_for_forwarding" in forwarding
    assert "evaluate_media_policy" in forwarding
    assert '"sender": sender_name' in forwarding
    assert '"message_type": message_type' in forwarding


def test_advanced_router_mutations_are_tenant_scoped():
    for domain in ("policies", "audit"):
        source = (ROOT / "backend" / "app" / "modules" / domain / "router.py").read_text(encoding="utf-8")
        assert 'user["tenant_id"]' in source


def test_audit_api_exposes_frontend_compatible_fields():
    source = (ROOT / "backend" / "app" / "modules" / "audit" / "repository.py").read_text(encoding="utf-8")

    assert "AS action" in source
    assert "AS detail" in source
    assert "AS response_status" in source
    assert "u.username" in source


def test_jsonb_values_are_encoded_only_by_database_codec():
    database = (ROOT / "backend" / "app" / "core" / "database.py").read_text(encoding="utf-8")
    filters = (ROOT / "backend" / "app" / "modules" / "policies" / "repository.py").read_text(encoding="utf-8")
    media = filters

    assert "json.dumps(target_bot_ids)" not in database
    assert "json.dumps(config)" not in database
    assert "json.dumps(req.config)" not in filters
    assert "json.dumps(req.allowed_types)" not in media


def test_compose_requires_production_secrets_from_environment():
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")

    assert "t2d-saas-2026" not in compose
    assert "t2d-saas-jwt-secret-2026" not in compose
    assert "${DATABASE_URL:?" in compose
    assert "${JWT_SECRET:?" in compose
    assert "PLATFORM_ADMIN_PASSWORD" in compose
    assert "TEST_TENANT_PASSWORD" in compose
