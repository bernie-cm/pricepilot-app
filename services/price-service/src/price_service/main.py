from fastapi import FastAPI
from price_service.routers.prices import router as prices_router

app = FastAPI()
app.include_router(prices_router)


@app.get("/health")
async def health_check():
    return {"status": "ok"}
