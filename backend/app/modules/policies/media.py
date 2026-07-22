from collections.abc import Mapping
from typing import Any


def evaluate_media_policy(
    config: Mapping[str, Any], media_type: str, file_size_bytes: int
) -> tuple[bool, str]:
    allowed_types = config.get("allowed_types") or ["photo", "video", "document"]
    if media_type not in allowed_types:
        return False, f"媒体类型 {media_type} 未启用"
    maximum = int(config.get("max_file_size_bytes") or 52428800)
    if file_size_bytes > maximum:
        return False, "媒体文件超过大小限制"
    return True, ""
