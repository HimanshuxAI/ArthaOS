from fastapi import APIRouter

from app.api.routes import auth, finance

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(finance.router)
