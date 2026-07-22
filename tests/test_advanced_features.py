from pathlib import Path

from app.modules.policies.filters import evaluate_filter_rules
from app.modules.policies.media import evaluate_media_policy
from app.modules.policies.templates import render_message_template


ROOT = Path(__file__).resolve().parents[1]


def test_filter_rules_are_priority_ordered_and_tenant_message_fields_are_supported():
    rules = [
        {
            "id": 2,
            "name": "blocked sender",
            "rule_type": "sender",
            "config": {"senders": ["spam-user"]},
            "priority": 20,
            "enabled": True,
        },
        {
            "id": 1,
            "name": "forbidden keyword",
            "rule_type": "keyword_exclude",
            "config": {"keywords": ["广告"]},
            "priority": 10,
            "enabled": True,
        },
    ]

    matched, reason = evaluate_filter_rules(
        rules,
        {"text": "这是一条广告", "sender": "spam-user", "message_type": "text"},
    )

    assert matched is True
    assert reason == "forbidden keyword"


def test_required_keyword_rule_filters_messages_without_any_required_keyword():
    rules = [{
        "id": 1,
        "name": "required topic",
        "rule_type": "keyword_include",
        "config": {"keywords": ["项目", "通知"]},
        "priority": 1,
        "enabled": True,
    }]

    assert evaluate_filter_rules(rules, {"text": "闲聊"}) == (True, "required topic")
    assert evaluate_filter_rules(rules, {"text": "项目更新"}) == (False, "")


def test_invalid_regex_does_not_crash_message_processing():
    rules = [{
        "id": 1,
        "name": "broken regex",
        "rule_type": "regex",
        "config": {"pattern": "["},
        "priority": 1,
        "enabled": True,
    }]

    assert evaluate_filter_rules(rules, {"text": "hello"}) == (False, "")


def test_message_template_renders_supported_variables_and_preserves_unknown_ones():
    rendered = render_message_template(
        "[{time}] {source} / {sender}: {content} ({unknown})",
        {
            "time": "2026-07-15 16:00",
            "source": "TG Group",
            "sender": "Alice",
            "content": "hello",
        },
    )

    assert rendered == "[2026-07-15 16:00] TG Group / Alice: hello ({unknown})"


def test_media_policy_enforces_allowed_types_and_maximum_size():
    config = {"allowed_types": ["photo", "video"], "max_file_size_bytes": 1024}

    assert evaluate_media_policy(config, "photo", 512) == (True, "")
    assert evaluate_media_policy(config, "document", 512) == (
        False,
        "媒体类型 document 未启用",
    )
    assert evaluate_media_policy(config, "video", 2048) == (
        False,
        "媒体文件超过大小限制",
    )


def test_schema_and_main_register_all_frontend_modules():
    schema = (ROOT / "backend" / "alembic" / "full_schema.sql").read_text(encoding="utf-8")
    main = (ROOT / "backend" / "main.py").read_text(encoding="utf-8")

    for table in ("login_logs", "api_logs", "filter_rules", "message_templates", "media_configs"):
        assert f"CREATE TABLE IF NOT EXISTS {table}" in schema
    assert 'app.include_router(policies.router, prefix="/api/v2/policies")' in main
    assert 'app.include_router(audit.router, prefix="/api/v2/audit")' in main
