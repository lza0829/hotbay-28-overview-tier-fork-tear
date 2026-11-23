from __future__ import annotations
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.db import db, db_ro

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
def distribution_bypass_reject(_body: dict | None = None):
    """维护口改分布数：显式拒绝（403）。

    全局架构为“打开总览即时重算”：三色分布只能由登记/迁移完成/销毁成功回执
    经分区册温层列重算生成，没有任何可写的分布账。维护口改数不是业务回执，
    整笔拒绝、不落库、不得冒充写口已成功，总览页不得因此亮齐。
    """
    raise HTTPException(
        status_code=403,
        detail="拒绝：维护口不得修改三色分布；分布仅由登记/迁移完成/销毁成功回执经分区册重算生成",
    )
