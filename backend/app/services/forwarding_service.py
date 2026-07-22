"""
消息转发服务 - 多租户版
核心引擎：Telegram -> 钉钉，完全按租户隔离
"""
import asyncio
import logging
import os
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from telethon.events import NewMessage
from telethon.tl.types import (
    MessageMediaPhoto, MessageMediaDocument, MessageMediaContact,
    MessageMediaGeo, MessageMediaPoll,
    DocumentAttributeVideo, DocumentAttributeAudio,
)

from app.core.tenant_context import TenantContext
from app.services.telegram_service import telegram_service
from app.services.dingtalk_service import dingtalk_service
from app.services.translation_service import translation_service
from app.services.filter_service import filter_service
from app.services.quota_service import quota_service
from app.core.config import settings
from app.modules.forwarding.repository import forwarding_repository
from app.modules.connectors.repository import connector_repository
from app.modules.policies.repository import policy_repository
from app.modules.forwarding.runtime import tenant_runtime
from app.modules.policies.media import evaluate_media_policy
from app.modules.policies.templates import render_message_template

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


MARKDOWN_TOKEN_PATTERN = re.compile(
    r"\r?\n|[ \t]+|\]\([^)]*\)|```|\*\*|__|~~|`|(?<!\*)\*(?!\*)|(?<!_)_(?!_)"
)


def protect_markdown_format(source_md: str) -> tuple[str, dict[str, str]]:
    """Replace Markdown syntax with stable tokens before machine translation."""
    tokens: dict[str, str] = {}

    def replace(match: re.Match) -> str:
        token = f"[[T2D_FMT_{len(tokens)}]]"
        tokens[token] = match.group(0)
        return token

    return MARKDOWN_TOKEN_PATTERN.sub(replace, source_md), tokens


def restore_markdown_format(translated_text: str, tokens: dict[str, str]) -> str:
    restored = translated_text or ""
    for token, marker in tokens.items():
        restored = restored.replace(token, marker)
    return restored


def normalize_dingtalk_markdown(md_text: str) -> str:
    """Convert Telegram Markdown into the subset rendered reliably by DingTalk."""
    if not md_text:
        return ""
    normalized = md_text.replace("__", "**")
    normalized = re.sub(r"\*{3,}", "**", normalized)

    def split_multiline(match: re.Match) -> str:
        marker, content = match.group(1), match.group(2)
        if "\n" not in content:
            return match.group(0)
        return "\n".join(
            f"{marker}{line}{marker}" if line.strip() else ""
            for line in content.split("\n")
        )

    normalized = re.sub(r"(\*\*|~~)(.*?)\1", split_multiline, normalized, flags=re.DOTALL)
    normalized = re.sub(
        r"[ \t]{2,}",
        lambda match: "&nbsp;" * len(match.group(0)),
        normalized,
    )
    if normalized.count("**") % 2:
        normalized += "**"
    if normalized.count("~~") % 2:
        normalized += "~~"
    return normalized.strip()


class ForwardingService:
    """多租户消息转发引擎"""

    def __init__(self):
        self._running = False
        self._handler_registered = False
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
        if not await tenant_runtime.is_running(tenant_id):
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
        message_md = getattr(message, "text_markdown", "") or html_to_markdown(message_html)

        self._stats["messages_received"] += 1

        # 消息去重
        if not await tenant_runtime.claim_message(tenant_id, chat_id, message_id):
            return

        # 配额检查
        quota_ok = await quota_service.check_message_quota(tenant_id)
        if not quota_ok:
            logger.warning(f"[T{tenant_id}] Quota exceeded, message dropped")
            return

        # 查找匹配的映射规则（从 DB 加载）
        mappings = await forwarding_repository.routes(tenant_id)
        matched = [m for m in mappings
                   if m.get("enabled", True)
                   and (m.get("source_chat_id") == chat_id or str(m.get("source_chat_id")) == str(chat_id))]

        if not matched:
            return

        # 在过滤前解析发送者和消息类型，确保高级规则使用真实字段。
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

        message_type = "text"
        if isinstance(media, MessageMediaPhoto):
            message_type = "photo"
        elif isinstance(media, MessageMediaDocument):
            doc = media.document
            mime_type = getattr(doc, "mime_type", "") or ""
            attributes = doc.attributes or []
            if any(type(a).__name__ == "DocumentAttributeSticker" for a in attributes):
                message_type = "sticker"
            elif any(isinstance(a, DocumentAttributeVideo) for a in attributes) or mime_type.startswith("video/"):
                message_type = "video"
            elif mime_type.startswith("image/"):
                message_type = "photo"
            elif mime_type.startswith("audio/"):
                audio = next((a for a in attributes if isinstance(a, DocumentAttributeAudio)), None)
                message_type = "voice" if getattr(audio, "voice", False) else "audio"
            else:
                message_type = "document"

        # 过滤检查
        should_filter, reason = await filter_service.should_filter({
            "text": message_text, "html": message_html,
            "chat_id": chat_id, "user_id": sender_id,
            "sender": sender_name, "message_type": message_type,
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

        # 跳过空消息
        has_content = message_text and message_text.strip()
        has_media = media_info is not None
        if not has_content and not has_media:
            return

        # 转发到所有匹配的目标
        if not await quota_service.reserve_message(tenant_id):
            logger.warning(f"[T{tenant_id}] Quota exceeded, message dropped")
            return

        for mapping in matched:
            await self._forward_to_dingtalk(
                tenant_id=tenant_id, mapping=mapping,
                message_text=message_text, message_md=message_md,
                media_info=media_info, sender_name=sender_name,
                message_id=message_id
            )
            # 记录用量

    async def _process_media(self, message, media, tenant_id: int) -> Optional[Dict]:
        """处理媒体文件，按租户存储"""
        try:
            media_config = await policy_repository.media_for_forwarding(tenant_id) or {
                "max_file_size_bytes": 52428800,
                "allowed_types": ["photo", "video", "document"],
                "forward_as_link": False,
            }
            media_dir = Path(settings.PUBLIC_MEDIA_DIR) / str(tenant_id) / "uploads"
            media_dir.mkdir(parents=True, exist_ok=True)

            if isinstance(media, MessageMediaPhoto):
                allowed, reason = evaluate_media_policy(media_config, "photo", 0)
                if not allowed:
                    logger.info(f"[T{tenant_id}] Media filtered: {reason}")
                    return None
                file_name = f"{uuid.uuid4().hex}.jpg"
                file_path = media_dir / file_name
                await message.download_media(str(file_path))
                url = f"{SERVER_PUBLIC_URL}/media/{tenant_id}/uploads/{file_name}"
                return {
                    "type": "photo", "url": url, "caption": "",
                    "forward_as_link": media_config.get("forward_as_link", False),
                }

            elif isinstance(media, MessageMediaDocument):
                doc = media.document
                is_video = any(isinstance(a, DocumentAttributeVideo) for a in (doc.attributes or []))
                is_sticker = any(type(a).__name__ == 'DocumentAttributeSticker' for a in (doc.attributes or []))
                mime_type = getattr(doc, 'mime_type', '') or ''
                audio_attr = next(
                    (a for a in (doc.attributes or []) if isinstance(a, DocumentAttributeAudio)),
                    None,
                )
                if is_sticker or mime_type == 'image/webp':
                    media_type = "sticker"
                elif is_video or mime_type.startswith('video/'):
                    media_type = "video"
                elif mime_type.startswith('image/'):
                    media_type = "photo"
                elif mime_type.startswith('audio/'):
                    media_type = "voice" if getattr(audio_attr, "voice", False) else "audio"
                else:
                    media_type = "document"
                allowed, reason = evaluate_media_policy(
                    media_config, media_type, int(getattr(doc, "size", 0) or 0)
                )
                if not allowed:
                    logger.info(f"[T{tenant_id}] Media filtered: {reason}")
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
                url = f"{SERVER_PUBLIC_URL}/media/{tenant_id}/uploads/{file_name}"

                return {
                    "type": media_type,
                    "url": url,
                    "caption": "",
                    "file_name": file_name,
                    "forward_as_link": media_config.get("forward_as_link", False),
                }

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
            bots = await connector_repository.bots(tenant_id)
            translation_enabled = mapping.get("translation_enabled", True)

            # 翻译
            display_text = message_md if message_md else message_text
            final_text = display_text
            if message_text and translation_enabled:
                try:
                    protected_text, format_tokens = protect_markdown_format(display_text)
                    translated_text = await translation_service.translate(protected_text, target_lang="zh")
                    final_text = restore_markdown_format(translated_text, format_tokens)
                except Exception:
                    final_text = message_md or message_text

            template = await policy_repository.default_template_for_forwarding(tenant_id)
            if template:
                final_text = render_message_template(
                    template["template_text"],
                    {
                        "source": str(mapping.get("source_chat_id", "")),
                        "time": datetime.now().strftime(template["time_format"]),
                        "sender": sender_name,
                        "content": final_text,
                        "type": media_info.get("type", "text") if media_info else "text",
                        "chat_id": str(mapping.get("source_chat_id", "")),
                    },
                )
            final_text = normalize_dingtalk_markdown(final_text)

            for bot_ref in target_bot_ids:
                # bot_ref 可能是 bot_id 字符串或数字 ID
                bot_config = None
                if isinstance(bot_ref, int) or (isinstance(bot_ref, str) and bot_ref.isdigit()):
                    bot_config = next((b for b in bots if b["id"] == int(bot_ref)), None)
                else:
                    bot_config = next((b for b in bots if b["bot_id"] == bot_ref), None)

                if not bot_config or not bot_config.get("enabled", True):
                    logger.error(f"[T{tenant_id}] Bot not found: {bot_ref}")
                    continue

                webhook = bot_config["webhook"]
                secret = bot_config.get("secret", "")
                bot_id_str = bot_config.get("bot_id", str(bot_config["id"]))

                # 构建消息内容
                if media_info and media_info.get("type") == "photo" and not media_info.get("forward_as_link"):
                    media_url = media_info.get("url", "")
                    clean_text = re.sub(r'!\[[^\]]*\]\([^)]*\)', '', final_text, flags=re.DOTALL).strip()
                    # Keep the original image first, followed by its Telegram caption/text.
                    full_text = f"![图片]({media_url})\n\n{clean_text}" if clean_text else f"![图片]({media_url})"
                    result = await dingtalk_service.send_markdown(
                        webhook=webhook, title="消息转发", text=full_text,
                        secret=secret, bot_id=bot_id_str
                    )
                elif media_info and media_info.get("type") == "video" and not media_info.get("forward_as_link"):
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

                await forwarding_repository.add_record(
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
