from __future__ import annotations
from fastapi import APIRouter
from pydantic import BaseModel
from app.services import migrate as svc

router = APIRouter(tags=["迁移"])


class MigrateIn(BaseModel):
    partition_id: int
    to_tier: str


class FinishIn(BaseModel):
    success: bool = True


@router.get("/迁移")
def list_jobs():
    return svc.list_jobs()


@router.post("/迁移")
def start(body: MigrateIn):
    return svc.start_migrate(body.partition_id, body.to_tier)


@router.post("/迁移/{job_id}/完成")
def finish(job_id: int, body: FinishIn):
    return svc.finish_migrate(job_id, body.success)
