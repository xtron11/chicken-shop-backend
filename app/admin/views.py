from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqladmin import ModelView
from sqladmin.filters import AllUniqueStringValuesFilter, StaticValuesFilter
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models.customer import Customer
from app.models.order import Order, OrderItem, OrderStatus
from app.models.product import Product
from app.services.excel_export import export_orders_to_excel


class ProductAdmin(ModelView, model=Product):
    name = "Товар"
    name_plural = "Товары"
    icon = "fa-solid fa-drumstick-bite"

    column_list = [Product.id, Product.name, Product.price, Product.unit, Product.is_active, Product.stock_qty]
    column_searchable_list = [Product.name]
    column_sortable_list = [Product.id, Product.name, Product.price]
    form_columns = [
        Product.name, Product.description, Product.price, Product.unit,
        Product.weight_step, Product.image_url, Product.is_active, Product.stock_qty,
    ]
    can_export = True


class OrderItemAdmin(ModelView, model=OrderItem):
    name = "Позиция заказа"
    name_plural = "Позиции заказов"
    column_list = [OrderItem.id, OrderItem.order_id, OrderItem.product_name, OrderItem.quantity, OrderItem.subtotal]
    can_create = False
    can_edit = False
    can_delete = False


class OrderAdmin(ModelView, model=Order):
    name = "Заказ"
    name_plural = "Заказы"
    icon = "fa-solid fa-truck"

    column_list = [
        Order.id, Order.customer_name, Order.customer_phone, Order.status,
        Order.delivery_date, Order.delivery_time, Order.total_amount, Order.created_at,
    ]
    column_searchable_list = [Order.customer_name, Order.customer_phone]
    column_sortable_list = [Order.id, Order.delivery_date, Order.created_at, Order.total_amount]
    column_filters = [
        StaticValuesFilter(
            Order.status,
            title="Статус",
            values=[(s.value, s.value) for s in OrderStatus],
        ),
        AllUniqueStringValuesFilter(Order.delivery_date, title="Дата доставки"),
    ]
    column_default_sort = [(Order.created_at, True)]

    # Заказы создаются только с сайта; в админке — просмотр и смена статуса (например, delivered)
    can_create = False
    can_delete = False
    form_columns = [Order.status, Order.comment]


class CustomerAdmin(ModelView, model=Customer):
    name = "Клиент"
    name_plural = "Клиенты"
    column_list = [Customer.id, Customer.name, Customer.phone, Customer.created_at]
    column_searchable_list = [Customer.name, Customer.phone]
    can_create = False


admin_router = APIRouter(prefix="/admin", tags=["admin"])


def _require_admin_session(request: Request) -> None:
    """Переиспользуем ту же сессию, что и SQLAdmin (см. AdminAuth.login)."""
    if not request.session.get("admin_authenticated"):
        raise HTTPException(status_code=401, detail="Требуется авторизация в админ-панели")


@admin_router.get("/orders/export")
async def export_orders(
    request: Request,
    date_from: date | None = None,
    date_to: date | None = None,
    session: AsyncSession = Depends(get_session),
):
    _require_admin_session(request)
    buffer = await export_orders_to_excel(session, date_from, date_to)
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=orders_export.xlsx"},
    )
