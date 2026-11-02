from datetime import datetime, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_session
from app.models.order import Order, OrderItem, OrderStatus
from app.models.product import Product
from app.schemas.order import OrderCreate, OrderOut, OrderStatusOut

router = APIRouter(prefix="/api/orders", tags=["orders"])


@router.post("", response_model=OrderOut, status_code=201)
async def create_order(payload: OrderCreate, session: AsyncSession = Depends(get_session)):
    # 1. Проверка слота доставки (не в прошлом, не раньше MIN_HOURS_BEFORE_DELIVERY)
    delivery_dt = datetime.combine(payload.delivery_date, payload.delivery_time)
    if delivery_dt < datetime.now() + timedelta(hours=settings.MIN_HOURS_BEFORE_DELIVERY):
        raise HTTPException(
            status_code=400,
            detail=f"Доставка возможна не раньше чем через {settings.MIN_HOURS_BEFORE_DELIVERY} ч.",
        )
    if not (settings.WORK_HOUR_FROM <= payload.delivery_time.hour < settings.WORK_HOUR_TO):
        raise HTTPException(status_code=400, detail="Выбранное время вне рабочего диапазона доставки")

    # 2. Подтягиваем товары и считаем сумму на СЕРВЕРЕ (никогда не доверять цене от клиента)
    product_ids = [item.product_id for item in payload.items]
    result = await session.execute(select(Product).where(Product.id.in_(product_ids)))
    products_by_id = {p.id: p for p in result.scalars().all()}

    order_items: list[OrderItem] = []
    total = Decimal("0")

    for item in payload.items:
        product = products_by_id.get(item.product_id)
        if not product or not product.is_active:
            raise HTTPException(status_code=400, detail=f"Товар id={item.product_id} недоступен")

        subtotal = (product.price * item.quantity).quantize(Decimal("0.01"))
        total += subtotal
        order_items.append(
            OrderItem(
                product_id=product.id,
                product_name=product.name,
                price=product.price,
                quantity=item.quantity,
                subtotal=subtotal,
            )
        )

    # 3. Создаём заказ со статусом pending_payment
    order = Order(
        customer_name=payload.customer_name,
        customer_phone=payload.customer_phone,
        delivery_address=payload.delivery_address,
        delivery_date=payload.delivery_date,
        delivery_time=payload.delivery_time,
        comment=payload.comment,
        status=OrderStatus.PENDING_PAYMENT,
        total_amount=total,
        items=order_items,
    )
    session.add(order)
    await session.commit()
    await session.refresh(order)

    return order


@router.get("/{order_id}/status", response_model=OrderStatusOut)
async def get_order_status(order_id: int, session: AsyncSession = Depends(get_session)):
    order = await session.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    return OrderStatusOut(id=order.id, status=order.status)


@router.get("/{order_id}", response_model=OrderOut)
async def get_order(order_id: int, session: AsyncSession = Depends(get_session)):
    order = await session.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    return order
