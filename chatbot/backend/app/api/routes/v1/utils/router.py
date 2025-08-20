from fastapi import APIRouter
from .health import router as health_router

router = APIRouter()
router.include_router(health_router, tags=["utils"])