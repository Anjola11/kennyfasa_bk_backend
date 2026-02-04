from fastapi import APIRouter, Depends, Request, Response, status
from src.utils.auth import get_current_user
from src.customers.schemas import (
    CustomerCreate, CustomerResponse, CustomerListResponse,
    CustomerUpdate,
)
from src.customers.services import CustomerServices
from sqlmodel.ext.asyncio.session import AsyncSession
from src.db.main import get_Session
from fastapi.security import HTTPBearer
from src.utils.limiter import limiter
import uuid


customer_router = APIRouter()
customer_services = CustomerServices()
security = HTTPBearer(auto_error=False)


@customer_router.post("/", response_model=CustomerResponse, status_code=status.HTTP_200_OK)
@limiter.limit("20/minute")
async def create_customer(
    request: Request,
    response: Response,
    customer: CustomerCreate, 
    session: AsyncSession = Depends(get_Session),
    user_details: dict = Depends(get_current_user)
):
    user_id = user_details.get("user_id")

    new_customer = await customer_services.create_customer(customer, session, user_id)

    return {
        "success": True,
        "message": "customer created successfully",
        "data": new_customer
    }

@customer_router.get("/", response_model=CustomerListResponse, status_code=status.HTTP_200_OK)
@limiter.limit("100/minute")
async def get_all_customer(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_Session),
    user_details: dict = Depends(get_current_user)
):
    user_id = user_details.get("user_id")

    customers = await customer_services.get_all_customers(session, user_id)

    return {
        "success": True,
        "message": "customers fetched successfully",
        "data": customers
    }


@customer_router.get("/{id}", response_model=CustomerResponse, status_code=status.HTTP_200_OK)
@limiter.limit("100/minute")
async def get_customer(
    request: Request,
    response: Response,
    id: uuid.UUID,
    session: AsyncSession = Depends(get_Session),
    user_details: dict = Depends(get_current_user)
):
    user_id = user_details.get("user_id")

    customer = await customer_services.get_customer_by_id(id, session, user_id)

    return {
        "success": True,
        "message": "customer fetched successfully",
        "data": customer
    }


@customer_router.patch("/{id}", response_model=CustomerResponse, status_code=status.HTTP_200_OK)
@limiter.limit("20/minute")
async def update_customer(
    request: Request,
    response: Response,
    id: uuid.UUID,
    update_data: CustomerUpdate, 
    session: AsyncSession = Depends(get_Session),
    user_details: dict = Depends(get_current_user)
):
    user_id = user_details.get("user_id")

    customer = await customer_services.update_customer(id, update_data, session, user_id)

    return {
        "success": True,
        "message": "customer updated successfully",
        "data": customer
    }


@customer_router.delete("/{id}", status_code=status.HTTP_200_OK)
@limiter.limit("20/minute")
async def delete_customer(
    request: Request,
    response: Response,
    id: uuid.UUID,
    session: AsyncSession = Depends(get_Session),
    user_details: dict = Depends(get_current_user)
):
    user_id = user_details.get("user_id")

    await customer_services.delete_customer(id, session, user_id)
    
    return {
        "success": True,
        "message": "customer deleted successfully",
        "data": {}
    }
