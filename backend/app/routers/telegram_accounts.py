"""
Telegram 账号管理路由
"""
import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.core.database import database
from app.core.dependencies import get_current_user
from app.core.tenant_context import TenantContext
from app.services.telegram_service import telegram_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/telegram", tags=["Telegram"])


class CreateAccountRequest(BaseModel):
    name: str = "default"
    api_id: int
    api_hash: str
    phone: str


class VerifyCodeRequest(BaseModel):
    account_id: int
    code: str
    password: Optional[str] = None


class GetDialogsRequest(BaseModel):
    account_id: int


@router.get("/accounts")
async def list_accounts(user: dict = Depends(get_current_user)):
    tenant_id = TenantContext.get()
    accounts = await database.get_tg_accounts(tenant_id)
    for acc in accounts:
        acc["connected"] = telegram_service.is_connected(tenant_id, acc["id"])
    return {"success": True, "data": accounts}


@router.post("/accounts")
async def create_account(req: CreateAccountRequest, user: dict = Depends(get_current_user)):
    tenant_id = TenantContext.get()

    # 检查资源配额
    from app.services.quota_service import quota_service
    existing = await database.get_tg_accounts(tenant_id)
    allowed = await quota_service.check_resource_limit(tenant_id, "telegram_account", len(existing))
    if not allowed:
        raise HTTPException(status_code=403, detail="TG 账号数量已达套餐上限，请升级套餐")

    account_id = await database.create_tg_account(
        tenant_id=tenant_id,
        name=req.name,
        api_id=req.api_id,
        api_hash=req.api_hash,
        phone=req.phone,
    )
    return {"success": True, "data": {"id": account_id}}


@router.post("/accounts/send-code")
async def send_code(data: dict, user: dict = Depends(get_current_user)):
    tenant_id = TenantContext.get()
    account_id = data.get("account_id")

    account = await database.get_tg_account(account_id, tenant_id)
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")

    result = await telegram_service.send_code(
        tenant_id=tenant_id,
        account_db_id=account_id,
        api_id=account["api_id"],
        api_hash=account["api_hash"],
        phone=account["phone"],
    )
    return result


@router.post("/accounts/connect")
async def connect_account(req: VerifyCodeRequest, user: dict = Depends(get_current_user)):
    tenant_id = TenantContext.get()

    account = await database.get_tg_account(req.account_id, tenant_id)
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")

    try:
        result = await telegram_service.verify_code(
            tenant_id=tenant_id,
            account_db_id=req.account_id,
            api_id=account["api_id"],
            api_hash=account["api_hash"],
            phone=account["phone"],
            code=req.code,
            password=req.password,
        )
        if result["success"]:
            await database.update_tg_account_status(req.account_id, tenant_id, "connected", True)
            return {"success": True, "message": "连接成功"}
        else:
            return {"success": False, "message": result.get("error", "验证失败")}
    except Exception as e:
        logger.error(f"TG connect error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/accounts/disconnect")
async def disconnect_account(data: dict, user: dict = Depends(get_current_user)):
    tenant_id = TenantContext.get()
    account_id = data.get("account_id")

    await telegram_service.disconnect_account(tenant_id, account_id)
    await database.update_tg_account_status(account_id, tenant_id, "disconnected", False)
    return {"success": True, "message": "已断开"}


@router.delete("/accounts/{account_id}")
async def delete_account(account_id: int, user: dict = Depends(get_current_user)):
    tenant_id = TenantContext.get()

    account = await database.get_tg_account(account_id, tenant_id)
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")

    await telegram_service.disconnect_account(tenant_id, account_id)
    await database.delete_tg_account(account_id, tenant_id)
    return {"success": True, "message": "已删除"}


@router.post("/accounts/dialogs")
async def get_dialogs(req: GetDialogsRequest, user: dict = Depends(get_current_user)):
    tenant_id = TenantContext.get()

    account = await database.get_tg_account(req.account_id, tenant_id)
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")

    dialogs = await telegram_service.get_dialogs(tenant_id, req.account_id)
    return {"success": True, "data": dialogs}
