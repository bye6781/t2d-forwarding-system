"""
钉钉机器人管理路由
"""
import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.core.database import database
from app.core.dependencies import get_current_user
from app.core.tenant_context import TenantContext
from app.services.dingtalk_service import dingtalk_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/dingtalk", tags=["DingTalk"])


class CreateBotRequest(BaseModel):
    bot_id: str
    name: str
    webhook: str
    secret: str = ""


class UpdateBotRequest(BaseModel):
    name: Optional[str] = None
    webhook: Optional[str] = None
    secret: Optional[str] = None
    enabled: Optional[bool] = None


class TestSendRequest(BaseModel):
    bot_id: str
    message: str = "T2D SaaS 测试消息 ✅"


@router.get("/bots")
async def list_bots(user: dict = Depends(get_current_user)):
    tenant_id = TenantContext.get()
    bots = await database.get_dingtalk_bots(tenant_id)
    return {"success": True, "data": bots}


@router.post("/bots")
async def create_bot(req: CreateBotRequest, user: dict = Depends(get_current_user)):
    tenant_id = TenantContext.get()

    from app.services.quota_service import quota_service
    existing = await database.get_dingtalk_bots(tenant_id)
    allowed = await quota_service.check_resource_limit(tenant_id, "bot", len(existing))
    if not allowed:
        raise HTTPException(status_code=403, detail="钉钉机器人数量已达套餐上限，请升级套餐")

    bot_db_id = await database.create_dingtalk_bot(
        tenant_id=tenant_id,
        bot_id=req.bot_id,
        name=req.name,
        webhook=req.webhook,
        secret=req.secret,
    )
    return {"success": True, "data": {"id": bot_db_id}}


@router.put("/bots/{bot_id}")
async def update_bot(bot_id: str, req: UpdateBotRequest, user: dict = Depends(get_current_user)):
    tenant_id = TenantContext.get()

    bot = await database.get_dingtalk_bot(bot_id, tenant_id)
    if not bot:
        raise HTTPException(status_code=404, detail="机器人不存在")

    updates = {k: v for k, v in req.dict().items() if v is not None}
    if updates:
        await database.update_dingtalk_bot(tenant_id, bot_id, **updates)

    return {"success": True, "message": "已更新"}


@router.delete("/bots/{bot_id}")
async def delete_bot(bot_id: str, user: dict = Depends(get_current_user)):
    tenant_id = TenantContext.get()

    bot = await database.get_dingtalk_bot(bot_id, tenant_id)
    if not bot:
        raise HTTPException(status_code=404, detail="机器人不存在")

    await database.delete_dingtalk_bot(bot_id, tenant_id)
    return {"success": True, "message": "已删除"}


@router.post("/bots/test")
async def test_bot(req: TestSendRequest, user: dict = Depends(get_current_user)):
    tenant_id = TenantContext.get()

    bot = await database.get_dingtalk_bot(req.bot_id, tenant_id)
    if not bot:
        raise HTTPException(status_code=404, detail="机器人不存在")

    result = await dingtalk_service.send_text(
        webhook=bot["webhook"],
        text=req.message,
        secret=bot.get("secret", ""),
        bot_id=req.bot_id,
    )
    return {"success": result.get("errcode") == 0, "result": result}
