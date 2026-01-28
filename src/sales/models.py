from sqlmodel import SQLModel, Field, Relationship, Column
from typing import List, Optional
from decimal import Decimal
import uuid
import sqlalchemy.dialects.postgresql as pg
from datetime import datetime, timezone
from enum import Enum
from src.payments.models import PaymentType
from src.payments.models import SalePaymentLink

def utc_now():
    return datetime.now(timezone.utc)

class SaleStatus(str, Enum):
    UNPAID = "unpaid"
    PARTIALLY_PAID = "partially_paid"
    FULLY_PAID = "fully_paid"



class Sale(SQLModel, table=True):
    __tablename__ = "sales"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    customer_id: uuid.UUID = Field(foreign_key="customers.id", index=True)
    user_id: uuid.UUID = Field(index=True)
    
    total_amount: Decimal = Field(default=Decimal("0.00"), decimal_places=2)
    amount_paid: Decimal = Field(default=Decimal("0.00"), decimal_places=2)
    credit_applied: Decimal = Field(default=Decimal("0.00"), decimal_places=2)  # Credit used at time of sale
    payment_type: Optional[PaymentType] = Field(default=None)
    status: SaleStatus = Field(default=SaleStatus.UNPAID, index=True)
     
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(pg.TIMESTAMP(timezone=True))
    )

    # Relationships
    items: List["SaleItem"] = Relationship(back_populates="sale", sa_relationship_kwargs={"cascade": "all, delete-orphan"})

    payments: List["Payment"] = Relationship(back_populates="sales", link_model=SalePaymentLink)

class SaleItem(SQLModel, table=True):
    __tablename__ = "sale_items"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    sale_id: uuid.UUID = Field(foreign_key="sales.id")
    product_id: uuid.UUID = Field(foreign_key="products.id")
    size_id: Optional[uuid.UUID] = Field(default=None, foreign_key="product_sizes.id")
    quantity: int = Field(gt=0)
    unit_price: Decimal = Field(decimal_places=2) # Captured snapshot
    total: Decimal = Field(decimal_places=2)      # quantity * unit_price

    sale: Sale = Relationship(back_populates="items")