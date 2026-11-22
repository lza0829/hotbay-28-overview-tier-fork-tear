from __future__ import annotations
from typing import Any
from fastapi import APIRouter
from pydantic import BaseModel, Field
from app.db import db_ro
from app.services import partitions as svc

router = APIRouter(tags=["分区"])


class ClipIn(BaseModel):
    object_key: str
    bytes: int
    entered_day: str | None = None
    note: str = ""


class PartIn(BaseModel):
    part_key: str
    title: str
    release_day: str
    vault_id: int
    tier: str = "热档"
    object_prefix: str
    clips: list[ClipIn] = Field(default_factory=list)


@router.get("/分区")
def list_parts():
    return svc.list_partitions()


@router.get("/分区/{pid}/素材段")
def list_clips(pid: int):
    with db_ro() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM clips WHERE partition_id=? ORDER BY id", (pid,)).fetchall()]


@router.post("/分区")
def create_part(body: PartIn):
    return svc.create_partition(
        body.part_key,
        body.title,
        body.release_day,
        body.vault_id,
        body.tier,
        body.object_prefix,
        [c.model_dump() for c in body.clips],
    )
