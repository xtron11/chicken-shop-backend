from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, Query

from app.core.config import settings
from app.schemas.order import DeliverySlotOut

router = APIRouter(prefix="/api/delivery-slots", tags=["delivery"])


def _is_slot_valid(slot_dt: datetime) -> bool:
    return slot_dt >= datetime.now() + timedelta(hours=settings.MIN_HOURS_BEFORE_DELIVERY)


@router.get("", response_model=list[DeliverySlotOut])
async def get_delivery_slots(target_date: date = Query(..., description="Дата доставки, YYYY-MM-DD")):
    """Возвращает список слотов на указанную дату с флагом доступности.

    Простая реализация без учёта капасити курьеров: слот доступен, если он
    в рабочем диапазоне часов и не раньше, чем MIN_HOURS_BEFORE_DELIVERY от текущего момента.
    Если нужно ограничивать число заказов на слот — добавить таблицу delivery_slots
    и проверять occupied/max_orders здесь же.
    """
    slots: list[DeliverySlotOut] = []
    current = datetime.combine(target_date, time(hour=settings.WORK_HOUR_FROM))
    end = datetime.combine(target_date, time(hour=settings.WORK_HOUR_TO))
    step = timedelta(minutes=settings.DELIVERY_SLOT_STEP_MINUTES)

    while current < end:
        slots.append(
            DeliverySlotOut(date=target_date, time=current.time(), available=_is_slot_valid(current))
        )
        current += step

    return slots
