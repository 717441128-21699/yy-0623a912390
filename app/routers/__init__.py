from fastapi import APIRouter
from app.routers.formwork import router as formwork_router

api_router = APIRouter()
api_router.include_router(formwork_router)
