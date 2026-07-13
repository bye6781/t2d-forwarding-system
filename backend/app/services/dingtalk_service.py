"""
钉钉 Webhook 发送服务 - 多租户隔离版
每个租户独立管理自己的钉钉机器人
"""
import time
import hmac
import hashlib
import base64
import urllib.parse
import logging
import asyncio
from typing import Optional

import aiohttp

logger = logging.getLogger(__name__)


class DingTalkService:
    """钉钉消息发送服务（多租户版）"""

    def __init__(self):
        self._semaphore = asyncio.Semaphore(50)
        self._rate_limits = {}  # bot_id -> (count, window_start)
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    def _sign(self, secret: str, timestamp: int) -> str:
        string_to_sign = f"{timestamp}\n{secret}"
        hmac_code = hmac.new(
            secret.encode("utf-8"),
            string_to_sign.encode("utf-8"),
            digestmod=hashlib.sha256
        ).digest()
        return urllib.parse.quote_plus(base64.b64encode(hmac_code).decode("utf-8"))

    def _check_rate_limit(self, bot_id: str, limit: int = 20) -> bool:
        now = time.time()
        window_start = now - 60
        if bot_id in self._rate_limits:
            count, start = self._rate_limits[bot_id]
            if start < window_start:
                self._rate_limits[bot_id] = (1, now)
                return True
            if count >= limit:
                return False
            self._rate_limits[bot_id] = (count + 1, start)
            return True
        else:
            self._rate_limits[bot_id] = (1, now)
            return True

    async def send_text(self, webhook: str, content: str, secret: str = "",
                        at_mobiles: list = None, at_all: bool = False,
                        bot_id: str = "default") -> dict:
        data = {
            "msgtype": "text",
            "text": {"content": content},
            "at": {"atMobiles": at_mobiles or [], "isAtAll": at_all}
        }
        return await self._send(webhook, data, secret, bot_id)

    async def send_markdown(self, webhook: str, title: str, text: str,
                            secret: str = "", bot_id: str = "default") -> dict:
        data = {
            "msgtype": "markdown",
            "markdown": {"title": title, "text": text}
        }
        return await self._send(webhook, data, secret, bot_id)

    async def send_image(self, webhook: str, pic_url: str,
                         secret: str = "", bot_id: str = "default") -> dict:
        data = {
            "msgtype": "image",
            "image": {"picURL": pic_url}
        }
        return await self._send(webhook, data, secret, bot_id)

    async def send_action_card(self, webhook: str, title: str, text: str,
                               btn_title: str, btn_url: str,
                               secret: str = "", bot_id: str = "default") -> dict:
        data = {
            "msgtype": "actionCard",
            "actionCard": {
                "title": title, "text": text,
                "btnOrientation": "0",
                "btns": [{"title": btn_title, "actionURL": btn_url}]
            }
        }
        return await self._send(webhook, data, secret, bot_id)

    async def _send(self, webhook: str, data: dict, secret: str = "",
                    bot_id: str = "default") -> dict:
        if not self._check_rate_limit(bot_id):
            logger.warning(f"DingTalk rate limit exceeded for bot: {bot_id}")
            return {"errcode": -1, "errmsg": "Rate limit exceeded"}

        url = webhook
        if secret:
            timestamp = int(time.time() * 1000)
            sign = self._sign(secret, timestamp)
            separator = "&" if "?" in webhook else "?"
            url = f"{webhook}{separator}timestamp={timestamp}&sign={sign}"

        async with self._semaphore:
            try:
                session = await self._get_session()
                async with session.post(
                    url, json=data,
                    timeout=aiohttp.ClientTimeout(total=10),
                    headers={"Content-Type": "application/json"}
                ) as resp:
                    result = await resp.json()
                    if result.get("errcode") != 0:
                        logger.warning(f"DingTalk send failed: {result}")
                    return result
            except Exception as e:
                logger.error(f"DingTalk send error: {e}")
                return {"errcode": -1, "errmsg": str(e)}


dingtalk_service = DingTalkService()
