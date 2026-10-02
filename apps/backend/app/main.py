import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import db
from .api import auth, collections, cooperative, lots, misc, payments, producers, sync, users
from .config import settings
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
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["Content-Disposition", "X-Duplicate"],
    )
    install_error_handlers(app)
    for module in (auth, users, cooperative, producers, collections, sync, lots, payments, misc):
        app.include_router(module.router, prefix=API_PREFIX)

    @app.get("/health", tags=["ops"])
    async def health():
        return {"status": "ok", "env": settings.env}

    return app


app = create_app()
