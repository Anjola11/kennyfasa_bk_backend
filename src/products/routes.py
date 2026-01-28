from fastapi import APIRouter, Depends, Request, Response, status
from src.utils.auth import get_current_user
from src.products.schemas import (
    ProductCreateInput, ProductResponse,ProductListResponse,
    UpdateProductInput,
)
from src.products.services import ProductServices
from sqlmodel.ext.asyncio.session import AsyncSession
from src.db.main import get_Session
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List
from src.utils.limiter import limiter
import uuid

product_router = APIRouter()
product_services = ProductServices()
security = HTTPBearer(auto_error=False)


@product_router.post("/", response_model=ProductResponse, status_code=status.HTTP_200_OK)
@limiter.limit("5/minute")
async def create_product(
    request: Request,
    response: Response,
    product: ProductCreateInput, 
    session: AsyncSession = Depends(get_Session),
    user_details: dict = Depends(get_current_user)
):
    user_id = user_details.get("user_id")

    new_product = await product_services.create_product(product, session, user_id)

    return {
        "success": True,
        "message": "product created successfully",
        "data": new_product
    }

@product_router.get("/", response_model=ProductListResponse, status_code=status.HTTP_200_OK)
@limiter.limit("5/minute")
async def get_all_product(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_Session),
    user_details: dict = Depends(get_current_user)
):
    user_id = user_details.get("user_id")

    products = await product_services.get_all_products(session, user_id)

    return {
        "success": True,
        "message": "products fetched successfully",
        "data": products
    }


@product_router.get("/{id}", response_model= ProductResponse, status_code=status.HTTP_200_OK)
@limiter.limit("5/minute")
async def get_product(
    request: Request,
    response: Response,
    id: uuid.UUID,
    session: AsyncSession = Depends(get_Session),
    user_details: dict = Depends(get_current_user)
):
    user_id = user_details.get("user_id")

    product = await product_services.get_product_by_id(id, session, user_id)

    return {
        "success": True,
        "message": "product fetched successfully",
        "data": product
    }


@product_router.patch("/{id}", response_model=ProductResponse, status_code=status.HTTP_200_OK)
@limiter.limit("5/minute")
async def update_product(
    request: Request,
    response: Response,
    id: uuid.UUID,
    update_data: UpdateProductInput, 
    session: AsyncSession = Depends(get_Session),
    user_details: dict = Depends(get_current_user)
):
    user_id = user_details.get("user_id")

    product = await product_services.update_product(id, update_data, session, user_id)

    return {
        "success": True,
        "message": "product updated successfully",
        "data": product
    }


@product_router.delete("/{id}", status_code=status.HTTP_200_OK)
@limiter.limit("5/minute")
async def delete_product(
    request: Request,
    response: Response,
    id: uuid.UUID,
    session: AsyncSession = Depends(get_Session),
    user_details: dict = Depends(get_current_user)
):
    user_id = user_details.get("user_id")

    await product_services.delete_product(id, session, user_id)
    
    return {
        "success": True,
        "message": "product deleted successfully",
        "data": {}
    }  