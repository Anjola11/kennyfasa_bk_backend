from sqlalchemy.ext.asyncio import create_async_engine
from src.config import Config
from sqlmodel import SQLModel
from sqlalchemy.orm import sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession

engine = create_async_engine(
    url=Config.DATABASE_URL,
    echo=False, 
)

async def init_db():
    async with engine.begin() as conn:
        # Import all models here to ensure they are registered on SQLModel.metadata
        # (Otherwise SQLModel.metadata.create_all may create only a subset of tables.)
        from src.auth import models as _auth_models 
        from src.customers import models as _customer_models 
        from src.products import models as _product_models 
        from src.sales import models as _sale_models 
        from src.payments import models as _payment_models 
        await conn.run_sync(SQLModel.metadata.create_all)

# Session factory configured for async operations
async_session_maker = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

async def get_Session():
    async with async_session_maker() as session:
        yield session
