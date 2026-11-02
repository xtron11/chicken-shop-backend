import logging

import httpx

from app.core.config import settings
from app.models.order import Order

logger = logging.getLogger(__name__)


def _build_order_text(order: Order) -> str:
    items_text = "\n".join(
        f"  • {item.product_name} — {item.quantity} x {item.price} = {item.subtotal} ₸"
        for item in order.items
    )
    return (
        f"🐔 <b>Новый оплаченный заказ #{order.id}</b>\n\n"
        f"👤 Клиент: {order.customer_name}\n"
        f"📞 Телефон: {order.customer_phone}\n"
        f"📍 Адрес: {order.delivery_address}\n"
        f"🗓 Доставка: {order.delivery_date} в {order.delivery_time}\n\n"
        f"Состав заказа:\n{items_text}\n\n"
        f"💰 Итого: {order.total_amount} ₸"
        + (f"\n📝 Комментарий: {order.comment}" if order.comment else "")
    )


async def send_order_notification(order: Order) -> None:
    """Отправляет уведомление о новом оплаченном заказе в Telegram-чат владельца.

    Вызывать ТОЛЬКО после подтверждения оплаты вебхуком, не раньше.
    Ошибки отправки логируются, но не должны ронять обработку заказа.
    """
    if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_CHAT_ID:
        logger.warning("Telegram bot token/chat_id не настроены, уведомление не отправлено")
        return

    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": settings.TELEGRAM_CHAT_ID,
        "text": _build_order_text(order),
        "parse_mode": "HTML",
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
    except httpx.HTTPError:
        logger.exception("Не удалось отправить уведомление в Telegram для заказа #%s", order.id)
