from __future__ import annotations
from fastapi import APIRouter
from app.db import db_ro
from app.services.distribution import current_distribution, cross_check

router = APIRouter(tags=["总览"])


@router.get("/总览")
def overview():
    # 架构口径：每次打开按分区册温层列即时重算，不读任何持久分布账/快照。
    # 走只读快照，读到的必是某笔已提交回执后的完整分区册，无中间态。
    with db_ro() as conn:
        def cnt(sql, *a):
            return conn.execute(sql, a).fetchone()["c"]

        dist = current_distribution(conn)
        tri = dist["三色"]
        return {
            # 三色分布条：唯一由分区册即时重算，保证与分区册温层列同刷。
            "热档": tri["热档"],
            "温档": tri["温档"],
            "冷档": tri["冷档"],
            "在册总数": dist["在册总数"],
            "分布口径": dist["口径"],
            "分布架构": dist["架构"],
            # 诊断对账随总览返回：诊断改数不会进入三色，对不上即明确拒因、不假装绿。
            "分布对账": cross_check(conn),
            "迁移执行中": cnt("SELECT COUNT(*) AS c FROM migrate_jobs WHERE status='执行中'"),
            "待销毁候选": cnt("SELECT COUNT(*) AS c FROM partitions WHERE status='已过期'"),
            "已销毁": cnt("SELECT COUNT(*) AS c FROM partitions WHERE status='已销毁'"),
            "目录对象": cnt("SELECT COUNT(*) AS c FROM inventory_objects"),
            "最近互证": (
                lambda r: dict(r) if r else None
            )(conn.execute("SELECT status, drift_count, created_at FROM verify_runs ORDER BY id DESC LIMIT 1").fetchone()),
            "片库间": [dict(x) for x in conn.execute("SELECT id, name, capacity, active FROM vaults ORDER BY id").fetchall()],
        }
