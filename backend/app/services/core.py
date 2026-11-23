from __future__ import annotations
from datetime import datetime
from fastapi import HTTPException
from app.config import TIER_ORDER, TIERS


def now() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def require_tier(tier: str) -> str:
    if tier not in TIERS:
        raise HTTPException(400, detail=f"温层只能是{'/'.join(TIERS)}")
    return tier


def vault_partition_count(conn, vault_id: int) -> int:
    return conn.execute(
        "SELECT COUNT(*) AS c FROM partitions WHERE vault_id=? AND status='在册'",
        (vault_id,),
    ).fetchone()["c"]


def partition_row(conn, pid: int):
    row = conn.execute("SELECT * FROM partitions WHERE id=?", (pid,)).fetchone()
    if not row:
        raise HTTPException(404, detail="分区不存在")
    return row


def can_migrate(from_tier: str, to_tier: str) -> bool:
    return TIER_ORDER[to_tier] != TIER_ORDER[from_tier]

