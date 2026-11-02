"""
Сервис оплаты.

Реализован как простой интерфейс, чтобы конкретного провайдера (Kaspi,
CloudPayments, ЮKassa и т.д.) можно было подключить, не переписывая остальной
код. Сейчас подключена DummyProvider — она ничего не отправляет во внешний
мир и нужна только для локальной разработки/тестов.

Как подключить реального провайдера:
1. Создать класс, унаследованный от PaymentProvider.
2. Реализовать init_payment() — вызов API провайдера, получение ссылки на оплату.
3. Реализовать parse_webhook() — разбор и проверка подписи входящего вебхука.
4. Прописать выбор провайдера в get_payment_provider() по settings.PAYMENT_PROVIDER.
"""

import hashlib
import hmac
import logging
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal

from app.core.config import settings
from app.models.order import Order

logger = logging.getLogger(__name__)


@dataclass
class PaymentInitResult:
    payment_id: str
    payment_url: str


@dataclass
class WebhookResult:
    payment_id: str
    order_id: int
    success: bool
    raw_payload: dict


class PaymentProvider(ABC):
    @abstractmethod
    async def init_payment(self, order: Order) -> PaymentInitResult:
        """Создаёт платёж у провайдера и возвращает ссылку на оплату."""
        raise NotImplementedError

    @abstractmethod
    def verify_and_parse_webhook(self, headers: dict, body: bytes, payload: dict) -> WebhookResult:
        """Проверяет подпись вебхука и возвращает разобранный результат.

        ВАЖНО: если подпись не совпадает — должно бросаться исключение,
        а не молча возвращаться success=False.
        """
        raise NotImplementedError


class DummyProvider(PaymentProvider):
    """Провайдер-заглушка для разработки. НЕ использовать в проде."""

    async def init_payment(self, order: Order) -> PaymentInitResult:
        payment_id = f"dummy_{uuid.uuid4().hex[:12]}"
        # в реальном провайдере тут будет ссылка вида https://pay.provider.kz/...
        payment_url = f"https://example-payment.local/pay/{payment_id}?amount={order.total_amount}"
        logger.info("DummyProvider: создан платёж %s для заказа #%s", payment_id, order.id)
        return PaymentInitResult(payment_id=payment_id, payment_url=payment_url)

    def verify_and_parse_webhook(self, headers: dict, body: bytes, payload: dict) -> WebhookResult:
        # В реальном провайдере здесь HMAC-проверка подписи по секретному ключу.
        # Пример шаблона проверки (адаптировать под конкретного провайдера):
        signature = headers.get("X-Signature", "")
        expected = hmac.new(
            settings.PAYMENT_WEBHOOK_SECRET.encode(), body, hashlib.sha256
        ).hexdigest()
        if settings.PAYMENT_WEBHOOK_SECRET and signature != expected:
            raise ValueError("Неверная подпись вебхука")

        return WebhookResult(
            payment_id=payload["payment_id"],
            order_id=int(payload["order_id"]),
            success=payload.get("status") == "success",
            raw_payload=payload,
        )


def get_payment_provider() -> PaymentProvider:
    if settings.PAYMENT_PROVIDER == "dummy":
        return DummyProvider()
    # elif settings.PAYMENT_PROVIDER == "kaspi":
    #     return KaspiProvider(...)
    # elif settings.PAYMENT_PROVIDER == "cloudpayments":
    #     return CloudPaymentsProvider(...)
    raise NotImplementedError(f"Провайдер {settings.PAYMENT_PROVIDER} не реализован")
