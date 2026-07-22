from collections.abc import Mapping
from typing import Any


class _SafeValues(dict):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def render_message_template(template_text: str, values: Mapping[str, Any]) -> str:
    return template_text.format_map(_SafeValues({key: str(value) for key, value in values.items()}))
