import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.config import get_settings
from app.core.cors import add_cors_middleware
from app.api.v1 import api_router
from app.api.v1.websocket import broadcast_loop
from app.database import engine, Base
from app import models


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create DB tables and start background broadcast task
    Base.metadata.create_all(bind=engine)
    task = asyncio.create_task(broadcast_loop())
    yield
    # Shutdown: cancel background task
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


def get_frontend_dir() -> str:
    """Resolve frontend directory for both local dev and Docker."""
    # Docker path
    docker_path = Path("/app/frontend")
    if docker_path.exists():
        return str(docker_path)
    # Local dev: main.py is at backend/app/main.py, frontend is at ../../frontend
    local_path = Path(__file__).resolve().parent.parent.parent / "frontend"
    if local_path.exists():
        return str(local_path)
    # Fallback
    return str(Path("frontend").resolve())


def create_application() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.APP_NAME,
        description="US Stock Market Data API powered by yfinance",
        version="1.0.0",
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        lifespan=lifespan,
    )

    add_cors_middleware(app)

    # API routes
    app.include_router(api_router, prefix="/api/v1")

    # Serve frontend static files
    frontend_dir = get_frontend_dir()
    if os.path.isdir(frontend_dir):
        app.mount("/assets", StaticFiles(directory=frontend_dir), name="frontend")

        @app.get("/")
        async def root():
            return FileResponse(os.path.join(frontend_dir, "index.html"))
    else:
        @app.get("/")
        async def root():
            return {"message": "Frontend not found. Please build the frontend first."}

    @app.get("/health")
    async def health_check():
        return {"status": "ok", "service": settings.APP_NAME}

    return app


app = create_application()
