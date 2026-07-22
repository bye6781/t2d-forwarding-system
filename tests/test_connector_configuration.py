import asyncio
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException


def test_dingtalk_configuration_does_not_require_internal_bot_id(monkeypatch):
    from app.core.database import database
    from app.modules.connectors.repository import connector_repository
    from app.modules.connectors.schemas import BotCreate

    payload = BotCreate(
        name="告警群",
        webhook="https://oapi.dingtalk.com/robot/send?access_token=test",
        secret="SEC-test",
    )
    fetchrow = AsyncMock(return_value={"id": 1})
    monkeypatch.setattr(database, "fetchrow", fetchrow)

    async def scenario():
        await connector_repository.create_bot(7, payload)
        args = fetchrow.await_args.args
        assert args[1] == 7
        assert args[2].startswith("dingtalk-")
        assert args[3] == "告警群"
        assert not hasattr(payload, "bot_id")

    asyncio.run(scenario())


def test_telegram_send_code_keeps_persistent_client(monkeypatch):
    from app.services.telegram_service import telegram_service

    connect_account = AsyncMock(return_value="pending_code")
    monkeypatch.setattr(telegram_service, "connect_account", connect_account)

    async def scenario():
        result = await telegram_service.send_code(7, 8, 12345, "api-hash", "+8613800000000")
        assert result == {"success": True, "message": "验证码已发送"}
        connect_account.assert_awaited_once_with(
            tenant_id=7,
            account_db_id=8,
            api_id=12345,
            api_hash="api-hash",
            phone="+8613800000000",
        )

    asyncio.run(scenario())


def test_telegram_verify_code_reuses_pending_client(monkeypatch):
    from app.services.telegram_service import telegram_service

    class PendingAccount:
        _client = object()
        connected = False

        _client = type("Client", (), {"is_connected": lambda self: True})()

        async def verify_code(self, code, password):
            assert code == "12345"
            assert password == "secret"
            return True

    telegram_service._accounts = {"7_8": PendingAccount()}
    connect_account = AsyncMock()
    monkeypatch.setattr(telegram_service, "connect_account", connect_account)

    async def scenario():
        result = await telegram_service.verify_code(7, 8, 12345, "api-hash", "+8613800000000", "12345", "secret")
        assert result == {"success": True, "message": "登录成功"}
        connect_account.assert_not_awaited()

    try:
        asyncio.run(scenario())
    finally:
        telegram_service._accounts.clear()


def test_telegram_send_code_failure_is_returned_as_http_error(monkeypatch):
    from app.modules.connectors.repository import connector_repository
    from app.modules.connectors.service import connector_service
    from app.services.telegram_service import telegram_service

    monkeypatch.setattr(
        connector_repository,
        "telegram_account",
        AsyncMock(return_value={"id": 8, "api_id": 12345, "api_hash": "api-hash", "phone": "+8613800000000"}),
    )
    monkeypatch.setattr(
        telegram_service,
        "send_code",
        AsyncMock(return_value={"success": False, "error": "Telegram temporarily disconnected"}),
    )

    async def scenario():
        with pytest.raises(HTTPException) as raised:
            await connector_service.telegram_action(
                {"tenant_id": 0, "role": "owner", "is_platform_admin": True},
                8,
                "send-code",
                None,
            )
        assert raised.value.status_code == 502
        assert raised.value.detail == "Telegram temporarily disconnected"

    asyncio.run(scenario())


def test_startup_accounts_include_platform_tenant(monkeypatch):
    from app.core.database import database
    from app.modules.connectors.repository import connector_repository

    fetch = AsyncMock(return_value=[])
    monkeypatch.setattr(database, "fetch", fetch)

    async def scenario():
        await connector_repository.authorized_accounts_for_startup()
        query = fetch.await_args.args[0]
        assert "a.is_authorized" in query
        assert "t.status='active'" in query
        assert "t.id>0" not in query

    asyncio.run(scenario())


def test_startup_reconnect_never_requests_a_login_code(monkeypatch):
    import main
    from app.modules.connectors.repository import connector_repository
    from app.services.telegram_service import telegram_service

    monkeypatch.setattr(
        connector_repository,
        "authorized_accounts_for_startup",
        AsyncMock(return_value=[{
            "tenant_id": 0,
            "id": 6,
            "api_id": 12345,
            "api_hash": "api-hash",
            "phone": "+8613800000000",
        }]),
    )
    connect = AsyncMock(return_value=True)
    monkeypatch.setattr(telegram_service, "connect_account", connect)
    monkeypatch.setattr(main.tenant_runtime, "start", AsyncMock())

    async def scenario():
        await main.connect_authorized_accounts()
        connect.assert_awaited_once_with(
            tenant_id=0,
            account_db_id=6,
            api_id=12345,
            api_hash="api-hash",
            phone="+8613800000000",
            request_code=False,
        )

    asyncio.run(scenario())


def test_photo_forward_keeps_image_before_original_markdown_text(monkeypatch):
    from app.modules.connectors.repository import connector_repository
    from app.modules.forwarding.repository import forwarding_repository
    from app.modules.policies.repository import policy_repository
    from app.services.dingtalk_service import dingtalk_service
    from app.services.forwarding_service import ForwardingService
    from app.services.translation_service import translation_service

    send_markdown = AsyncMock(return_value={"errcode": 0})
    monkeypatch.setattr(connector_repository, "bots", AsyncMock(return_value=[{
        "id": 9,
        "bot_id": "dingtalk-9",
        "webhook": "https://example.test/webhook",
        "secret": "",
        "enabled": True,
    }]))
    monkeypatch.setattr(policy_repository, "default_template_for_forwarding", AsyncMock(return_value=None))
    monkeypatch.setattr(translation_service, "translate", AsyncMock(side_effect=lambda text, target_lang: text))
    monkeypatch.setattr(dingtalk_service, "send_markdown", send_markdown)
    monkeypatch.setattr(forwarding_repository, "add_record", AsyncMock())

    async def scenario():
        await ForwardingService()._forward_to_dingtalk(
            tenant_id=0,
            mapping={"target_bot_ids": [9], "translation_enabled": True},
            message_text="标题\n正文",
            message_md="**标题**\n正文",
            media_info={"type": "photo", "url": "https://cdn.test/photo.jpg", "forward_as_link": False},
            sender_name="sender",
            message_id=1,
        )
        text = send_markdown.await_args.kwargs["text"]
        assert text == "![图片](https://cdn.test/photo.jpg)\n\n**标题**\n正文"

    asyncio.run(scenario())


def test_dingtalk_test_uses_send_text_content_parameter(monkeypatch):
    from app.modules.connectors.repository import connector_repository
    from app.modules.connectors.service import connector_service
    from app.services.dingtalk_service import dingtalk_service

    monkeypatch.setattr(
        connector_repository,
        "bot",
        AsyncMock(return_value={
            "webhook": "https://oapi.dingtalk.com/robot/send?access_token=test",
            "secret": "SEC-test",
            "bot_id": "dingtalk-test",
        }),
    )
    send_text = AsyncMock(return_value={"errcode": 0, "errmsg": "ok"})
    monkeypatch.setattr(dingtalk_service, "send_text", send_text)

    async def scenario():
        result = await connector_service.test_bot(
            {"tenant_id": 0, "role": "owner", "is_platform_admin": True},
            8,
            "T2D Cloud test message",
        )
        assert result["errcode"] == 0
        send_text.assert_awaited_once_with(
            webhook="https://oapi.dingtalk.com/robot/send?access_token=test",
            content="T2D Cloud test message",
            secret="SEC-test",
            bot_id="dingtalk-test",
        )

    asyncio.run(scenario())


def test_connector_pages_are_separate_and_use_configuration_names():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1] / "frontend" / "src"
    navigation = (root / "router" / "navigation.ts").read_text(encoding="utf-8")
    router = (root / "router" / "index.ts").read_text(encoding="utf-8")
    telegram = (root / "features" / "connectors" / "TelegramConfigView.vue").read_text(encoding="utf-8")
    dingtalk = (root / "features" / "connectors" / "DingTalkConfigView.vue").read_text(encoding="utf-8")
    connector_api = (root / "features" / "connectors" / "api.ts").read_text(encoding="utf-8")

    assert "Telegram 账号" in navigation
    assert "钉钉机器人" in navigation
    assert "path: '/telegram'" in navigation
    assert "path: '/dingtalk'" in navigation
    assert "redirect: '/telegram'" in router
    assert "redirect: '/dingtalk'" in router
    assert "connectors/telegram" in router
    assert "connectors/dingtalk" in router
    assert "el-tabs" not in telegram
    assert "el-tabs" not in dingtalk
    assert "Bot ID" not in dingtalk
    assert "TelegramConfig" in connector_api
    assert "DingTalkConfig" in connector_api
