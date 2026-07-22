import re
from collections.abc import Mapping, Sequence
from typing import Any


def evaluate_filter_rules(
    rules: Sequence[Mapping[str, Any]], message: Mapping[str, Any]
) -> tuple[bool, str]:
    text = str(message.get("text") or "")
    sender = str(message.get("sender") or message.get("user_id") or "")
    message_type = str(message.get("message_type") or "text")
    chat_id = str(message.get("chat_id") or "")

    for rule in sorted(rules, key=lambda item: (item.get("priority", 10), item.get("id", 0))):
        if not rule.get("enabled", True):
            continue
        config = rule.get("config") or {}
        rule_type = rule.get("rule_type")
        matched = False
        if rule_type == "keyword_exclude":
            matched = any(str(keyword).lower() in text.lower() for keyword in config.get("keywords", []))
        elif rule_type == "keyword_include":
            keywords = [str(keyword).lower() for keyword in config.get("keywords", [])]
            matched = bool(keywords) and not any(keyword in text.lower() for keyword in keywords)
        elif rule_type == "regex":
            try:
                matched = bool(re.search(str(config.get("pattern", "")), text, re.IGNORECASE))
            except re.error:
                matched = False
        elif rule_type == "message_type":
            matched = message_type in {str(value) for value in config.get("types", [])}
        elif rule_type == "sender":
            matched = sender in {str(value) for value in config.get("senders", [])}
        elif rule_type == "chat":
            matched = chat_id in {str(value) for value in config.get("chat_ids", [])}
        elif rule_type == "legacy_config":
            if not config.get("enabled", True):
                continue
            blocklist = config.get("blocklist") or {}
            matched = any(
                str(keyword).lower() in text.lower()
                for keyword in blocklist.get("keywords", [])
            )
            matched = matched or sender in {str(value) for value in blocklist.get("users", [])}
            matched = matched or chat_id in {str(value) for value in blocklist.get("chats", [])}
            content = config.get("content_filter") or {}
            if content.get("enabled"):
                matched = matched or len(text) < int(content.get("min_length", 0))
                matched = matched or len(text) > int(content.get("max_length", 10000))
        if matched:
            return True, str(rule.get("name") or rule_type or "rule")
    return False, ""
