import asyncio
import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.routers import campus, health, profile, resolve
from app.services.pipeline import vision

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("visual_campus")



@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load the CLIP model in the background: the server answers at once, profiles get vision when it is ready.
    warm_up = asyncio.create_task(vision.warm_up())
    yield
    warm_up.cancel()


app = FastAPI(title="Visual Campus API", version="0.1.0", lifespan=lifespan)

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


@app.exception_handler(RequestValidationError)
async def readable_validation_error(request: Request, exc: RequestValidationError):
    problems = [f"{'.'.join(str(p) for p in err['loc'][1:])}: {err['msg']}" for err in exc.errors()]
    return JSONResponse(status_code=422, content={"detail": "Invalid request. " + "; ".join(problems)})


app.include_router(health.router)
app.include_router(resolve.router)
app.include_router(profile.router)
app.include_router(campus.router)
