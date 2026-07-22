from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_user, require_feature_access
from app.modules.policies.repository import policy_repository
from app.modules.policies.schemas import (
    FilterRuleWrite, FilterTest, MediaPolicyTest, MediaPolicyWrite,
    TemplatePreview, TemplateWrite, TranslationPolicyWrite,
)
from app.modules.policies.service import policy_service
from app.shared.responses import success


router = APIRouter(tags=["Policies"], dependencies=[Depends(require_feature_access("policies"))])


@router.get("/filters")
async def filters(user=Depends(get_current_user)):
    return success(await policy_repository.filters(user["tenant_id"]))


@router.post("/filters")
async def create_filter(payload: FilterRuleWrite, user=Depends(get_current_user)):
    return success(await policy_repository.create_filter(user["tenant_id"], payload))


@router.put("/filters/{rule_id}")
async def update_filter(rule_id: int, payload: FilterRuleWrite, user=Depends(get_current_user)):
    return success(await policy_service.update_filter(user["tenant_id"], rule_id, payload))


@router.delete("/filters/{rule_id}")
async def delete_filter(rule_id: int, user=Depends(get_current_user)):
    await policy_service.delete_filter(user["tenant_id"], rule_id)
    return success({"message": "过滤规则已删除"})


@router.post("/filters/test")
async def test_filter(payload: FilterTest, user=Depends(get_current_user)):
    return success(await policy_service.test_filters(user["tenant_id"], payload))


@router.get("/templates")
async def templates(user=Depends(get_current_user)):
    return success(await policy_repository.templates(user["tenant_id"]))


@router.post("/templates")
async def create_template(payload: TemplateWrite, user=Depends(get_current_user)):
    return success(await policy_repository.create_template(user["tenant_id"], payload))


@router.put("/templates/{template_id}")
async def update_template(template_id: int, payload: TemplateWrite, user=Depends(get_current_user)):
    return success(await policy_service.update_template(user["tenant_id"], template_id, payload))


@router.delete("/templates/{template_id}")
async def delete_template(template_id: int, user=Depends(get_current_user)):
    await policy_service.delete_template(user["tenant_id"], template_id)
    return success({"message": "消息模板已删除"})


@router.put("/templates/{template_id}/default")
async def default_template(template_id: int, user=Depends(get_current_user)):
    return success(await policy_service.default_template(user["tenant_id"], template_id))


@router.post("/templates/preview")
async def preview_template(payload: TemplatePreview, user=Depends(get_current_user)):
    return success(await policy_service.preview(user["tenant_id"], payload))


@router.get("/media")
async def media(user=Depends(get_current_user)):
    return success(await policy_repository.media(user["tenant_id"]))


@router.put("/media")
async def save_media(payload: MediaPolicyWrite, user=Depends(get_current_user)):
    return success(await policy_repository.save_media(user["tenant_id"], payload))


@router.post("/media/test")
async def test_media(payload: MediaPolicyTest, user=Depends(get_current_user)):
    return success(await policy_service.test_media(user["tenant_id"], payload))


@router.get("/translation")
async def translation(user=Depends(get_current_user)):
    return success(await policy_repository.translation(user["tenant_id"]) or {
        "enabled": False, "api_key": "", "base_url": "https://api.deepseek.com/v1", "model": "deepseek-chat"
    })


@router.put("/translation")
async def save_translation(payload: TranslationPolicyWrite, user=Depends(get_current_user)):
    return success(await policy_repository.save_translation(user["tenant_id"], payload))
