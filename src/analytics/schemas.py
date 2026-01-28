from pydantic import BaseModel
from decimal import Decimal
from datetime import date
from typing import List

class DashboardSummary(BaseModel):
    total_revenue: Decimal
    total_collected: Decimal
    total_debt: Decimal
    total_customers: int

class SalesTrendItem(BaseModel):
    date: date
    sales_amount: Decimal

class ProductPerformanceItem(BaseModel):
    product_name: str
    quantity_sold: int
    total_revenue: Decimal

class TopCustomerItem(BaseModel):
    customer_name: str
    total_revenue: Decimal
    current_debt: Decimal
