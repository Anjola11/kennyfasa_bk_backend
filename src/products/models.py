

from sqlmodel import SQLModel, Field, Column, Relationship
import uuid
from datetime import datetime, timezone
import sqlalchemy.dialects.postgresql as pg
from enum import Enum
from decimal import Decimal
from typing import List


def utc_now():
   
    return datetime.now(timezone.utc)

class Category(str, Enum):
    PRINTING = "printing"
    MATERIALS = "materials"
    BANNER = "banner"
    


class Product(SQLModel, table=True):
    __tablename__ = "products"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)                                  
    name:  str 
    user_id: uuid.UUID = Field(index=True)
    base_price: Decimal = Field(gt=0.0, decimal_places=2)
    category: Category
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(pg.TIMESTAMP(timezone=True))
    )

    ##relationship
    sizes:  List["ProductSizes"] = Relationship(
    back_populates="product",
    sa_relationship_kwargs={
        "cascade": "all, delete-orphan"
    }
    ) 

class ProductSizes(SQLModel, table=True):
    __tablename__ = "product_sizes"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    size: str  # e.g., "A4", "2x4ft"
    price: Decimal = Field(gt=0.0, decimal_places=2)
    product_id: uuid.UUID = Field(foreign_key="products.id", index=True)

    product: Product = Relationship(back_populates="sizes")
