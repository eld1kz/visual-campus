import logging
import time

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.services import ai_budget
from app.routers import ai, campus, chat, health, profile, resolve

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
async def ai_user(request: Request, call_next):
    """Who pays for Claude calls made while serving this request (see services/ai_budget.py)."""
    client_id = (request.headers.get("x-client-id") or "").strip()[:64]
    user = f"id:{client_id}" if client_id else f"ip:{request.client.host if request.client else 'unknown'}"
    token = ai_budget.current_user.set(user)
    try:
        return await call_next(request)
    finally:
        ai_budget.current_user.reset(token)


@app.middleware("http")
async def log_request_time(request: Request, call_next):
    started = time.perf_counter()
    response = await call_next(request)
    took_ms = (time.perf_counter() - started) * 1000
    logger.info("%s %s -> %s in %.0f ms", request.method, request.url.path, response.status_code, took_ms)
    response.headers["X-Response-Time-ms"] = f"{took_ms:.0f}"
    return response


@app.exception_handler(RequestValidationError)
async def readable_validation_error(request: Request, exc: RequestValidationError):
    problems = [f"{'.'.join(str(p) for p in err['loc'][1:])}: {err['msg']}" for err in exc.errors()]
    return JSONResponse(status_code=422, content={"detail": "Invalid request. " + "; ".join(problems)})


app.include_router(health.router)
app.include_router(resolve.router)
app.include_router(profile.router)
app.include_router(campus.router)
app.include_router(chat.router)
app.include_router(ai.router)
