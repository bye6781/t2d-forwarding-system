"""
Telegram 服务 - 多租户版
每个租户独立管理自己的 Telegram 账号池
账号按 tenant_id 隔离，会话文件按租户存储
"""
import asyncio
import logging
from typing import Optional, Callable, Any, List, Dict

logger = logging.getLogger(__name__)


class TelegramAccount:
    """单个 Telegram 账号（绑定到特定租户）"""

    def __init__(self, account_id: int, tenant_id: int, api_id: int,
                 api_hash: str, phone: str, name: str = "default"):
        self.account_id = account_id
        self.tenant_id = tenant_id
        self.api_id = api_id
        self.api_hash = api_hash
        self.phone = phone
        self.name = name
        self._client = None
        self._connected = False
        self._handlers = []
        self._event_handler_registered = False

    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def session_path(self) -> str:
        return f"/app/data/sessions/{self.tenant_id}/{self.account_id}"

    async def connect(self):
        """连接到 Telegram"""
        try:
            import os
            from telethon import TelegramClient
            from telethon.errors import SessionPasswordNeededError
            from telethon.events import NewMessage

            os.makedirs(os.path.dirname(self.session_path), exist_ok=True)
            self._client = TelegramClient(self.session_path, self.api_id, self.api_hash)
            await self._client.connect()

            if await self._client.is_user_authorized():
                me = await self._client.get_me()
                logger.info(f"[T{self.tenant_id}:A{self.account_id}] Connected: {me.first_name}")
                self._connected = True
                if not self._event_handler_registered:
                    self._client.add_event_handler(self._on_message, NewMessage())
                    self._event_handler_registered = True
                return True
            else:
                logger.info(f"[T{self.tenant_id}:A{self.account_id}] Sending code to {self.phone}...")
                await self._client.send_code_request(self.phone)
                self._connected = False
                return "pending_code"

        except SessionPasswordNeededError:
            logger.error(f"[T{self.tenant_id}:A{self.account_id}] 2FA required")
            self._connected = False
            return "need_2fa"
        except Exception as e:
            logger.error(f"[T{self.tenant_id}:A{self.account_id}] Connection failed: {e}")
            self._connected = False
            return False

    async def verify_code(self, code: str, password: str = None) -> Any:
        if not self._client:
            return False
        try:
            from telethon.events import NewMessage
            from telethon.errors import SessionPasswordNeededError

            await self._client.sign_in(self.phone, code)
            self._connected = True
            me = await self._client.get_me()
            logger.info(f"[T{self.tenant_id}:A{self.account_id}] Login OK: {me.first_name}")
            if not self._event_handler_registered:
                self._client.add_event_handler(self._on_message, NewMessage())
                self._event_handler_registered = True
            return True
        except SessionPasswordNeededError:
            if password:
                try:
                    from telethon.events import NewMessage
                    await self._client.sign_in(password=password)
                    self._connected = True
                    me = await self._client.get_me()
                    logger.info(f"[T{self.tenant_id}:A{self.account_id}] 2FA login OK")
                    if not self._event_handler_registered:
                        self._client.add_event_handler(self._on_message, NewMessage())
                        self._event_handler_registered = True
                    return True
                except Exception as e2:
                    logger.error(f"[T{self.tenant_id}:A{self.account_id}] 2FA failed: {e2}")
                    return False
            return "need_password"
        except Exception as e:
            logger.error(f"[T{self.tenant_id}:A{self.account_id}] Verify failed: {e}")
            self._connected = False
            return False

    async def disconnect(self):
        if self._client:
            await self._client.disconnect()
            self._connected = False
            logger.info(f"[T{self.tenant_id}:A{self.account_id}] Disconnected")

    def add_handler(self, handler: Callable):
        if handler not in self._handlers:
            self._handlers.append(handler)

    async def _on_message(self, event):
        for handler in self._handlers:
            try:
                await handler(event, account_id=self.account_id, tenant_id=self.tenant_id)
            except Exception as e:
                logger.error(f"[T{self.tenant_id}:A{self.account_id}] Handler error: {e}", exc_info=True)

    async def get_dialogs(self) -> list:
        if not self._client or not self._connected:
            return []
        try:
            dialogs = await self._client.get_dialogs()
            return [
                {"id": d.id, "title": d.title or d.name,
                 "is_channel": d.is_channel, "is_group": d.is_group}
                for d in dialogs
            ]
        except Exception as e:
            logger.error(f"[T{self.tenant_id}:A{self.account_id}] Get dialogs failed: {e}")
            return []


class TelegramService:
    """Telegram 多租户账号管理服务"""

    def __init__(self):
        self._accounts: Dict[str, TelegramAccount] = {}  # key: "{tenant_id}_{account_id}"
        self._global_handlers: List[Callable] = []

    def _key(self, tenant_id: int, account_id: int) -> str:
        return f"{tenant_id}_{account_id}"

    @property
    def connected_count(self) -> int:
        return sum(1 for a in self._accounts.values() if a.connected)

    @property
    def accounts(self) -> Dict[str, TelegramAccount]:
        return self._accounts

    def get_account(self, tenant_id: int, account_db_id: int) -> Optional[TelegramAccount]:
        return self._accounts.get(self._key(tenant_id, account_db_id))

    def get_tenant_accounts(self, tenant_id: int) -> List[TelegramAccount]:
        return [a for a in self._accounts.values() if a.tenant_id == tenant_id]

    def is_connected(self, tenant_id: int, account_db_id: int) -> bool:
        """检查账号是否已连接"""
        account = self.get_account(tenant_id, account_db_id)
        return account is not None and account.connected

    async def connect_account(self, tenant_id: int, account_db_id: int,
                              api_id: int, api_hash: str, phone: str,
                              name: str = "default") -> Any:
        """连接单个账号"""
        account = TelegramAccount(account_db_id, tenant_id, api_id, api_hash, phone, name)
        for handler in self._global_handlers:
            account.add_handler(handler)
        key = self._key(tenant_id, account_db_id)
        # 断开旧连接
        old = self._accounts.get(key)
        if old and old.connected:
            await old.disconnect()
        self._accounts[key] = account
        result = await account.connect()
        logger.info(f"Account T{tenant_id}:A{account_db_id} connect result: {result}")
        return result

    async def send_code(self, tenant_id: int, account_db_id: int,
                        api_id: int, api_hash: str, phone: str) -> Dict:
        """发送验证码（不连接，仅发送 code）"""
        import os
        from telethon import TelegramClient

        session_path = f"/app/data/sessions/{tenant_id}/{account_db_id}"
        os.makedirs(os.path.dirname(session_path), exist_ok=True)

        client = TelegramClient(session_path, api_id, api_hash)
        try:
            await client.connect()
            await client.send_code_request(phone)
            await client.disconnect()
            return {"success": True, "message": "验证码已发送"}
        except Exception as e:
            try:
                await client.disconnect()
            except Exception:
                pass
            logger.error(f"Send code failed: {e}")
            return {"success": False, "error": str(e)}

    async def verify_code(self, tenant_id: int, account_db_id: int,
                          api_id: int, api_hash: str, phone: str,
                          code: str, password: str = None) -> Dict:
        """验证验证码并建立持久连接"""
        result = await self.connect_account(tenant_id, account_db_id, api_id, api_hash, phone)

        if result is True:
            return {"success": True, "message": "已连接"}

        if result == "pending_code" or result == "need_2fa":
            # 账号已创建但需要验证码
            account = self.get_account(tenant_id, account_db_id)
            if account:
                verify_result = await account.verify_code(code, password)
                if verify_result is True:
                    return {"success": True, "message": "登录成功"}
                elif verify_result == "need_password":
                    return {"success": False, "error": "需要两步验证码"}
                else:
                    return {"success": False, "error": "验证码错误"}
            return {"success": False, "error": "账号未找到"}

        return {"success": False, "error": str(result)}

    async def disconnect_account(self, tenant_id: int, account_db_id: int):
        """断开单个账号"""
        key = self._key(tenant_id, account_db_id)
        account = self._accounts.pop(key, None)
        if account:
            await account.disconnect()
            logger.info(f"Disconnected T{tenant_id}:A{account_db_id}")

    async def disconnect_tenant(self, tenant_id: int):
        """断开某租户所有账号"""
        for key, account in list(self._accounts.items()):
            if account.tenant_id == tenant_id:
                await account.disconnect()
                del self._accounts[key]

    async def disconnect_all(self):
        for account in self._accounts.values():
            await account.disconnect()
        self._accounts.clear()

    def add_handler(self, handler: Callable):
        """给所有账号添加消息处理回调"""
        if handler not in self._global_handlers:
            self._global_handlers.append(handler)
        for account in self._accounts.values():
            account.add_handler(handler)

    async def get_dialogs(self, tenant_id: int, account_db_id: int) -> list:
        """获取指定账号的聊天列表"""
        account = self.get_account(tenant_id, account_db_id)
        if account and account.connected:
            return await account.get_dialogs()
        return []

    async def get_all_dialogs(self, tenant_id: int) -> Dict[int, list]:
        result = {}
        for account in self.get_tenant_accounts(tenant_id):
            result[account.account_id] = await account.get_dialogs()
        return result

    def get_client(self, tenant_id: int, account_db_id: int):
        """获取 Telethon client（用于发消息等）"""
        account = self.get_account(tenant_id, account_db_id)
        if account and account.connected:
            return account._client
        return None


telegram_service = TelegramService()
