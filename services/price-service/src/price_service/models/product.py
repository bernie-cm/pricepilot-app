# A product represents a grocery item at a specific store. Two stores can sell the same physical
# product, but they represent separate rows because they have different names and prices.

# The table needs
"""
id (UUID): primary key, generated automatically
name (string): product name as the store displays it
url (string): product page URL, unique per store
store (string): "woolworths" or "coles"
created_at (datetime): when we first saw this product
updated_at (datetime): last time we updated it
"""

import uuid
from datetime import datetime

from sqlalchemy import func, DateTime, Uuid, String
from sqlalchemy.orm import Mapped, mapped_column

from price_service.database import Base  # this imports the declarative base superclass


class Product(Base):
    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str]
    url: Mapped[str] = mapped_column(unique=True)
    store: Mapped[str] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
