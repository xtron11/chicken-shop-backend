from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.models.product import ProductUnit


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    price: Decimal
    unit: ProductUnit
    weight_step: Decimal
    image_url: str | None
    is_active: bool
