from fastapi import APIRouter
from app.api.endpoints import monitor

api_router = APIRouter()

# Add monitor endpoints
api_router.include_router(
    monitor.router,
    prefix="/monitor",
    tags=["monitor"]
)

# ... existing code ...
