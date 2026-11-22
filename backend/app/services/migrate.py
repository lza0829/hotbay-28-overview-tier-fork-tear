from __future__ import annotations
from fastapi import HTTPException
from app.db import db, db_ro
from app.services.core import can_migrate, now, partition_row, require_tier


def list_jobs():
    with db_ro() as conn:
        rows = conn.execute(
            '''SELECT j.*, p.part_key, p.title FROM migrate_jobs j
               JOIN partitions p ON p.id=j.partition_id ORDER BY j.id DESC'''
        ).fetchall()
        return [dict(r) for r in rows]


def start_migrate(partition_id: int, to_tier: str):
    to_tier = require_tier(to_tier)
    with db() as conn:
        p = partition_row(conn, partition_id)
        if p["status"] != "在册":
            raise HTTPException(400, detail="仅在册分区可迁移")
        if not can_migrate(p["tier"], to_tier):
            raise HTTPException(400, detail="目标温层与现行相同")
        open_job = conn.execute(
            "SELECT 1 FROM migrate_jobs WHERE partition_id=? AND status='执行中'",
            (partition_id,),
        ).fetchone()
        if open_job:
            raise HTTPException(400, detail="已有执行中的迁移，拒绝双迁")
        cur = conn.execute(
            "INSERT INTO migrate_jobs(partition_id, from_tier, to_tier, status, created_at) VALUES (?,?,?,?,?)",
            (partition_id, p["tier"], to_tier, "执行中", now()),
        )
        return {"job_id": cur.lastrowid, "status": "执行中"}


def finish_migrate(job_id: int, success: bool = True):
    with db() as conn:
        j = conn.execute("SELECT * FROM migrate_jobs WHERE id=?", (job_id,)).fetchone()
        if not j:
            raise HTTPException(404, detail="迁移单不存在")
        if j["status"] != "执行中":
            raise HTTPException(400, detail="迁移单不在执行中")
        if success:
            conn.execute("UPDATE partitions SET tier=? WHERE id=?", (j["to_tier"], j["partition_id"]))
            conn.execute(
                "UPDATE migrate_jobs SET status='已完成', finished_at=? WHERE id=?",
                (now(), job_id),
            )
            return {"job_id": job_id, "status": "已完成", "tier": j["to_tier"]}
        conn.execute(
            "UPDATE migrate_jobs SET status='已失败', finished_at=?, note='执行失败回滚温层' WHERE id=?",
            (now(), job_id),
        )
        return {"job_id": job_id, "status": "已失败"}
