from typing import Any, Iterable


def success(data: Any) -> dict[str, Any]:
    return {"data": data}


def page(items: Iterable[Any], *, total: int, limit: int, offset: int) -> dict[str, Any]:
    return {
        "data": {
            "items": list(items),
            "total": total,
            "limit": limit,
            "offset": offset,
        }
    }
