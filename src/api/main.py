from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from .audit_service import close_audit_pg_engine, init_audit_pg_engine, router as audit_router
from .ruc_validator import validate_ruc_from_master


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    database_url = os.getenv("DATABASE_URL") or os.getenv("LEDGER_DATABASE_URL")
    if database_url:
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)
        init_audit_pg_engine(app, database_url)

        def ruc_validator(ruc: str, tenant_id: str | None = None) -> dict[str, str]:
            active_tenant_id = tenant_id or getattr(app.state, "last_tenant_id", "")
            return validate_ruc_from_master(app.state.pg_engine, active_tenant_id, ruc)

        app.state.ruc_validator = ruc_validator

    yield
    close_audit_pg_engine(app)


app = FastAPI(
    title="CONTA_PRO Enterprise - Auditoria Forense",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("AUDIT_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def tenant_context(request: Request, call_next):
    tenant_id = (
        request.headers.get("X-Tenant-Id")
        or request.query_params.get("tenant_id")
        or os.getenv("DEFAULT_TENANT_ID")
        or ""
    ).strip()
    if tenant_id:
        request.state.tenant_id = tenant_id
        request.app.state.last_tenant_id = tenant_id
    return await call_next(request)


@app.get("/health")
async def health():
    return {
        "ok": True,
        "service": "conta-pro-audit",
        "postgres_configured": bool(getattr(app.state, "pg_engine", None)),
    }


app.include_router(audit_router)
