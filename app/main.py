from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import health
from app.core.database import create_tables

# Additional routers registered here as each module is implemented via TDD:
# from app.api.routes import scan, history
# from app.dashboard import router as dashboard_router


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
