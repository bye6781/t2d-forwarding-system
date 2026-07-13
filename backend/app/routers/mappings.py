"""
转发映射规则管理路由
"""
import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional

from app.core.database import database
from app.core.dependencies import get_current_user
from app.core.tenant_context import TenantContext

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/mappings", tags=["Mappings"])


class CreateMappingRequest(BaseModel):
    source_chat_id: int
    target_bot_ids: List[str]
    translation_enabled: bool = True
    filter_enabled: bool = True
    enabled: bool = True


class UpdateMappingRequest(BaseModel):
    source_chat_id: Optional[int] = None
    target_bot_ids: Optional[List[str]] = None
    translation_enabled: Optional[bool] = None
    filter_enabled: Optional[bool] = None
    enabled: Optional[bool] = None


@router.get("")
async def list_mappings(user: dict = Depends(get_current_user)):
    tenant_id = TenantContext.get()
    mappings = await database.get_mappings(tenant_id)
    return {"success": True, "data": mappings}


@router.post("")
async def create_mapping(req: CreateMappingRequest, user: dict = Depends(get_current_user)):
    tenant_id = TenantContext.get()

    from app.services.quota_service import quota_service
    existing = await database.get_mappings(tenant_id)
    allowed = await quota_service.check_resource_limit(tenant_id, "mapping", len(existing))
    if not allowed:
        raise HTTPException(status_code=403, detail="映射规则数量已达套餐上限，请升级套餐")

    mapping_id = await database.create_mapping(
        tenant_id=tenant_id,
        source_chat_id=req.source_chat_id,
        target_bot_ids=req.target_bot_ids,
        translation_enabled=req.translation_enabled,
        filter_enabled=req.filter_enabled,
        enabled=req.enabled,
    )
    return {"success": True, "data": {"id": mapping_id}}


@router.put("/{mapping_id}")
async def update_mapping(mapping_id: int, req: UpdateMappingRequest, user: dict = Depends(get_current_user)):
    tenant_id = TenantContext.get()
    updates = {k: v for k, v in req.dict().items() if v is not None}
    if updates:
        await database.update_mapping(mapping_id, tenant_id, **updates)
    return {"success": True, "message": "已更新"}


@router.delete("/{mapping_id}")
async def delete_mapping(mapping_id: int, user: dict = Depends(get_current_user)):
    tenant_id = TenantContext.get()
    await database.delete_mapping(mapping_id, tenant_id)
    return {"success": True, "message": "已删除"}
