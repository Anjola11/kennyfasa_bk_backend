from src.customers.schemas import CustomerCreate, CustomerUpdate
from sqlmodel.ext.asyncio.session import AsyncSession
from src.customers.models import Customer
from src.auth.models import User
from sqlmodel import select
from fastapi import HTTPException, status
from sqlalchemy.exc import DatabaseError
import uuid
from src.auth.services import AuthServices
from decimal import Decimal
from src.utils.logger import logger

authServices = AuthServices()


class CustomerServices():


    async def create_customer(self, customer: CustomerCreate, session: AsyncSession, user_id: str):
        # Verify the user exists in the system before allowing customer creation
        await authServices.check_user_exists(user_id, session)

        # Create new customer
        new_customer = Customer(**customer.model_dump(), user_id=uuid.UUID(user_id))

        session.add(new_customer)

        try:
            # Commit the transaction
            await session.commit()
            
            # Reload the object from the database to ensure we have all generated fields
            await session.refresh(new_customer)
            logger.info(f"Customer created successfully: {new_customer.id} by user {user_id}")
            return new_customer
        except Exception as e:
            # If anything fails, undo all changes to keep the data consistent
            logger.error(f"Failed to create customer by user {user_id}: {str(e)}", exc_info=True)
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail="Failed to create customer"
            )
        
    async def get_all_customers(self, session: AsyncSession, user_id: str):
        statement = select(Customer)

        try:
            result = await session.exec(statement)
            customers = result.all()

            return customers
        
        except DatabaseError as e:
            logger.error(f"Database error while fetching all customers by user {user_id}: {str(e)}", exc_info=True)
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="internal server error"
            )
        
    async def get_customer_by_id(self, customer_id: uuid.UUID, session: AsyncSession, user_id: str):
        statement = select(Customer).where(Customer.id == customer_id)

        try:
            result = await session.exec(statement)
            customer = result.first()

            if not customer:
                logger.warning(f"Customer {customer_id} not found by user {user_id}")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Customer not found"
                )

            return customer
        
        except DatabaseError as e:
            logger.error(f"Database error while fetching customer {customer_id}: {str(e)}", exc_info=True)
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="internal server error"
            )
        
    async def update_customer(self, customer_id: uuid.UUID, update_data: CustomerUpdate, session: AsyncSession, user_id: str):
        await authServices.check_user_exists(user_id, session)

        if update_data.name is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You must provide at least one field to update (name)"
            )

        statement = select(Customer).where(Customer.id == customer_id)

        try:
            result = await session.exec(statement)
            customer = result.first()

            if not customer:
                logger.warning(f"Failed to update: Customer {customer_id} not found")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Customer not found"
                )

            # Convert the input to a dictionary, excluding unset values
            update_dict = update_data.model_dump(exclude_unset=True)

            for key, value in update_dict.items():
                setattr(customer, key, value)

            await session.commit()
            await session.refresh(customer)
            logger.info(f"Customer {customer_id} updated successfully by user {user_id}")
            return customer
        
        except DatabaseError as e:
            logger.error(f"Database error while updating customer {customer_id}: {str(e)}", exc_info=True)
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="internal server error"
            )
        
    async def delete_customer(self, customer_id: uuid.UUID, session: AsyncSession, user_id: str):
        await authServices.check_user_exists(user_id, session)

        statement = select(Customer).where(Customer.id == customer_id)

        try:
            result = await session.exec(statement)
            customer = result.first()

            if not customer:
                logger.warning(f"Failed to delete: Customer {customer_id} not found")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Customer not found"
                )

            await session.delete(customer)
            await session.commit()
            logger.info(f"Customer {customer_id} deleted successfully by user {user_id}")
            return True
        
        except DatabaseError as e:
            logger.error(f"Database error while deleting customer {customer_id}: {str(e)}", exc_info=True)
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="internal server error"
            )

    async def add_initial_debt(self, customer_id: uuid.UUID, amount: Decimal, session: AsyncSession, user_id: str):
        await authServices.check_user_exists(user_id, session)

        if amount <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Debt amount must be greater than zero"
            )

        statement = select(Customer).where(Customer.id == customer_id).with_for_update()

        try:
            result = await session.exec(statement)
            customer = result.first()

            if not customer:
                logger.warning(f"Failed to add debt: Customer {customer_id} not found by user {user_id}")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Customer not found"
                )

            logger.info(f"Adding initial debt of {amount} to customer {customer_id} by user {user_id}")
            if customer.credit_balance > 0:
                logger.info(f"Customer {customer_id} has existing credit balance of {customer.credit_balance}. Offsetting...")
                if customer.credit_balance >= amount:
                    customer.credit_balance -= amount
                else:
                    remaining_debt = amount - customer.credit_balance
                    customer.credit_balance = Decimal("0.0")
                    customer.total_debt += remaining_debt
            else:
                customer.total_debt += amount

            await session.commit()
            await session.refresh(customer)
            logger.info(f"Successfully added initial debt for customer {customer_id}. New debt: {customer.total_debt}, New credit: {customer.credit_balance}")
            return customer
        
        except HTTPException:
            await session.rollback()
            raise
        except DatabaseError as e:
            logger.error(f"Database error while adding debt to customer {customer_id}: {str(e)}", exc_info=True)
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="internal server error"
            )
