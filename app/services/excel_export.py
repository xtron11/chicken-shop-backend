import io
from datetime import date

import openpyxl
from openpyxl.styles import Font
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order


async def export_orders_to_excel(
    session: AsyncSession, date_from: date | None = None, date_to: date | None = None
) -> io.BytesIO:
    query = select(Order).order_by(Order.delivery_date, Order.delivery_time)
    if date_from:
        query = query.where(Order.delivery_date >= date_from)
    if date_to:
        query = query.where(Order.delivery_date <= date_to)

    result = await session.execute(query)
    orders = result.scalars().all()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Заказы"

    headers = [
        "ID", "Клиент", "Телефон", "Адрес", "Дата доставки", "Время доставки",
        "Статус", "Состав заказа", "Сумма", "Создан",
    ]
    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True)

    for order in orders:
        items_str = "; ".join(f"{i.product_name} x{i.quantity}" for i in order.items)
        ws.append([
            order.id,
            order.customer_name,
            order.customer_phone,
            order.delivery_address,
            order.delivery_date.isoformat(),
            order.delivery_time.strftime("%H:%M"),
            order.status.value,
            items_str,
            float(order.total_amount),
            order.created_at.strftime("%Y-%m-%d %H:%M") if order.created_at else "",
        ])

    # Автоширина колонок (примерная)
    for col in ws.columns:
        max_len = max((len(str(c.value)) for c in col if c.value is not None), default=10)
        ws.column_dimensions[col[0].column_letter].width = min(max_len + 2, 50)

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer
