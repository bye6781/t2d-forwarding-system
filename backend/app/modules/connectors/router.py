from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_user
from app.modules.connectors.schemas import (
    BotCreate, BotTest, BotUpdate, TelegramAccountAction, TelegramAccountCreate,
)
from app.modules.connectors.service import connector_service
from app.shared.responses import success


router = APIRouter(tags=["Connectors"])


@router.get("/telegram/accounts")
async def telegram_accounts(user=Depends(get_current_user)):
    return success(await connector_service.telegram_accounts(user))


@router.post("/telegram/accounts")
async def create_telegram(payload: TelegramAccountCreate, user=Depends(get_current_user)):
    return success(await connector_service.create_telegram(user, payload))


@router.post("/telegram/accounts/{account_id}/{action}")
async def telegram_action(account_id: int, action: str, payload: TelegramAccountAction, user=Depends(get_current_user)):
    return success(await connector_service.telegram_action(user, account_id, action, payload))


@router.delete("/telegram/accounts/{account_id}")
async def delete_telegram(account_id: int, user=Depends(get_current_user)):
    await connector_service.delete_telegram(user, account_id)
    return success({"message": "Telegram 账号已删除"})


@router.get("/dingtalk/bots")
async def bots(user=Depends(get_current_user)):
    return success(await connector_service.bots(user))


@router.post("/dingtalk/bots")
async def create_bot(payload: BotCreate, user=Depends(get_current_user)):
    return success(await connector_service.create_bot(user, payload))


@router.put("/dingtalk/bots/{bot_id}")
async def update_bot(bot_id: int, payload: BotUpdate, user=Depends(get_current_user)):
    return success(await connector_service.update_bot(user, bot_id, payload))


@router.delete("/dingtalk/bots/{bot_id}")
async def delete_bot(bot_id: int, user=Depends(get_current_user)):
    await connector_service.delete_bot(user, bot_id)
    return success({"message": "钉钉机器人已删除"})


@router.post("/dingtalk/bots/{bot_id}/test")
async def test_bot(bot_id: int, payload: BotTest, user=Depends(get_current_user)):
    return success(await connector_service.test_bot(user, bot_id, payload.message))
