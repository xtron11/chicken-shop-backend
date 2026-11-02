from datetime import date, time
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.order import OrderStatus


class OrderItemCreate(BaseModel):
    product_id: int
    quantity: Decimal = Field(gt=0, description="Количество в кг или шт., зависит от unit товара")


class OrderCreate(BaseModel):
    customer_name: str = Field(min_length=2, max_length=255)
    customer_phone: str = Field(min_length=6, max_length=32)
    delivery_address: str = Field(min_length=5)
    delivery_date: date
    delivery_time: time
    comment: str | None = None
    items: list[OrderItemCreate] = Field(min_length=1)

    @field_validator("customer_phone")
    @classmethod
    def phone_digits_only(cls, v: str) -> str:
        cleaned = v.replace(" ", "").replace("-", "")
        if not cleaned.replace("+", "").isdigit():
            raise ValueError("Некорректный формат телефона")
        return cleaned


class OrderItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    product_name: str
    price: Decimal
    quantity: Decimal
    subtotal: Decimal


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_name: str
    customer_phone: str
    delivery_address: str
    delivery_date: date
    delivery_time: time
    status: OrderStatus
    total_amount: Decimal
    comment: str | None
    items: list[OrderItemOut]


class OrderStatusOut(BaseModel):
    id: int
    status: OrderStatus


class PaymentInitOut(BaseModel):
    order_id: int
    payment_url: str
    payment_id: str


class DeliverySlotOut(BaseModel):
    date: date
    time: time
    available: bool
