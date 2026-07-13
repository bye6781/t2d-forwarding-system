"""
消息转发服务 - 多租户版
核心引擎：Telegram -> 钉钉，完全按租户隔离
"""
import asyncio
import logging
import os
import re
import uuid
from pathlib import Path
from typing import List, Dict, Any, Optional

from telethon.events import NewMessage
from telethon.tl.types import (
    MessageMediaPhoto, MessageMediaDocument, MessageMediaContact,
    MessageMediaGeo, MessageMediaPoll,
    DocumentAttributeVideo, DocumentAttributeAudio,
)

from app.core.database import database
from app.core.tenant_context import TenantContext
from app.services.telegram_service import telegram_service
from app.services.dingtalk_service import dingtalk_service
from app.services.translation_service import translation_service
from app.services.filter_service import filter_service
from app.services.quota_service import quota_service

logger = logging.getLogger(__name__)

SERVER_PUBLIC_URL = os.getenv("SERVER_PUBLIC_URL", "http://46.8.78.121:8001")


def html_to_plain_text(html_text: str) -> str:
    if not html_text:
        return ""
    text = html_text
    text = re.sub(r'<a[^>]*>(.*?)</a>', r'\1', text, flags=re.DOTALL)
    text = re.sub(r'<br\s*/?\s*>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'</(?:p|div|tr|li|h[1-6])>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<[^>]+>', '', text)
    text = text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
    text = text.replace('&quot;', '"').replace("&#39;", "'").replace('&nbsp;', ' ')
    text = re.sub(r'\*\*\*(.*?)\*\*\*', r'\1', text)
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'__(.*?)__', r'\1', text)
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    text = re.sub(r'_(.*?)_', r'\1', text)
    text = re.sub(r'`(.*?)`', r'\1', text)
    text = re.sub(r'~~(.*?)~~', r'\1', text)
    text = re.sub(r'^#+\s*', '', text, flags=re.MULTILINE)
    text = re.sub(r'!\[[^\]]*\]\((?:[^()]*|\([^()]*\))*\)', '', text, flags=re.DOTALL)
    text = re.sub(r'!\[[^\]]*\]\[[^\]]*\]', '', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def html_to_markdown(html_text: str) -> str:
    if not html_text:
        return ""
    md = html_text
    md = re.sub(r'<br\s*/?\s*>', '\n', md, flags=re.IGNORECASE)
    md = re.sub(r'</(?:p|div|tr|li|h[1-6]|blockquote)>', '\n', md, flags=re.IGNORECASE)
    md = re.sub(r'<b>(.*?)</b>', r'**\1**', md, flags=re.DOTALL)
    md = re.sub(r'<strong>(.*?)</strong>', r'**\1**', md, flags=re.DOTALL)
    md = re.sub(r'<i>(.*?)</i>', r'*\1*', md, flags=re.DOTALL)
    md = re.sub(r'<em>(.*?)</em>', r'*\1*', md, flags=re.DOTALL)
    md = re.sub(r'<code>(.*?)</code>', r'`\1`', md, flags=re.DOTALL)
    md = re.sub(r'<pre>(.*?)</pre>', r'```\n\1\n```', md, flags=re.DOTALL)
    md = re.sub(r'<a href="([^"]*)">(.*?)</a>', r'[\2](\1)', md, flags=re.DOTALL)
    md = re.sub(r'<s>(.*?)</s>', r'~~\1~~', md, flags=re.DOTALL)
    md = re.sub(r'<[^>]+>', '', md)
    md = md.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
    md = md.replace('&quot;', '"').replace("&#39;", "'").replace('&nbsp;', ' ')
    md = re.sub(r'\n{3,}', '\n\n', md)
    return md.strip()


def format_markdown(md_text: str) -> str:
    if not md_text:
        return ""
    lines = md_text.split('\n')
    formatted = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            formatted.append('')
            continue
        stripped = re.sub(r'  +', ' ', stripped)
        if not stripped.startswith('#') and not stripped.startswith('```') and not stripped.startswith('>'):
            stripped = stripped + '  '
        formatted.append(stripped)
    result = '\n'.join(formatted)
    result = re.sub(r'\n{3,}', '\n\n', result)
    return result.strip()


class ForwardingService:
    """多租户消息转发引擎"""

    def __init__(self):
        self._running = False
        self._handler_registered = False
        self._processed_messages: set = set()
        self._pending_albums: Dict[int, List[Dict]] = {}
        self._filtered_albums: set = set()
        self._stats = {"messages_received": 0, "messages_forwarded": 0, "messages_failed": 0}

    async def start(self):
        """启动转发引擎"""
        self._running = True
        if not self._handler_registered:
            telegram_service.add_handler(self._handle_message)
            self._handler_registered = True
        logger.info("Forwarding engine started (multi-tenant)")

    async def stop(self):
        self._running = False
        logger.info("Forwarding engine stopped")

    async def _handle_message(self, event, account_id: int = 0, tenant_id: int = 0):
        """处理 Telegram 消息事件 - 自动设置租户上下文"""
        if not self._running:
            return

        # 设置租户上下文
        TenantContext.set(tenant_id)

        try:
            await self._process_event(event, account_id, tenant_id)
        except Exception as e:
            logger.error(f"[T{tenant_id}] Error processing message: {e}", exc_info=True)
        finally:
            TenantContext.clear()

    async def _process_event(self, event, account_id: int, tenant_id: int):
        """处理消息事件的核心逻辑"""
        from telethon.events import NewMessage as NM

        if isinstance(event, NM.Event):
            chat_id = event.chat_id
            message = event.message
            message_text = message.text or ""
            message_id = message.id
            sender_id = event.sender_id
            media = event.media
            message_html = getattr(message, 'html', '') or message_text
        else:
            message = getattr(event, 'message', None)
            if not message:
                return
            if hasattr(message, 'edit_date') and message.edit_date:
                return
            message_text = getattr(message, 'text', '') or ''
            message_html = getattr(message, 'html', '') or message_text
            message_id = getattr(message, 'id', None)
            peer_id = getattr(message, 'peer_id', None)
            if peer_id:
                if hasattr(peer_id, 'channel_id'):
                    chat_id = int(f"-100{peer_id.channel_id}")
                elif hasattr(peer_id, 'chat_id'):
                    chat_id = -peer_id.chat_id
                elif hasattr(peer_id, 'user_id'):
                    chat_id = peer_id.user_id
                else:
                    return
            else:
                return
            sender_id = None
            from_id = getattr(message, 'from_id', None)
            if from_id and hasattr(from_id, 'user_id'):
                sender_id = from_id.user_id
            media = getattr(message, 'media', None)

        message_text = html_to_plain_text(message_html)
        message_md = html_to_markdown(message_html)

        self._stats["messages_received"] += 1

        # 消息去重
        msg_key = f"{tenant_id}:{chat_id}:{message_id}"
        if msg_key in self._processed_messages:
            return
        self._processed_messages.add(msg_key)
        if len(self._processed_messages) > 2000:
            to_remove = list(self._processed_messages)[:1000]
            for key in to_remove:
                self._processed_messages.discard(key)

        # 配额检查
        quota_ok = await quota_service.check_message_quota(tenant_id)
        if not quota_ok:
            logger.warning(f"[T{tenant_id}] Quota exceeded, message dropped")
            return

        # 查找匹配的映射规则（从 DB 加载）
        mappings = await database.get_mappings(tenant_id)
        matched = [m for m in mappings
                   if m.get("source_chat_id") == chat_id or str(m.get("source_chat_id")) == str(chat_id)]

        if not matched:
            return

        # 过滤检查
        should_filter, reason = await filter_service.should_filter({
            "text": message_text, "html": message_html,
            "chat_id": chat_id, "user_id": sender_id
        })
        if should_filter:
            logger.info(f"[T{tenant_id}] Message filtered: {reason}")
            return

        # @ 提及过滤
        mention_pattern = re.compile(r'@[a-zA-Z_]', re.IGNORECASE)
        if mention_pattern.search(message_text or "") or mention_pattern.search(message_html or ""):
            return

        # 处理媒体
        media_info = None
        if media:
            media_info = await self._process_media(message, media, tenant_id)

        # 获取发送者名称
        sender_name = "Unknown"
        try:
            sender = None
            if isinstance(event, NM.Event) and hasattr(event, 'get_sender'):
                sender = await event.get_sender()
            elif sender_id:
                client = telegram_service.get_client(tenant_id, account_id)
                if client:
                    sender = await client.get_entity(sender_id)
            if sender:
                sender_type = type(sender).__name__
                if sender_type in ("Channel", "Chat"):
                    sender_name = sender.title or sender_type
                else:
                    sender_name = getattr(sender, 'first_name', '') or ''
                    if getattr(sender, 'last_name', None):
                        sender_name += ' ' + sender.last_name
                    sender_name = sender_name.strip() or 'Unknown'
        except Exception as e:
            logger.warning(f"[T{tenant_id}] Failed to get sender: {e}")

        # 跳过空消息
        has_content = message_text and message_text.strip()
        has_media = media_info is not None
        if not has_content and not has_media:
            return

        # 转发到所有匹配的目标
        for mapping in matched:
            await self._forward_to_dingtalk(
                tenant_id=tenant_id, mapping=mapping,
                message_text=message_text, message_md=message_md,
                media_info=media_info, sender_name=sender_name,
                message_id=message_id
            )
            # 记录用量
            await quota_service.record_message(tenant_id)

    async def _process_media(self, message, media, tenant_id: int) -> Optional[Dict]:
        """处理媒体文件，按租户存储"""
        try:
            media_dir = Path(f"/app/data/{tenant_id}/uploads")
            media_dir.mkdir(parents=True, exist_ok=True)

            if isinstance(media, MessageMediaPhoto):
                file_name = f"{uuid.uuid4().hex}.jpg"
                file_path = media_dir / file_name
                await message.download_media(str(file_path))
                url = f"{SERVER_PUBLIC_URL}/static/{tenant_id}/{file_name}"
                return {"type": "photo", "url": url, "caption": ""}

            elif isinstance(media, MessageMediaDocument):
                doc = media.document
                is_video = any(isinstance(a, DocumentAttributeVideo) for a in (doc.attributes or []))
                is_sticker = any(type(a).__name__ == 'DocumentAttributeSticker' for a in (doc.attributes or []))
                mime_type = getattr(doc, 'mime_type', '') or ''

                if is_sticker or mime_type == 'image/webp':
                    return None

                file_name = f"{uuid.uuid4().hex[:8]}"
                for attr in (doc.attributes or []):
                    if hasattr(attr, 'file_name'):
                        fn = attr.file_name or ''
                        if fn:
                            file_name = Path(fn).name
                            break

                if '.' not in file_name:
                    ext_map = {'video/mp4': '.mp4', 'image/gif': '.gif', 'audio/ogg': '.ogg'}
                    file_name += ext_map.get(mime_type, '.bin')

                file_path = media_dir / file_name
                await message.download_media(str(file_path))
                url = f"{SERVER_PUBLIC_URL}/static/{tenant_id}/{file_name}"

                if is_video or mime_type.startswith('video/'):
                    return {"type": "video", "url": url, "caption": "", "file_name": file_name}
                elif mime_type.startswith('image/'):
                    return {"type": "photo", "url": url, "caption": ""}
                elif mime_type.startswith('audio/'):
                    return {"type": "voice", "url": url, "caption": "", "file_name": file_name}
                else:
                    return {"type": "document", "url": url, "caption": "", "file_name": file_name}

            elif isinstance(media, MessageMediaContact):
                contact = media.contact
                name = f"{contact.first_name or ''} {contact.last_name or ''}".strip()
                return {"type": "contact", "url": "", "caption": f"联系人: {name} ({contact.phone or ''})"}

            elif isinstance(media, MessageMediaGeo):
                geo = media.geo
                lat, lon = getattr(geo, 'lat', 0), getattr(geo, 'long', 0)
                return {"type": "location", "url": f"https://maps.google.com/?q={lat},{lon}",
                        "caption": f"位置: {lat}, {lon}"}

        except Exception as e:
            logger.error(f"[T{tenant_id}] Media processing error: {e}", exc_info=True)
        return None

    async def _forward_to_dingtalk(self, tenant_id: int, mapping: Dict,
                                   message_text: str, message_md: str,
                                   media_info: Optional[Dict], sender_name: str,
                                   message_id: int):
        """转发消息到钉钉"""
        import time
        start_time = time.time()

        try:
            target_bot_ids = mapping.get("target_bot_ids", [])
            if isinstance(target_bot_ids, str):
                target_bot_ids = [target_bot_ids]

            # 加载租户的钉钉机器人配置
            bots = await database.get_dingtalk_bots(tenant_id)
            translation_enabled = mapping.get("translation_enabled", True)

            # 翻译
            display_text = message_md if message_md else message_text
            final_text = display_text
            if message_text and translation_enabled:
                try:
                    final_text = await translation_service.translate(message_text, target_lang="zh")
                except Exception:
                    final_text = message_text

            for bot_ref in target_bot_ids:
                # bot_ref 可能是 bot_id 字符串或数字 ID
                bot_config = None
                if isinstance(bot_ref, int) or (isinstance(bot_ref, str) and bot_ref.isdigit()):
                    bot_config = next((b for b in bots if b["id"] == int(bot_ref)), None)
                else:
                    bot_config = next((b for b in bots if b["bot_id"] == bot_ref), None)

                if not bot_config:
                    logger.error(f"[T{tenant_id}] Bot not found: {bot_ref}")
                    continue

                webhook = bot_config["webhook"]
                secret = bot_config.get("secret", "")
                bot_id_str = bot_config.get("bot_id", str(bot_config["id"]))

                # 构建消息内容
                if media_info and media_info.get("type") == "photo":
                    media_url = media_info.get("url", "")
                    clean_text = re.sub(r'!\[[^\]]*\]\([^)]*\)', '', final_text, flags=re.DOTALL).strip()
                    full_text = f"{clean_text}\n\n![图片]({media_url})" if clean_text else f"![图片]({media_url})"
                    result = await dingtalk_service.send_markdown(
                        webhook=webhook, title="消息转发", text=full_text,
                        secret=secret, bot_id=bot_id_str
                    )
                elif media_info and media_info.get("type") == "video":
                    video_url = media_info.get("url", "")
                    result = await dingtalk_service.send_action_card(
                        webhook=webhook, title="视频消息",
                        text=final_text.strip() or "点击播放",
                        btn_title="▶ 点击播放视频", btn_url=video_url,
                        secret=secret, bot_id=bot_id_str
                    )
                else:
                    content_parts = []
                    if media_info:
                        caption = media_info.get("caption", "")
                        if caption:
                            content_parts.append(caption)
                        elif media_info.get("url"):
                            content_parts.append(f"下载链接: {media_info['url']}")
                    if final_text.strip():
                        content_parts.append(final_text)
                    full_text = '\n'.join(content_parts) if content_parts else final_text
                    full_text = format_markdown(full_text)
                    result = await dingtalk_service.send_markdown(
                        webhook=webhook, title="消息转发", text=full_text,
                        secret=secret, bot_id=bot_id_str
                    )

                processing_time = int((time.time() - start_time) * 1000)
                status = "success" if result.get("errcode") == 0 else "failed"
                if status == "success":
                    self._stats["messages_forwarded"] += 1
                else:
                    self._stats["messages_failed"] += 1
                    logger.error(f"[T{tenant_id}] Forward failed: {result}")

                await database.add_forward_record(
                    tenant_id=tenant_id,
                    chat_id=mapping.get("source_chat_id"),
                    message_id=message_id,
                    bot_id=bot_id_str,
                    message_type=media_info.get("type", "text") if media_info else "text",
                    content_preview=message_text[:100] if message_text else "",
                    status=status,
                    processing_time_ms=processing_time
                )

        except Exception as e:
            self._stats["messages_failed"] += 1
            logger.error(f"[T{tenant_id}] Forward error: {e}", exc_info=True)

    def get_stats(self) -> Dict:
        return self._stats.copy()


forwarding_service = ForwardingService()
