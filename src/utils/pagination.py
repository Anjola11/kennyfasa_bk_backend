from sqlmodel import select, desc, asc, func, SQLModel, Field
from pydantic import BaseModel
from enum import Enum
from src.sales.models import Sale
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import TypeVar, Generic, List, Type, Sequence
from sqlalchemy.sql.selectable import Select


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

# async def pagination(
#         session:AsyncSession,
#         model: Type[T],
#         statement: Select[T],
#         params: PaginationParameters,
#         sort_column: str = "id"):
#     order = desc if params.order == SortEnum.DESCENDING else asc
#     query = (
#         statement
#         .limit(params.per_page)
#         .offset((params.page - 1) * params.per_page)
#         .order_by(order(getattr(model, sort_column)))
#         )
    
#     count_query = select(func.count()).select_from(statement.subquery())
 
#     results = await session.exec(query)
#     items = results.all()
    
#     total_count_result = await session.exec(count_query)
#     total_count = total_count_result.one()

#     return PaginatedResponse(
#         items=items,
#         total_count=total_count,
#         page=params.page,
#         per_page=params.per_page
#     )

