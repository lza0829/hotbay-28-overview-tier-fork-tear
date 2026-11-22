from __future__ import annotations
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import PROJECT_NAME
from app.routers import dashboard, migrates, partitions, retentions, settings, vaults, verify
from app.seed import seed_if_empty

seed_if_empty()

app = FastAPI(title=PROJECT_NAME)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.include_router(dashboard.router, prefix="/api")
app.include_router(vaults.router, prefix="/api")
app.include_router(partitions.router, prefix="/api")
app.include_router(migrates.router, prefix="/api")
app.include_router(retentions.router, prefix="/api")
app.include_router(verify.router, prefix="/api")
app.include_router(settings.router, prefix="/api")


@app.get("/api/健康")
def health():
    return {"产品": PROJECT_NAME, "状态": "正常"}
