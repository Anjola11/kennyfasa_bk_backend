from sqlmodel import select
from fastapi import HTTPException, status
from sqlalchemy.exc import DatabaseError
import uuid
from sqlalchemy.orm import selectinload
from src.payments.models import Payment, SalePaymentLink
from src.payments.schemas import PaymentInput
from src.customers.models import Customer
from src.sales.models import Sale, SaleStatus
from sqlmodel.ext.asyncio.session import AsyncSession
from src.auth.services import AuthServices
from decimal import Decimal

authServices = AuthServices()

class PaymentServices:

    async def add_payment(self, payment_input: PaymentInput, session: AsyncSession, user_id: str):
            await authServices.check_user_exists(user_id, session)

            user_uuid = uuid.UUID(user_id)
            payment_dict = payment_input.model_dump()
            
            # Use with_for_update() to prevent race conditions
            customer_statement = select(Customer).where(Customer.id == payment_dict["customer_id"]).with_for_update()
            customer_result = await session.exec(customer_statement)
            customer = customer_result.first()
            
            if not customer:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, 
                    detail="Customer not found"
                    )

            #Update Global Balances (Seesaw Logic)
            payment_amount = payment_dict["amount"]
            effective_balance = payment_amount + customer.credit_balance

            if customer.total_debt > 0:
                if effective_balance >= customer.total_debt:
                    effective_balance -= customer.total_debt
                    customer.total_debt = Decimal("0.0")
                    customer.credit_balance = effective_balance
                else:
                    customer.total_debt -= effective_balance
                    customer.credit_balance = Decimal("0.0")
            else:
                customer.credit_balance = effective_balance

        
            # Fetch unpaid sales OLDEST first 
            sales_statement = select(Sale).where(
                Sale.customer_id == customer.id, 
                Sale.status != SaleStatus.FULLY_PAID
            ).order_by(Sale.created_at.asc())
            
            unpaid_sales = (await session.exec(sales_statement)).all()
            
            # create the Payment object first to get its ID
            new_payment = Payment(**payment_dict, user_id=user_uuid)
            session.add(new_payment)
            
            await session.flush() 
            amount_to_allocate = payment_amount 

            for sale in unpaid_sales:
                if amount_to_allocate <= 0:
                    break
                    
                sale_debt = sale.total_amount - sale.amount_paid
                
                # Calculate how much of this payment applies to this sale
                applied = min(amount_to_allocate, sale_debt)
                
                # Create the Audit Link
                link = SalePaymentLink(
                    sale_id=sale.id,
                    payment_id=new_payment.id,
                    amount_applied=applied
                )
                session.add(link)

                # Update the Sale record
                sale.amount_paid += applied
                amount_to_allocate -= applied

                if sale.amount_paid >= sale.total_amount:
                    sale.status = SaleStatus.FULLY_PAID
                else:
                    sale.status = SaleStatus.PARTIALLY_PAID

            try:
                await session.commit()
                await session.refresh(new_payment)
                return new_payment
            except Exception:
                await session.rollback()
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                    detail="Failed to add payment"
                    )
    
    async def get_all_payments(self, session: AsyncSession, user_id: str):
        await authServices.check_user_exists(user_id, session)

        statement = select(Payment)

        try:
            result = await session.exec(statement)
            payments = result.all()

            return payments
        
        except DatabaseError:
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="internal server error"
            )
        
    async def get_payment_by_id(self, payment_id: uuid.UUID, session: AsyncSession, user_id: str):
        await authServices.check_user_exists(user_id, session)

        statement = select(Payment).where(Payment.id == payment_id)

        try:
            result = await session.exec(statement)
            payment = result.first()

            if not payment:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Payment not found"
                )

            return payment
        
        except DatabaseError:
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="internal server error"
            )
        
    async def get_customer_payments_history(self, customer_id: uuid.UUID, session: AsyncSession, user_id: str):
        await authServices.check_user_exists(user_id, session)

        # Multi-tenancy: ensure customer belongs to current user
        user_uuid = uuid.UUID(user_id)
        customer = (await session.exec(select(Customer).where(Customer.id == customer_id))).first()

        if not customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="customer not found"
            )
        
        # Filter by user_id for multi-tenancy
        statement = select(Payment).where(Payment.customer_id == customer_id)

        try:
            result = await session.exec(statement)
            payments = result.all()

            if not payments:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Payments not found"
                )

            return payments
        
        except DatabaseError:
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="internal server error"
            )
        
        



        


