from sqlmodel import SQLModel,Field,Relationship, Column
import uuid
from decimal import Decimal
import sqlalchemy.dialects.postgresql as pg
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

def utc_now():
    return datetime.now(timezone.utc)


class PaymentType(str, Enum):
    TRANSFER = "transfer"
    CASH = "cash"
    CARD = "card"

class SalePaymentLink(SQLModel, table=True):
    __tablename__ = "sale_payment_links"

    sale_id: uuid.UUID = Field(foreign_key="sales.id", primary_key=True)
    payment_id: uuid.UUID = Field(foreign_key="payments.id", primary_key=True)
    amount_applied: Decimal = Field(decimal_places=2) 
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(pg.TIMESTAMP(timezone=True))
    )

class Payment(SQLModel, table=True):
    __tablename__ = "payments"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)             
    customer_id: uuid.UUID = Field(foreign_key="customers.id", index=True)
    user_id: uuid.UUID = Field(index=True)
    amount: Decimal = Field(gt=0, decimal_places=2)
    payment_type: PaymentType
    
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(pg.TIMESTAMP(timezone=True))
    )  

    #relationship
    sales: List["Sale"] = Relationship(back_populates="payments", link_model=SalePaymentLink)
    
