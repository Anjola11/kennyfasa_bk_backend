from pydantic import BaseModel
from typing import Optional, List
from decimal import Decimal
import uuid
from datetime import datetime

class CustomerCreate(BaseModel):
    name: str

class CustomerUpdate(BaseModel):
    name: Optional[str] = None

class CustomerInfo(BaseModel):
    id: uuid.UUID
    name: str
    credit_balance: Decimal
    total_debt: Decimal
    created_at: datetime

class CustomerResponse(BaseModel):
    success: bool
    message: str
    data: CustomerInfo

class CustomerListResponse(BaseModel):
    success: bool
    message: str
    data: List[CustomerInfo]