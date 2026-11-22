from __future__ import annotations
from datetime import date, timedelta
from app.db import db, init_db


def seed_if_empty() -> None:
    init_db()
    with db() as conn:
        n = conn.execute("SELECT COUNT(*) AS c FROM vaults").fetchone()["c"]
        if n:
            return
        vaults = [
            ("主厅成片间", 40),
            ("宣发快取间", 24),
            ("冷库片窖", 80),
        ]
        for name, cap in vaults:
            conn.execute("INSERT INTO vaults(name, capacity, active) VALUES (?,?,1)", (name, cap))
        conn.execute(
            "INSERT INTO retention_policies(name, max_age_days, action, active) VALUES (?,?,?,1)",
            ("常规片龄九十天", 90, "销毁"),
        )
        conn.execute(
            "INSERT INTO retention_policies(name, max_age_days, action, active) VALUES (?,?,?,1)",
            ("宣发快取三十天", 30, "只标过期"),
        )
        today = date.today()
        rows = [
            ("P-红海2024-主成片", "红海行动重映成片", str(today - timedelta(days=120)), 1, "热档", "reel/红海/主成片/"),
            ("P-流浪2025-预告", "流浪地球预告合集", str(today - timedelta(days=20)), 2, "温档", "reel/流浪/预告/"),
            ("P-哪吒2025-物料", "哪吒宣发物料", str(today - timedelta(days=5)), 2, "热档", "reel/哪吒/物料/"),
            ("P-封神2023-冷存", "封神第一部冷存", str(today - timedelta(days=400)), 3, "冷档", "reel/封神/冷存/"),
        ]
        for key, title, day, vid, tier, prefix in rows:
            cur = conn.execute(
                "INSERT INTO partitions(part_key, title, release_day, vault_id, tier, object_prefix, status, created_at) VALUES (?,?,?,?,?,?, '在册', ?)",
                (key, title, day, vid, tier, prefix, f"{day}T10:00:00"),
            )
            pid = cur.lastrowid
            for i, label in enumerate(("正片段", "字幕段", "海报静帧"), start=1):
                ok = f"{prefix}seg-{i:02d}.bin"
                conn.execute(
                    "INSERT INTO clips(partition_id, object_key, bytes, entered_day, note) VALUES (?,?,?,?,?)",
                    (pid, ok, 8_000_000 + i * 120_000, day, label),
                )
                conn.execute(
                    "INSERT INTO inventory_objects(object_key, bytes, vault_name, scanned_at) VALUES (?,?,?,?)",
                    (
                        ok,
                        8_000_000 + i * 120_000,
                        {1: "主厅成片间", 2: "宣发快取间", 3: "冷库片窖"}[vid],
                        f"{today.isoformat()}T09:00:00",
                    ),
                )
        conn.execute(
            "INSERT INTO settings(key, value) VALUES ('营业日', ?)",
            (today.isoformat(),),
        )
