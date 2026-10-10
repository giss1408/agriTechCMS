import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from . import db
from .api import auth, collections, cooperative, issues, lots, misc, payments, producers, sync, users
from .config import settings
from .core.bandwidth import ETagMiddleware, GzipRequestMiddleware
from .core.errors import install_error_handlers
from .models import Base

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

API_PREFIX = "/v1"


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings.check()
    if settings.auto_create_schema:
        async with db.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="AgriTech CMS API",
        version="0.1.0",
        description="Collecte agricole, paiements mobile money et traçabilité pour les coopératives ivoiriennes.",
        lifespan=lifespan,
        docs_url="/docs",
    )
    # Innermost first. Low bandwidth: ETag/304 on the uncompressed body, gzip-encoded uploads accepted,
    # responses gzip-compressed (JSON shrinks 5-10x), CORS outermost so 304s carry CORS headers too.
    app.add_middleware(ETagMiddleware)
    app.add_middleware(GzipRequestMiddleware)
    app.add_middleware(GZipMiddleware, minimum_size=860, compresslevel=6)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["Content-Disposition", "X-Duplicate", "ETag"],
    )
    install_error_handlers(app)
    for module in (auth, users, cooperative, producers, collections, sync, lots, payments, issues, misc):
        app.include_router(module.router, prefix=API_PREFIX)

    @app.get("/health", tags=["ops"])
    async def health():
        return {"status": "ok", "env": settings.env}

    return app


app = create_app()
