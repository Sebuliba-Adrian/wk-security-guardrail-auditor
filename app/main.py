from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import dashboard, health, history, scan
from app.core.database import create_tables


@asynccontextmanager
async def lifespan(app: FastAPI) -> Any:
    await create_tables()
    yield


app = FastAPI(
    title="Security Guardrail Auditor",
    description="Audit Terraform and CloudFormation files against security baselines.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(scan.router, prefix="/api")
app.include_router(history.router, prefix="/api")
app.include_router(dashboard.router)
