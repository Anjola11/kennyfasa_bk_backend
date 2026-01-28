from pydantic import BaseModel
import uuid
from decimal import Decimal
from src.sales.models import SaleStatus
from datetime import datetime
from typing import Optional, List
from src.payments.models import PaymentType

class Sale(BaseModel):
    id: uuid.UUID 
    customer_id: uuid.UUID 
    total_amount: Decimal
    amount_paid: Decimal
    payment_type: Optional[PaymentType] = None
    status: SaleStatus
    items: Optional[List["SaleItem"]] = []
    created_at: datetime

class SaleInput(BaseModel):
    customer_id: uuid.UUID 
    amount_paid: Decimal
    payment_type: Optional[PaymentType] = None
    items: Optional[List["SaleItemInput"]] = []


class SaleItem(BaseModel):
    id: uuid.UUID 
    sale_id: uuid.UUID 
    product_id: uuid.UUID  
    quantity: int 
    unit_price: Decimal 
    total: Decimal

class SaleItemInput(BaseModel):
    product_id: uuid.UUID  
    quantity: int 
    size_id: Optional[uuid.UUID] = None


class UpdateSaleInput(BaseModel):
    amount_paid: Decimal


class SaleResponse(BaseModel):
    success: bool
    message: str
    data: Sale


class SaleListResponse(BaseModel):
    success: bool
    message: str
    data: List[Sale]