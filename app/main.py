from fastapi import FastAPI
from app.routes.auth import router as auth_router
from app.routes.ads import router as ads_router
# from app.routes.auth import router as ads_router

app = FastAPI()

# Register routes
app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
app.include_router(ads_router, prefix="/ads", tags=["Google Ads"])

@app.get("/")
async def root():
    return {"message": "Google Ads Integration API"}
