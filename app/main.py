from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqladmin import Admin
from starlette.middleware.sessions import SessionMiddleware

from app.admin.auth import AdminAuth
from app.admin.views import CustomerAdmin, OrderAdmin, OrderItemAdmin, ProductAdmin, admin_router
from app.api import delivery, orders, payments, products
from app.core.config import settings
from app.core.database import engine
from app.services.scheduler import create_scheduler

scheduler = create_scheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.start()
    yield
    scheduler.shutdown()


app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # на проде сузить до домена фронтенда
    allow_methods=["*"],
    allow_headers=["*"],
)
# нужен для сессий SQLAdmin (логин админа)
app.add_middleware(SessionMiddleware, secret_key=settings.ADMIN_SECRET_KEY)

# --- публичные роуты ---
app.include_router(products.router)
app.include_router(delivery.router)
app.include_router(orders.router)
app.include_router(payments.router)
app.include_router(admin_router)

# --- админ-панель ---
admin = Admin(app, engine, authentication_backend=AdminAuth(secret_key=settings.ADMIN_SECRET_KEY))
admin.add_view(ProductAdmin)
admin.add_view(OrderAdmin)
admin.add_view(OrderItemAdmin)
admin.add_view(CustomerAdmin)


@app.get("/health")
async def health_check():
    return {"status": "ok"}
