from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from price_service.models.product import Product
from price_service.database import get_db

router = APIRouter()


@router.get("/products")
async def list_products(
    db: AsyncSession = Depends(get_db),
):
    result = await db.scalars(select(Product))
    return result.all()
