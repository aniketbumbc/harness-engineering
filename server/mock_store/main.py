from fastapi import FastAPI

from .endpoints import router

app = FastAPI(title="Mock Store")
app.include_router(router)
