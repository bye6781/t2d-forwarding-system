"""
过滤引擎 - 多租户版
每个租户独立配置过滤规则
"""
import re
import logging
from typing import Optional

from app.core.database import database
from app.core.tenant_context import TenantContext

logger = logging.getLogger(__name__)


class FilterService:
    """消息过滤服务（多租户版）"""

    def __init__(self):
        self._config_cache = {}  # tenant_id -> config dict

    async def _get_tenant_config(self, tenant_id: int) -> dict:
        if tenant_id in self._config_cache:
            return self._config_cache[tenant_id]

        config = await database.get_filter_config(tenant_id)
        if config:
            self._config_cache[tenant_id] = config
        else:
            self._config_cache[tenant_id] = {"enabled": True, "blocklist": {}, "content_filter": {}, "button_filter": {}}
        return self._config_cache[tenant_id]

    def invalidate_cache(self, tenant_id: int = None):
        if tenant_id:
            self._config_cache.pop(tenant_id, None)
        else:
            self._config_cache.clear()

    async def should_filter(self, message: dict) -> tuple:
        """
        检查消息是否应被过滤
        返回 (是否过滤, 原因)
        """
        tenant_id = TenantContext.get()
        config = await self._get_tenant_config(tenant_id)

        if not config.get("enabled", True):
            return False, ""

        text = message.get("text", "")
        html = message.get("html", "")
        chat_id = message.get("chat_id")
        user_id = message.get("user_id")

        blocklist = config.get("blocklist", {})

        # 关键词过滤
        for kw in blocklist.get("keywords", []):
            if kw.lower() in text.lower() or (html and kw.lower() in html.lower()):
                return True, f"Keyword: {kw}"

        # 用户过滤
        if user_id and str(user_id) in [str(u) for u in blocklist.get("users", [])]:
            return True, f"Blocked user: {user_id}"

        # 群组过滤
        if chat_id and str(chat_id) in [str(c) for c in blocklist.get("chats", [])]:
            return True, f"Blocked chat: {chat_id}"

        # URL 模式过滤
        all_urls = []
        if html:
            href_urls = re.findall(r"href\s*=\s*[\"']([^\"']+)[\"']", html, re.IGNORECASE)
            all_urls.extend(href_urls)
        text_urls = re.findall(r"https?://[^\s]+", text, re.IGNORECASE)
        all_urls.extend(text_urls)

        for pattern in blocklist.get("url_patterns", []):
            if re.search(pattern, text, re.IGNORECASE):
                return True, f"URL pattern: {pattern}"
            for url in all_urls:
                if re.search(pattern, url, re.IGNORECASE):
                    return True, f"URL pattern: {pattern}"

        # 内容长度过滤
        content_filter = config.get("content_filter", {})
        if content_filter.get("enabled"):
            min_len = content_filter.get("min_length", 0)
            max_len = content_filter.get("max_length", 10000)
            if len(text) < min_len or len(text) > max_len:
                return True, f"Content length: {len(text)}"

        # 按钮关键词过滤
        button_filter = config.get("button_filter", {})
        if button_filter.get("enabled"):
            buttons = message.get("buttons", [])
            for btn in buttons:
                for kw in button_filter.get("keywords", []):
                    if kw.lower() in str(btn).lower():
                        return True, f"Button keyword: {kw}"

        return False, ""


filter_service = FilterService()
