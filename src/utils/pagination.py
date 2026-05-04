from sqlmodel import select, desc, asc, func, SQLModel, Field
from pydantic import BaseModel
from enum import Enum
from src.sales.models import Sale
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import TypeVar, Generic, List, Type, Sequence
from sqlalchemy.sql.selectable import Select
from sqlalchemy.exc import DatabaseError


T = TypeVar("T", bound=SQLModel)

class SortEnum(str, Enum):
    ASCENDING = "asc"
    DESCENDING = "desc"

class PaginationParameters(BaseModel):
    page: int = Field(1, ge=1) 
    per_page: int = Field(10, ge=1, le=100)
    order: SortEnum = SortEnum.DESCENDING

class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total_count: int
    page: int
    per_page: int

#work in progress

async def paginate(session: AsyncSession, model: Type[T], base_statement: Select, params: PaginationParameters):
    
    order = desc if params.order == SortEnum.DESCENDING else asc
    query = (
            base_statement
            .limit(params.per_page)
            .offset((params.page - 1) * params.per_page)
            .order_by(order(getattr(model, "created_at", model.id)))
        )
    count_query = select(func.count()).select_from(base_statement.subquery())


    try:
        results = await session.exec(query)
        items = results.all()

        total_count_result = await session.exec(count_query)
        total_count = total_count_result.one()

        return PaginatedResponse(
            items=items,
            total_count=total_count,
            page=params.page,
            per_page=params.per_page
        )


        
    except DatabaseError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="internal server error"
        )