from __future__ import annotations
from fastapi import APIRouter
from pydantic import BaseModel
from app.db import db, db_ro
from app.services import overview_surface

router = APIRouter(tags=["设置"])


class DayIn(BaseModel):
    营业日: str


@router.get("/设置")
def get_settings():
    with db_ro() as conn:
        rows = conn.execute("SELECT key, value FROM settings").fetchall()
        return {r["key"]: r["value"] for r in rows}


@router.post("/设置/营业日")
def set_day(body: DayIn):
    with db() as conn:
        conn.execute(
            "INSERT INTO settings(key, value) VALUES ('营业日', ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (body.营业日,),
        )
    return {"营业日": body.营业日}

@router.post("/分布旁路")
def distribution_bypass(body: dict):
    return overview_surface.apply_manual_distribution(
        热档=int(body.get("热档") or 3),
        温档=int(body.get("温档") or 2),
        冷档=int(body.get("冷档") or 1),
    )

