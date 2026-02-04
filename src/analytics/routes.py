from fastapi import APIRouter, Depends, status
from sqlmodel.ext.asyncio.session import AsyncSession
from src.db.main import get_Session
from src.utils.auth import get_current_user, role_required
from src.analytics.services import AnalyticsServices
from src.analytics.schemas import DashboardSummary, SalesTrendItem, ProductPerformanceItem, TopCustomerItem
from typing import List

analytics_router = APIRouter()
analytics_services = AnalyticsServices()

@analytics_router.get("/summary", response_model=DashboardSummary)
async def get_summary(
    session: AsyncSession = Depends(get_Session),
    current_user: dict = Depends(get_current_user)
):
    """Get high-level business summary metrics."""
    user_id = current_user.get("user_id")
    return await analytics_services.get_dashboard_summary(session, user_id)

@analytics_router.get("/sales-trend", response_model=List[SalesTrendItem])
async def get_sales_trend(
    days: int = 30,
    session: AsyncSession = Depends(get_Session),
    current_user: dict = Depends(get_current_user)
):
    """Get sales revenue trend over a specific number of days."""
    user_id = current_user.get("user_id")
    return await analytics_services.get_sales_trend(session, days)

@analytics_router.get("/product-performance", response_model=List[ProductPerformanceItem])
async def get_product_performance(
    limit: int = 10,
    session: AsyncSession = Depends(get_Session),
    current_user: dict = Depends(get_current_user)
):
    """Get performance metrics for top products."""
    user_id = current_user.get("user_id")
    return await analytics_services.get_product_performance(session, user_id, limit)

@analytics_router.get("/top-customers", response_model=List[TopCustomerItem])
async def get_top_customers(
    limit: int = 10,
    session: AsyncSession = Depends(get_Session),
    current_user: dict = Depends(get_current_user)
):
    """Get lifetime value and debt status of top customers."""
    user_id = current_user.get("user_id")
    return await analytics_services.get_top_customers(session, user_id, limit)
