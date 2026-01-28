from pydantic import BaseModel
import uuid
from decimal import Decimal
from src.payments.models import PaymentType
from datetime import datetime
from typing import List

class Payment(BaseModel):
    id: uuid.UUID
    customer_id: uuid.UUID 
    amount: Decimal
    payment_type: PaymentType
    created_at: datetime 

class PaymentInput(BaseModel):
    customer_id: uuid.UUID 
    amount: Decimal
    payment_type: PaymentType

class PaymentResponse(BaseModel):
    success: bool
    message: str
    data: Payment

class PaymentListResponse(BaseModel):
    success: bool
    message: str
    data: List[Payment]
