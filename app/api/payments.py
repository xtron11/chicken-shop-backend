import json
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models.order import Order, OrderStatus
from app.schemas.order import PaymentInitOut
from app.services.payment_service import get_payment_provider
from app.services.telegram_service import send_order_notification

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/payments", tags=["payments"])


class PaymentInitRequest(BaseModel):
    order_id: int


@router.post("/init", response_model=PaymentInitOut)
async def init_payment(payload: PaymentInitRequest, session: AsyncSession = Depends(get_session)):
    order = await session.get(Order, payload.order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    if order.status != OrderStatus.PENDING_PAYMENT:
        raise HTTPException(status_code=400, detail="Заказ уже оплачен или отменён")

    provider = get_payment_provider()
    result = await provider.init_payment(order)

    order.payment_id = result.payment_id
    await session.commit()

    return PaymentInitOut(order_id=order.id, payment_url=result.payment_url, payment_id=result.payment_id)


@router.post("/webhook")
async def payment_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
):
    """Вебхук от платёжного провайдера.

    ВАЖНО:
    - Формат payload и заголовков зависит от конкретного провайдера —
      адаптировать под его документацию.
    - Именно здесь, и только здесь, заказ переводится в статус paid.
      Не доверяйте статусу оплаты, пришедшему от фронтенда/редиректа.
    """
    raw_body = await request.body()
    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Некорректный payload")

    provider = get_payment_provider()
    try:
        webhook_result = provider.verify_and_parse_webhook(dict(request.headers), raw_body, payload)
    except ValueError as exc:
        logger.warning("Отклонён вебхук с неверной подписью: %s", exc)
        raise HTTPException(status_code=400, detail="Неверная подпись") from exc

    order = await session.get(Order, webhook_result.order_id)
    if not order:
        logger.warning("Вебхук для несуществующего заказа #%s", webhook_result.order_id)
        raise HTTPException(status_code=404, detail="Заказ не найден")

    # Идемпотентность: если заказ уже оплачен — просто отвечаем 200, повторно ничего не делаем
    if order.status == OrderStatus.PAID:
        return {"status": "already_processed"}

    if webhook_result.success:
        order.status = OrderStatus.PAID
        order.payment_id = webhook_result.payment_id
        await session.commit()
        await session.refresh(order)

        # Уведомление в Telegram отправляем в фоне, чтобы не задерживать ответ вебхуку
        background_tasks.add_task(send_order_notification, order)
    else:
        order.status = OrderStatus.CANCELLED
        await session.commit()

    return {"status": "ok"}
