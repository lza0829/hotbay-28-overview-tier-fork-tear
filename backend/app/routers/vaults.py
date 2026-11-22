from __future__ import annotations
from fastapi import APIRouter
from app.db import db_ro
from app.services.core import vault_partition_count

router = APIRouter(tags=["片库间"])


@router.get("/片库间")
def list_vaults():
    with db_ro() as conn:
        out = []
        for v in conn.execute("SELECT * FROM vaults ORDER BY id").fetchall():
            d = dict(v)
            d["在册分区数"] = vault_partition_count(conn, v["id"])
            out.append(d)
        return out
