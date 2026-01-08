from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 1. Create App
app = FastAPI(title="VMS Controller")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Include Routers
try:
    # Import the 'router' variable from your controller files
    from app.backend.controllers.auth_controller import router as auth_router
    from app.backend.controllers.doorlist_controller import router as door_router
    from app.backend.controllers.visitorlist_controller import router as visitor_router
    from app.backend.controllers.visitorregister_controller import router as register_router

    # Connect them
    app.include_router(auth_router, tags=["Authentication"])
    app.include_router(door_router, prefix="/api/doors", tags=["Doors"])
    app.include_router(visitor_router, prefix="/api/visitors", tags=["Visitors"])
    app.include_router(register_router, prefix="/api/register", tags=["Registration"])
    
    print("SUCCESS: All routers connected.")
except ImportError as e:
    print(f"CRITICAL: Failed to load routers. Error: {e}")
except AttributeError as e:
    print(f"CRITICAL: One of your controllers is missing 'router = APIRouter()'. Error: {e}")