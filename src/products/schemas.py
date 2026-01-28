from pydantic import Field, BaseModel, ConfigDict
import uuid
from src.products.models import Category
from datetime import datetime
from typing import Optional, List
from decimal import Decimal

# Child model first for clean referencing
class ProductSize(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    size: str
    price: Decimal

class Product(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID                             
    name:  str 
    base_price: Decimal      
    category: Category
    sizes: List[ProductSize] = []
    created_at: datetime

class ProductSizeCreate(BaseModel):
    size: str
    price: Decimal = Field(gt=0)

class ProductCreateInput(BaseModel):
    name: str
    base_price: Decimal = Field(gt=0)
    category: Category
    sizes: Optional[List[ProductSizeCreate]] = []

class ProductResponse(BaseModel):
    success: bool
    message: str
    data: Product

class ProductListResponse(BaseModel):
    success: bool
    message: str
    data: List[Product]

class UpdateProductInput(BaseModel):
    name:  Optional[str] = None
    base_price: Optional[Decimal] = Field(default=None, gt=0)
    category: Optional[Category] = None
    sizes: Optional[List[ProductSizeCreate]] = []