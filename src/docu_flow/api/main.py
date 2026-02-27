"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from docu_flow.api.routes import protocols, screening, health
from docu_flow.config import settings
from docu_flow.logging import configure_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    settings.ensure_dirs()
    yield


app = FastAPI(
    title="docu-flow",
    description="Clinical trial eligibility screening via protocol PDF parsing",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, tags=["health"])
app.include_router(protocols.router, prefix="/protocols", tags=["protocols"])
app.include_router(screening.router, prefix="/screening", tags=["screening"])
