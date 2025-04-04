from fastapi import FastAPI, APIRouter
from modules.google_ads.router.google_ads_router import router as google_ads_router
import uvicorn
import os
# from app.routes.auth import router as ads_router

router = APIRouter(prefix="/integrations", tags=["Integrations"])

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Welcome to integrations server"}

if __name__ == "__main__":
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"  # ✅ Set this to allow HTTP in local testing
    uvicorn.run(app, host="0.0.0.0", port=8000)

# Register routes
app.include_router(router=google_ads_router)
