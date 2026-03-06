from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from price_service.models.price import Price
from price_service.database import get_db

router = APIRouter()


@router.get("/prices")
async def list_prices(
    db: AsyncSession = Depends(get_db),
    ):
    result = await db.scalars(select(Price))
    return result.all()
