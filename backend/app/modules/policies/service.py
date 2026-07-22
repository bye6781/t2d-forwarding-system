from datetime import datetime

from fastapi import HTTPException

from app.modules.policies.filters import evaluate_filter_rules
from app.modules.policies.media import evaluate_media_policy
from app.modules.policies.repository import policy_repository
from app.modules.policies.templates import render_message_template


class PolicyService:
    async def update_filter(self, tenant_id: int, rule_id: int, payload):
        row = await policy_repository.update_filter(tenant_id, rule_id, payload)
        if not row:
            raise HTTPException(404, "过滤规则不存在")
        return row

    async def delete_filter(self, tenant_id: int, rule_id: int):
        if not await policy_repository.delete_filter(tenant_id, rule_id):
            raise HTTPException(404, "过滤规则不存在")

    async def test_filters(self, tenant_id: int, payload):
        matched, reason = evaluate_filter_rules(
            await policy_repository.filters(tenant_id), payload.model_dump()
        )
        return {"should_filter": matched, "reason": reason}

    async def update_template(self, tenant_id: int, template_id: int, payload):
        row = await policy_repository.update_template(tenant_id, template_id, payload)
        if not row:
            raise HTTPException(404, "消息模板不存在")
        return row

    async def delete_template(self, tenant_id: int, template_id: int):
        if not await policy_repository.delete_template(tenant_id, template_id):
            raise HTTPException(404, "消息模板不存在")

    async def default_template(self, tenant_id: int, template_id: int):
        row = await policy_repository.default_template(tenant_id, template_id)
        if not row:
            raise HTTPException(404, "消息模板不存在")
        return row

    async def preview(self, tenant_id: int, payload):
        template = None
        if payload.template_id:
            template = await policy_repository.template(tenant_id, payload.template_id)
            if not template:
                raise HTTPException(404, "消息模板不存在")
        template_text = payload.template_text or (template and template["template_text"])
        if not template_text:
            raise HTTPException(422, "模板内容不能为空")
        time_format = (template and template["time_format"]) or "%Y-%m-%d %H:%M"
        return {
            "preview": render_message_template(template_text, {
                "source": "Telegram 示例群组", "sender": "示例用户",
                "content": "这是一条模板预览消息", "type": "text",
                "chat_id": "-100123", "time": datetime.now().strftime(time_format),
            })
        }

    async def test_media(self, tenant_id: int, payload):
        config = await policy_repository.media(tenant_id)
        allowed, reason = evaluate_media_policy(config, payload.media_type, payload.file_size_bytes)
        return {"should_forward": allowed, "reason": reason}


policy_service = PolicyService()
