from __future__ import annotations
from datetime import date
from fastapi import HTTPException
from app.db import db, db_ro
from app.services.core import now, partition_row


def list_policies():
    with db_ro() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM retention_policies ORDER BY id").fetchall()]


def list_destroys():
    with db_ro() as conn:
        rows = conn.execute(
            '''SELECT d.*, p.part_key, p.title, pol.name AS policy_name
               FROM destroy_runs d
               JOIN partitions p ON p.id=d.partition_id
               JOIN retention_policies pol ON pol.id=d.policy_id
               ORDER BY d.id DESC'''
        ).fetchall()
        return [dict(r) for r in rows]


def run_retention(policy_id: int, mode: str = "连目录销毁"):
    if mode not in ("连目录销毁", "只删元数据"):
        raise HTTPException(400, detail="销毁模式无效")
    with db() as conn:
        pol = conn.execute("SELECT * FROM retention_policies WHERE id=? AND active=1", (policy_id,)).fetchone()
        if not pol:
            raise HTTPException(404, detail="保留策略不存在")
        biz = conn.execute("SELECT value FROM settings WHERE key='营业日'").fetchone()
        today = date.fromisoformat(biz["value"] if biz else date.today().isoformat())
        parts = conn.execute("SELECT * FROM partitions WHERE status='在册'").fetchall()
        done = []
        for p in parts:
            age = (today - date.fromisoformat(p["release_day"])).days
            if age < pol["max_age_days"]:
                continue
            if pol["action"] == "只标过期":
                conn.execute("UPDATE partitions SET status='已过期' WHERE id=?", (p["id"],))
                cur = conn.execute(
                    "INSERT INTO destroy_runs(partition_id, policy_id, mode, status, created_at, note) VALUES (?,?,?,?,?,?)",
                    (p["id"], policy_id, mode, "已标记过期", now(), f"片龄{age}天"),
                )
                done.append({"partition_id": p["id"], "run_id": cur.lastrowid, "status": "已标记过期"})
                continue
            clips = conn.execute("SELECT object_key FROM clips WHERE partition_id=?", (p["id"],)).fetchall()
            if mode == "连目录销毁":
                for c in clips:
                    conn.execute("DELETE FROM inventory_objects WHERE object_key=?", (c["object_key"],))
            conn.execute("DELETE FROM clips WHERE partition_id=?", (p["id"],))
            conn.execute("UPDATE partitions SET status='已销毁' WHERE id=?", (p["id"],))
            cur = conn.execute(
                "INSERT INTO destroy_runs(partition_id, policy_id, mode, status, created_at, note) VALUES (?,?,?,?,?,?)",
                (p["id"], policy_id, mode, "已销毁", now(), f"片龄{age}天"),
            )
            done.append({"partition_id": p["id"], "run_id": cur.lastrowid, "status": "已销毁"})
        return {"policy": pol["name"], "affected": done}
