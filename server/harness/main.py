import httpx
from fastapi import FastAPI
from shared.settings import settings

app = FastAPI(title="Refund Harness")


@app.get("/health")
def health():
    r = httpx.get(f"{settings.mock_store_url}/health", timeout=5)
    return {
        "status": "ok",
        "service": "harness",
        "mock_store": r.json(),
    }