import uuid
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from price_service.models.price import Price
from price_service.database import get_db

router = APIRouter()


@router.get("/prices")
async def list_prices(
    product_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(Price)
    if product_id:
        query = query.where(Price.product_id == product_id)
    result = await db.scalars(query)
    return result.all()
