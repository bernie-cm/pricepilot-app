import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from price_service.models.product import Product
from price_service.models.price import Price
from price_service.database import get_db

router = APIRouter()


@router.get("/products")
async def list_products(
    db: AsyncSession = Depends(get_db),
):
    query = select(Product)
    result = await db.scalars(query)
    return result.all()


@router.get("/products/{product_id}")
async def get_latest_product_price(product_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    # First get the product
    product = await db.scalar(select(Product).where(Product.id == product_id))
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    # Second, get the latest price for this product
    latest_price = await db.scalar(
        select(Price).where(Price.product_id == product_id).order_by(Price.observed_at.desc()).limit(1)
    )

    return {"product": product, "latest_price": latest_price}
