import logging
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from app.core.config import settings
from app.core.database import async_session_maker
from app.models.order import Order, OrderStatus

logger = logging.getLogger(__name__)


async def cancel_stale_pending_orders() -> None:
    """Отменяет заказы, которые висят в pending_payment дольше PENDING_ORDER_TTL_MINUTES."""
    cutoff = datetime.now() - timedelta(minutes=settings.PENDING_ORDER_TTL_MINUTES)
    async with async_session_maker() as session:
        result = await session.execute(
            select(Order).where(
                Order.status == OrderStatus.PENDING_PAYMENT,
                Order.created_at < cutoff,
            )
        )
        stale_orders = result.scalars().all()
        for order in stale_orders:
            order.status = OrderStatus.CANCELLED
            logger.info("Отменён просроченный неоплаченный заказ #%s", order.id)

        if stale_orders:
            await session.commit()


def create_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()
    scheduler.add_job(cancel_stale_pending_orders, "interval", minutes=5, id="cancel_stale_orders")
    return scheduler
