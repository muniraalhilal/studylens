import os
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from .database import Base, ROOT, engine
from .routers import auth, documents, quizzes
from .middleware import RequestSizeLimit
from .config import app_origin
from sqlalchemy import text
from .database import SessionLocal
from .services.demo import cleanup_expired_guests


@asynccontextmanager
async def lifespan(app):
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        cleanup_expired_guests(db)
        db.commit()
    yield


app = FastAPI(
    title="StudyLens API",
    version="1.1.0",
    description="Private document study workspace with an entirely offline extractive engine.",
    lifespan=lifespan,
)
app.add_middleware(RequestSizeLimit)
requests = defaultdict(deque)


@app.middleware("http")
async def protections(request: Request, call_next):
    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        origin = request.headers.get("origin")
        allowed = app_origin()
        if origin and origin.rstrip("/") != allowed:
            return JSONResponse({"detail": "Origin not allowed"}, status_code=403)
        try:
            content_length = int(request.headers.get("content-length", "0") or 0)
        except ValueError:
            return JSONResponse({"detail": "Invalid Content-Length"}, status_code=400)
        if content_length > 11 * 1024 * 1024:
            return JSONResponse({"detail": "Maximum upload size is 10 MB"}, status_code=413)
    if request.url.path.startswith("/api/") and request.method in {"POST", "DELETE"}:
        key = request.client.host if request.client else "local"
        if os.getenv("TRUST_CLOUDFLARE", "false").lower() == "true" and key in {"127.0.0.1", "::1"}:
            key = request.headers.get("cf-connecting-ip", key)
        auth_request = request.url.path in {"/api/auth/login", "/api/auth/register", "/api/auth/demo"}
        key = (key, "auth" if auth_request else "write")
        # Discard stale IP buckets so the limiter itself stays bounded.
        for stale in [k for k, q in requests.items() if not q or q[-1] < time.monotonic() - 60]:
            del requests[stale]
        if key not in requests and len(requests) >= 10000:
            return JSONResponse({"detail": "Server busy, please retry"}, status_code=429)
        queue = requests[key]
        now = time.monotonic()
        while queue and queue[0] < now - 60:
            queue.popleft()
        if len(queue) >= (15 if auth_request else 120):
            return JSONResponse({"detail": "Please wait a minute / يرجى الانتظار دقيقة"}, status_code=429)
        queue.append(now)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "same-origin"
    if request.url.path.startswith("/api"):
        response.headers["Cache-Control"] = "no-store"
    if not request.url.path.startswith(("/docs", "/redoc")):
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; frame-ancestors 'none'"
        )
    return response


for router in (auth.router, documents.router, quizzes.router):
    app.include_router(router, prefix="/api")


@app.get("/api/health", tags=["System"])
def health():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception:
        return JSONResponse({"status": "unavailable"}, status_code=503)
    return {"status": "ok", "database": "ok", "engine": "offline-extractive"}


@app.get("/api/config", tags=["System"])
def config():
    return {"public_demo_only": os.getenv("PUBLIC_DEMO_ONLY", "false").lower() == "true"}


app.mount("/assets", StaticFiles(directory=ROOT / "frontend"), name="assets")


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(ROOT / "frontend/index.html")
