from sqlmodel import select, func, desc, col
from sqlmodel.ext.asyncio.session import AsyncSession
from src.sales.models import Sale, SaleItem
from src.payments.models import Payment
from src.customers.models import Customer
from src.products.models import Product
from src.analytics.schemas import DashboardSummary, SalesTrendItem, ProductPerformanceItem, TopCustomerItem
from datetime import datetime, timedelta, date
from decimal import Decimal
from typing import List

class AnalyticsServices:

    async def get_dashboard_summary(self, session: AsyncSession, user_id: str) -> DashboardSummary:
        # Company-wide access (for now): do not filter by creator user_id.
        sales_stmt = select(func.sum(Sale.total_amount))
        payments_stmt = select(func.sum(Payment.amount))
        debt_stmt = select(func.sum(Customer.total_debt))
        customers_stmt = select(func.count(Customer.id))

        sales_result = await session.exec(sales_stmt)
        payments_result = await session.exec(payments_stmt)
        debt_result = await session.exec(debt_stmt)
        customers_result = await session.exec(customers_stmt)

        return DashboardSummary(
            total_revenue=sales_result.first() or Decimal("0.0"),
            total_collected=payments_result.first() or Decimal("0.0"),
            total_debt=debt_result.first() or Decimal("0.0"),
            total_customers=customers_result.first() or 0
        )

    async def get_sales_trend(self, session: AsyncSession, days: int = 30) -> List[SalesTrendItem]:
        """Get daily sales trend for the last N days.
        
        Returns sales amount per day, including days with zero sales.
        """
        # Calculate date range
        end_date = date.today()
        start_date = end_date - timedelta(days=days - 1)
        
        # Query to get sales grouped by date
        # Use func.date() to extract just the date portion from created_at timestamp
        stmt = (
            select(
                func.date(Sale.created_at).label("sale_date"),
                func.sum(Sale.total_amount).label("total")
            )
            .where(func.date(Sale.created_at) >= start_date)
            .where(func.date(Sale.created_at) <= end_date)
            .group_by(func.date(Sale.created_at))
            .order_by(func.date(Sale.created_at))
        )
        
        result = await session.exec(stmt)
        rows = result.all()
        
        # Create a dictionary of date -> sales_amount from query results
        sales_dict = {row.sale_date: row.total for row in rows}
        
        # Fill in all dates in range, including those with zero sales
        trend_data = []
        current_date = start_date
        while current_date <= end_date:
            trend_data.append(
                SalesTrendItem(
                    date=current_date,
                    sales_amount=sales_dict.get(current_date, Decimal("0.0"))
                )
            )
            current_date += timedelta(days=1)
        
        return trend_data


    async def get_product_performance(self, session: AsyncSession, user_id: str, limit: int = 10) -> List[ProductPerformanceItem]:
        stmt = (
            select(Product.name, func.sum(SaleItem.quantity).label("qty"), func.sum(SaleItem.total).label("rev"))
            .join(SaleItem, SaleItem.product_id == Product.id)
            .group_by(Product.name)
            .order_by(desc("qty"))
            .limit(limit)
        )
        
        result = await session.exec(stmt)
        rows = result.all()
        
        return [ProductPerformanceItem(product_name=r.name, quantity_sold=r.qty, total_revenue=r.rev) for r in rows]

    async def get_top_customers(self, session: AsyncSession, user_id: str, limit: int = 10) -> List[TopCustomerItem]:
        # Top customers by total spent
        stmt = (
            select(Customer.name, func.sum(Sale.total_amount).label("rev"), Customer.total_debt)
            .join(Sale, Sale.customer_id == Customer.id)
            .group_by(Customer.id, Customer.name, Customer.total_debt)
            .order_by(desc("rev"))
            .limit(limit)
        )
        
        result = await session.exec(stmt)
        rows = result.all()
        
        return [TopCustomerItem(customer_name=r.name, total_revenue=r.rev, current_debt=r.total_debt) for r in rows]
