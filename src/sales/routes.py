from fastapi import APIRouter, Depends, Request, Response, status
from src.utils.auth import get_current_user
from src.sales.schemas import (
    SaleInput, SaleResponse, SaleListResponse,
    UpdateSaleInput,
)
from src.sales.services import SaleServices
from sqlmodel.ext.asyncio.session import AsyncSession
from src.db.main import get_Session
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List
from src.utils.limiter import limiter
import uuid


sale_router = APIRouter()
sale_services = SaleServices()
security = HTTPBearer(auto_error=False)


@sale_router.post("/", response_model=SaleResponse, status_code=status.HTTP_200_OK)
@limiter.limit("5/minute")
async def create_sale(
    request: Request,
    response: Response,
    sale: SaleInput, 
    session: AsyncSession = Depends(get_Session),
    user_details: dict = Depends(get_current_user)
):
    user_id = user_details.get("user_id")

    new_sale = await sale_services.create_sale(sale, session, user_id)

    return {
        "success": True,
        "message": "sale created successfully",
        "data": new_sale
    }


@sale_router.get("/", response_model=SaleListResponse, status_code=status.HTTP_200_OK)
@limiter.limit("5/minute")
async def get_all_sales(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_Session),
    user_details: dict = Depends(get_current_user)
):
    user_id = user_details.get("user_id")

    sales = await sale_services.get_all_sales(session, user_id)

    return {
        "success": True,
        "message": "sales fetched successfully",
        "data": sales
    }


@sale_router.get("/{id}", response_model=SaleResponse, status_code=status.HTTP_200_OK)
@limiter.limit("5/minute")
async def get_sale(
    request: Request,
    response: Response,
    id: uuid.UUID,
    session: AsyncSession = Depends(get_Session),
    user_details: dict = Depends(get_current_user)
):
    user_id = user_details.get("user_id")

    sale = await sale_services.get_sale_by_id(id, session, user_id)

    return {
        "success": True,
        "message": "sale fetched successfully",
        "data": sale
    }

