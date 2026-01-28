from src.customers.schemas import CustomerCreate, CustomerUpdate
from sqlmodel.ext.asyncio.session import AsyncSession
from src.customers.models import Customer
from src.auth.models import User
from sqlmodel import select
from fastapi import HTTPException, status
from sqlalchemy.exc import DatabaseError
import uuid
from src.auth.services import AuthServices

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
            
            return new_customer
        except Exception as e:
            # If anything fails, undo all changes to keep the data consistent
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
        
        except DatabaseError:
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
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Customer not found"
                )

            return customer
        
        except DatabaseError:
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
            return customer
        
        except DatabaseError:
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
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Customer not found"
                )

            await session.delete(customer)
            await session.commit()
            return True
        
        except DatabaseError:
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="internal server error"
            )
