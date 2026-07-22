"""Live API smoke test for a freshly initialized T2D deployment."""

import json
import os
import urllib.error
import urllib.request


BASE = os.environ.get("T2D_BASE_URL", "http://127.0.0.1:8002/api").rstrip("/")
ADMIN_PASSWORD = os.environ["T2D_ADMIN_PASSWORD"]
TENANT_PASSWORD = os.environ["T2D_TENANT_PASSWORD"]


def request(path, method="GET", payload=None, token=None, expected=(200,), raw=False):
    body = json.dumps(payload).encode() if payload is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(BASE + path, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            status = response.status
            data = response.read()
            content_type = response.headers.get("content-type", "")
    except urllib.error.HTTPError as exc:
        status = exc.code
        data = exc.read()
        content_type = exc.headers.get("content-type", "")
    assert status in expected, (method, path, status, data.decode(errors="replace"))
    if raw:
        return data
    return json.loads(data) if data and "json" in content_type else None


def login(username, password):
    return request("/auth/login", "POST", {"username": username, "password": password})


admin_login = login("admin", ADMIN_PASSWORD)
tenant_login = login("testtenant", TENANT_PASSWORD)
admin_token = admin_login["access_token"]
tenant_token = tenant_login["access_token"]
assert admin_login["user"]["is_platform_admin"] is True
assert tenant_login["user"]["is_platform_admin"] is False
request("/auth/login", "POST", {"username": "admin", "password": "wrong-password"}, expected=(401,))

tenants = request("/system/tenants", token=admin_token)
test_tenant = next(row for row in tenants if row["slug"] == "t2d-test")
assert request("/system/stats", token=admin_token)["total_tenants"] == 1
request("/system/stats", token=tenant_token, expected=(403,))
request("/system/tenants", token=tenant_token, expected=(403,))

isolated_login = request(
    "/auth/register",
    "POST",
    {"team_name": "Isolation Tenant", "username": "isolatedtenant", "password": "IsolationPass-2026"},
)
isolated_token = isolated_login["access_token"]

for path in (
    "/tenant/info", "/tenant/usage", "/system/info", "/forwarding/status",
    "/telegram/accounts", "/dingtalk/bots", "/mappings", "/filter-rules",
    "/templates", "/media-configs",
):
    request(path, token=tenant_token)

request(f"/system/tenants/{test_tenant['id']}/plan?plan=pro", "PUT", token=admin_token)
member = request(
    "/tenant/members", "POST",
    {"username": "smokemember", "password": "SmokeMember-2026", "role": "viewer"},
    tenant_token,
)
request(f"/tenant/members/{member['id']}", "PUT", {"role": "member"}, isolated_token, expected=(404,))
request(f"/tenant/members/{member['id']}", "DELETE", token=tenant_token)
request("/tenant/change-plan", "POST", {"plan": "basic"}, tenant_token)

rule = request(
    "/filter-rules", "POST",
    {"name": "Block spam", "rule_type": "keyword_exclude", "config": {"keywords": ["spam"]}, "priority": 5},
    tenant_token,
)
assert request(
    "/filter-rules/test-message", "POST",
    {"text": "contains spam", "sender": "tester", "message_type": "text", "chat_id": "1"},
    tenant_token,
)["should_filter"] is True
request(f"/filter-rules/{rule['id']}", "DELETE", token=isolated_token, expected=(404,))
request(
    f"/filter-rules/{rule['id']}", "PUT",
    {"name": "Block ads", "rule_type": "keyword_exclude", "config": {"keywords": ["ads"]}, "priority": 6},
    tenant_token,
)

template = request(
    "/templates", "POST",
    {"name": "Default", "template_text": "{sender}: {content}", "enabled": True, "is_default": True},
    tenant_token,
)
preview = request("/templates/preview", "POST", {"template_id": template["id"]}, tenant_token)
assert "示例用户" in preview["preview"]
request(f"/templates/{template['id']}", "DELETE", token=isolated_token, expected=(404,))
request(f"/templates/{template['id']}/default", "PUT", token=tenant_token)

media = request(
    "/media-configs", "PUT",
    {"max_file_size_bytes": 1024, "allowed_types": ["photo"], "thumbnail_enabled": True,
     "thumbnail_max_width": 320, "thumbnail_quality": 75, "forward_as_link": False},
    tenant_token,
)
assert media["max_file_size_bytes"] == 1024
assert request(
    "/media-configs/test", "POST", {"media_type": "video", "file_size_bytes": 512}, tenant_token
)["should_forward"] is False

account = request(
    "/telegram/accounts", "POST",
    {"name": "Smoke TG", "api_id": 123456, "api_hash": "dummy-api-hash", "phone": "+10000000000"},
    tenant_token,
)
request(f"/telegram/accounts/{account['data']['id']}", "DELETE", token=isolated_token, expected=(404,))

bot = request(
    "/dingtalk/bots", "POST",
    {"bot_id": "smoke-bot", "name": "Smoke Bot", "webhook": "https://example.invalid/webhook", "secret": ""},
    tenant_token,
)
request("/dingtalk/bots/smoke-bot", "PUT", {"enabled": False}, tenant_token)
request("/dingtalk/bots/smoke-bot", "DELETE", token=isolated_token, expected=(404,))

mapping = request(
    "/mappings", "POST",
    {"source_chat_id": -1001234567890, "target_bot_ids": ["smoke-bot"],
     "translation_enabled": False, "filter_enabled": True, "enabled": True},
    tenant_token,
)
mapping_id = mapping["data"]["id"]
request(f"/mappings/{mapping_id}", "DELETE", token=isolated_token, expected=(404,))
request(f"/mappings/{mapping_id}", "PUT", {"enabled": False}, tenant_token)

request("/audit/logs", token=tenant_token)
assert request("/audit/login-logs", token=tenant_token)
assert request("/audit/api-logs", token=tenant_token)
summary = request("/audit/summary", token=tenant_token)
assert summary["total_logins"] >= 1
assert summary["total_api_calls"] >= 1
assert request("/audit/logs/export", token=tenant_token, raw=True).startswith(b"\xef\xbb\xbf")

request(f"/mappings/{mapping_id}", "DELETE", token=tenant_token)
request("/dingtalk/bots/smoke-bot", "DELETE", token=tenant_token)
request(f"/telegram/accounts/{account['data']['id']}", "DELETE", token=tenant_token)
request(f"/templates/{template['id']}", "DELETE", token=tenant_token)
request(f"/filter-rules/{rule['id']}", "DELETE", token=tenant_token)

print("api_smoke: ok")
