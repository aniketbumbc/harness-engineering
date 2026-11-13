from fastapi import FastAPI

from .route import router

app = FastAPI(title="Mock Store")
app.include_router(router)
