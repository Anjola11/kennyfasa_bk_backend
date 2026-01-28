from sqlmodel import SQLModel, Field, Column
import uuid
from decimal import Decimal
import sqlalchemy.dialects.postgresql as pg
from datetime import datetime, timezone

def utc_now():
    return datetime.now(timezone.utc)

class Customer(SQLModel, table=True):
    __tablename__ = "customers"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(index=True)
    name: str = Field(index=True)
    
    # credit_balance: Money the customer has overpaid (pre-paid)
    credit_balance: Decimal = Field(default=Decimal("0.00"), decimal_places=2)
    
    # total_debt: Total amount the customer owes across all sales
    total_debt: Decimal = Field(default=Decimal("0.00"), decimal_places=2)
    
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(pg.TIMESTAMP(timezone=True))
    )