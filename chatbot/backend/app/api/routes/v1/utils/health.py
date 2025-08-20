from fastapi import APIRouter

router = APIRouter()

@router.get("/health-check")
async def health_check():
    return {"status": "healthy", "message": "Backend is running"}