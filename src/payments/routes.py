from fastapi import APIRouter, Depends, Request, Response, status
from src.utils.auth import get_current_user
from src.payments.schemas import (
    PaymentInput, PaymentResponse, PaymentListResponse,
)
from src.payments.services import PaymentServices
from sqlmodel.ext.asyncio.session import AsyncSession
from src.db.main import get_Session
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from src.utils.limiter import limiter
import uuid


payment_router = APIRouter()
payment_services = PaymentServices()
security = HTTPBearer(auto_error=False)


@payment_router.post("/", response_model=PaymentResponse, status_code=status.HTTP_200_OK)
@limiter.limit("5/minute")
async def add_payment(
    request: Request,
    response: Response,
    payment: PaymentInput, 
    session: AsyncSession = Depends(get_Session),
    user_details: dict = Depends(get_current_user)
):
    user_id = user_details.get("user_id")

    new_payment = await payment_services.add_payment(payment, session, user_id)

    return {
        "success": True,
        "message": "payment added successfully",
        "data": new_payment
    }


@payment_router.get("/", response_model=PaymentListResponse, status_code=status.HTTP_200_OK)
@limiter.limit("5/minute")
async def get_all_payments(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_Session),
    user_details: dict = Depends(get_current_user)
):
    user_id = user_details.get("user_id")

    payments = await payment_services.get_all_payments(session, user_id)

    return {
        "success": True,
        "message": "payments fetched successfully",
        "data": payments
    }


@payment_router.get("/{id}", response_model=PaymentResponse, status_code=status.HTTP_200_OK)
@limiter.limit("5/minute")
async def get_payment(
    request: Request,
    response: Response,
    id: uuid.UUID,
    session: AsyncSession = Depends(get_Session),
    user_details: dict = Depends(get_current_user)
):
    user_id = user_details.get("user_id")

    payment = await payment_services.get_payment_by_id(id, session, user_id)

    return {
        "success": True,
        "message": "payment fetched successfully",
        "data": payment
    }


@payment_router.get("/customer/{customer_id}", response_model=PaymentListResponse, status_code=status.HTTP_200_OK)
@limiter.limit("5/minute")
async def get_customer_payments(
    request: Request,
    response: Response,
    customer_id: uuid.UUID,
    session: AsyncSession = Depends(get_Session),
    user_details: dict = Depends(get_current_user)
):
    user_id = user_details.get("user_id")

    payments = await payment_services.get_customer_payments_history(customer_id, session, user_id)

    return {
        "success": True,
        "message": "customer payment history fetched successfully",
        "data": payments
    }
