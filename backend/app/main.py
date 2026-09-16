import logging
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import health

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("visual_campus")

app = FastAPI(title="Visual Campus API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_request_time(request: Request, call_next):
    started = time.perf_counter()
    response = await call_next(request)
    took_ms = (time.perf_counter() - started) * 1000
    logger.info("%s %s -> %s in %.0f ms", request.method, request.url.path, response.status_code, took_ms)
    response.headers["X-Response-Time-ms"] = f"{took_ms:.0f}"
    return response


app.include_router(health.router)
