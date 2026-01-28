from fastapi import FastAPI, HTTPException, Request, status
from contextlib import asynccontextmanager
from src.db.main import init_db
from src.db.redis import redis_client, check_redis_connection

from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from src.auth.routes import authRouter
from src.customers.routes import customer_router
from src.sales.routes import sale_router
from src.products.routes import product_router
from src.payments.routes import payment_router
from src.analytics.routes import analytics_router
from src.utils.limiter import limiter




@asynccontextmanager
async def lifespan(app: FastAPI):
    print("\n---Server Started---\n")
    
    # 1. Initialize Postgres
    await init_db()
    
    # 2. Check Redis Connection
    await check_redis_connection()

    yield
    
    # 3. Clean up Redis connections on shutdown
    print("---Closing Redis Connection---")
    if redis_client:
        await redis_client.close()
    print("---Server Closed---")

app = FastAPI(
    title="KennyFasa Bookkeeping API",
    description="the API for the bookkeeping software of KennyFasa",
    lifespan = lifespan
)

# Required for SlowAPI to function correctly on routes
app.state.limiter = limiter

from fastapi.middleware.cors import CORSMiddleware

origins = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
    "https://kennyfasa-bk-frontend.vercel.app",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def health_check():
    return{
        "status": "Success",
        "message": "Server Working"
    }

@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.detail,
            "data": None
        }
    )

def format_validation_errors(errors):
    formatted = []
    for err in errors:
        # Skip the first element if it's "body", "query", etc.
        loc = err["loc"]
        field = ".".join(str(l) for l in loc[1:]) if len(loc) > 1 else str(loc[0])
        formatted.append({
            "field": field,
            "message": err["msg"]
        })
    return formatted

@app.exception_handler(RequestValidationError)
async def custom_validation_exception_handler(request:Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={
            "success": False,
            "message": "Validation error",
            "errors": format_validation_errors(exc.errors()),
            "data": None
        }
    )

# Register all routers
app.include_router(authRouter, prefix="/api/auth", tags=["Authentication"])
app.include_router(customer_router, prefix="/api/customers", tags=["Customers"])
app.include_router(product_router, prefix="/api/products", tags=["Products"])
app.include_router(sale_router, prefix="/api/sales", tags=["Sales"])
app.include_router(payment_router, prefix="/api/payments", tags=["Payments"])
app.include_router(analytics_router, prefix="/api/analytics", tags=["Analytics"])
