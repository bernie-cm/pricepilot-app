"""
This table needs
id (UUID): primary key generated automatically
product_id (UUID): foreign key linking to products.id
price (Numeric): tracking price
observed_at (datetime): when the price was obtained
"""

import uuid
from decimal import Decimal
from datetime import datetime

from sqlalchemy import func, DateTime, Uuid, ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from price_service.database import Base

class Price(Base):
    __tablename__ = "prices"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("products.id"))
    price: Mapped[Decimal] = mapped_column(Numeric(precision=10, scale=2))
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())