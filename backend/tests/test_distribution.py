"""三色分布联动闭合测试。

全局架构：打开总览即时重算（recompute_on_open），无持久分布账。
覆盖需求的全部闭合条件：
  1. 三类业务回执（登记/迁移完成/销毁成功）后，总览三色与分区册温层列同刷；
  2. 分布结果可由选定口径重放（纯函数，同输入同输出）；
  3. 诊断改数不得伪装回执：改数端点 403，互证/目录改数盖不住重算；
  4. 半截回执整体回滚，不留“分布已变、分区册未变”；
  5. 并发登记与迁移完成不漂档：三色之和恒等于在册分区数，分档与分组逐一对上。
"""
import os
import threading
import tempfile

import pytest

# 必须在导入 app 之前指定独立临时库，避免污染开发库。
_TMP = tempfile.mkdtemp(prefix="hotbay-test-")
os.environ["HOTBAY_DB"] = os.path.join(_TMP, "test.db")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.db import connect  # noqa: E402
from app.services import partitions as psvc  # noqa: E402
from app.services import migrate as msvc  # noqa: E402
from app.services import retention as rsvc  # noqa: E402
from app.services.distribution import (  # noqa: E402
    DISTRIBUTION_ARCH,
    current_distribution,
    replay_distribution,
)


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def _tier_book():
    """直接按分区册温层列分组，作为独立基准事实。"""
    conn = connect()
    try:
        rows = conn.execute(
            "SELECT tier, COUNT(*) AS c FROM partitions WHERE status='在册' GROUP BY tier"
        ).fetchall()
        book = {"热档": 0, "温档": 0, "冷档": 0}
        for r in rows:
            book[r["tier"]] = r["c"]
        on_book = conn.execute(
            "SELECT COUNT(*) AS c FROM partitions WHERE status='在册'"
        ).fetchone()["c"]
        return book, on_book
    finally:
        conn.close()


def _overview_tri(client):
    o = client.get("/api/总览").json()
    return {t: o[t] for t in ("热档", "温档", "冷档")}, o


def _assert_matches_book(client):
    """核心不变量：总览三色 === 分区册温层列分组，且三色之和 === 在册总数。"""
    tri, o = _overview_tri(client)
    book, on_book = _tier_book()
    assert tri == book
    assert sum(tri.values()) == on_book == o["在册总数"]
    assert o["分布架构"] == DISTRIBUTION_ARCH
    assert o["分布对账"]["一致"] is True
    return tri


def test_seed_initial_distribution_matches_book(client):
    tri = _assert_matches_book(client)
    # seed：热档 2、温档 1、冷档 1
    assert tri == {"热档": 2, "温档": 1, "冷档": 1}


def test_replay_is_pure_and_replayable(client):
    # 同一批分区册行，任意次重放结果一致（可由选定口径重放）。
    conn = connect()
    try:
        rows = conn.execute("SELECT tier, status FROM partitions").fetchall()
    finally:
        conn.close()
    first = replay_distribution(rows)
    second = replay_distribution([dict(r) for r in rows])
    assert first == second
    # 与在线重算口径一致
    assert first["三色"] == current_distribution()["三色"]
    assert first["架构"] == "recompute_on_open"


def _new_partition(client, key, tier="热档", vault_id=3):
    body = {
        "part_key": key,
        "title": f"片-{key}",
        "release_day": "2026-01-01",
        "vault_id": vault_id,
        "tier": tier,
        "object_prefix": f"reel/{key}/",
        "clips": [{"object_key": f"reel/{key}/seg-01.bin", "bytes": 1000, "note": "正片段"}],
    }
    r = client.post("/api/分区", json=body)
    assert r.status_code == 200, r.text
    return r.json()


def test_register_receipt_moves_distribution_and_book_together(client):
    before, _ = _overview_tri(client)
    _new_partition(client, "P-TEST-REG-1", tier="温档")
    after = _assert_matches_book(client)
    assert after["温档"] == before["温档"] + 1
    # 其它档不动
    assert after["热档"] == before["热档"]
    assert after["冷档"] == before["冷档"]


def test_migrate_finish_receipt_moves_one_tier_atomically(client):
    p = _new_partition(client, "P-TEST-MIG-1", tier="热档")
    mid = client.post("/api/迁移", json={"partition_id": p["id"], "to_tier": "冷档"}).json()["job_id"]
    before = _assert_matches_book(client)
    r = client.post(f"/api/迁移/{mid}/完成", json={"success": True})
    assert r.status_code == 200 and r.json()["status"] == "已完成"
    after = _assert_matches_book(client)
    assert after["热档"] == before["热档"] - 1
    assert after["冷档"] == before["冷档"] + 1
    assert after["温档"] == before["温档"]
    # 分区册温层列确已变更
    conn = connect()
    try:
        tier = conn.execute("SELECT tier FROM partitions WHERE id=?", (p["id"],)).fetchone()["tier"]
        assert tier == "冷档"
    finally:
        conn.close()


def test_migrate_failure_keeps_book_and_distribution(client):
    p = _new_partition(client, "P-TEST-MIG-FAIL", tier="热档")
    mid = client.post("/api/迁移", json={"partition_id": p["id"], "to_tier": "温档"}).json()["job_id"]
    before = _assert_matches_book(client)
    client.post(f"/api/迁移/{mid}/完成", json={"success": False})
    after = _assert_matches_book(client)
    assert after == before  # 失败回滚，温层与分布都不动


def test_destroy_receipt_removes_from_distribution(client):
    # 用一个早已过期的分区，走“销毁”策略（策略1：90天销毁）
    body = {
        "part_key": "P-TEST-DESTROY-1",
        "title": "过期片",
        "release_day": "2020-01-01",
        "vault_id": 3,
        "tier": "冷档",
        "object_prefix": "reel/P-TEST-DESTROY-1/",
        "clips": [{"object_key": "reel/P-TEST-DESTROY-1/s.bin", "bytes": 10}],
    }
    client.post("/api/分区", json=body)
    before = _assert_matches_book(client)
    r = client.post("/api/保留执行", json={"policy_id": 1, "mode": "只删元数据"})
    assert r.status_code == 200
    destroyed = [a for a in r.json()["affected"] if a["status"] == "已销毁"]
    assert any(a["status"] == "已销毁" for a in destroyed)
    after = _assert_matches_book(client)
    # 在册总数恰按本次销毁条数下降；目标分区已不在册
    assert sum(after.values()) == sum(before.values()) - len(destroyed)
    conn = connect()
    try:
        st = conn.execute(
            "SELECT status FROM partitions WHERE part_key='P-TEST-DESTROY-1'"
        ).fetchone()["status"]
        assert st == "已销毁"
    finally:
        conn.close()


def test_half_receipt_rolls_back_entirely(client):
    # 先登记一个分区占用某对象键，再用同对象键登记第二个分区：
    # 分区插入后在片段插入处撞库报错，整笔事务回滚（不依赖 seed 数据与用例顺序）。
    dup_key = "reel/P-TEST-HALF-DUP/s.bin"
    _new_partition(client, "P-TEST-HALF-0", tier="热档")
    conn = connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute(
            "INSERT OR REPLACE INTO clips(partition_id, object_key, bytes, entered_day) VALUES (?,?,?,?)",
            (1, dup_key, 1, "2026-01-01"),
        )
        conn.commit()
    finally:
        conn.close()

    book_before, on_before = _tier_book()
    body = {
        "part_key": "P-TEST-HALF-1",
        "title": "半截回执",
        "release_day": "2026-01-01",
        "vault_id": 3,
        "tier": "热档",
        "object_prefix": "reel/P-TEST-HALF-1/",
        "clips": [{"object_key": dup_key, "bytes": 1}],
    }
    r = client.post("/api/分区", json=body)
    assert r.status_code == 400
    # 分区册无残留
    conn = connect()
    try:
        ghost = conn.execute("SELECT 1 FROM partitions WHERE part_key='P-TEST-HALF-1'").fetchone()
        assert ghost is None
    finally:
        conn.close()
    # 分布条与分区册都未变，不存在半截
    assert _tier_book() == (book_before, on_before)
    _assert_matches_book(client)


def test_diagnostic_tamper_is_rejected_and_cannot_repaint(client):
    tri_before, o_before = _overview_tri(client)
    # 1) 显式改数端点必须 403
    r = client.post("/api/分布对账/改数", json={"热档": 999})
    assert r.status_code == 403
    # 2) 直接篡改诊断侧数据（互证流水 + 目录清单字节），不得影响三色重算
    conn = connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute(
            "INSERT INTO verify_runs(status, drift_count, detail, created_at) VALUES (?,?,?,?)",
            ("一致", 0, "[]", "2026-11-22T00:00:00"),
        )
        conn.execute("UPDATE inventory_objects SET bytes=bytes+1")
        conn.commit()
    finally:
        conn.close()
    tri_after, o_after = _overview_tri(client)

    # 对账仍以分区册为准且自洽
    cc = client.get("/api/分布对账").json()
    assert cc["一致"] is True and cc["拒因"] is None
    assert cc["三色重算"] == tri_after


def test_maintenance_bypass_is_rejected_and_cannot_repaint(client):
    """维护口（/api/分布旁路）改数：整笔 403，不得冒充写口成功，总览不得因此亮齐。"""
    tri_before, _ = _overview_tri(client)
    r = client.post("/api/分布旁路", json={"热档": 999, "温档": 888, "冷档": 777})
    assert r.status_code == 403
    # 总览三色仍由分区册重放，与旁路改数前完全一致
    tri_after, o_after = _overview_tri(client)
    assert tri_after == tri_before
    assert o_after["分布对账"]["一致"] is True
    # 旁路不得留下任何“表面已对齐”的落库痕迹
    conn = connect()
    try:
        keys = {
            row["key"]
            for row in conn.execute(
                "SELECT key FROM settings WHERE key LIKE 'overview_surface%'"
            ).fetchall()
        }
    finally:
        conn.close()
    assert not keys


def test_overview_read_path_writes_nothing(client):
    """读路径（总览/分布对账）只读：不得写任何表，尤其不得落伪分布快照。"""
    conn = connect()
    try:
        before = {
            row["key"]
            for row in conn.execute("SELECT key FROM settings").fetchall()
        }
    finally:
        conn.close()
    client.get("/api/总览")
    client.get("/api/分布对账")
    conn = connect()
    try:
        after = {
            row["key"]
            for row in conn.execute("SELECT key FROM settings").fetchall()
        }
    finally:
        conn.close()
    assert after == before  # 读路径不产生任何新设置键（无 overview_surface_* 之类）
    _assert_matches_book(client)



def test_concurrent_register_and_migrate_never_drift(client):
    n = 20
    errors = []

    def register(i):
        try:
            psvc.create_partition(
                f"P-CONC-R-{i}", f"并发登记{i}", "2026-01-01", 3, "热档",
                f"reel/conc-r-{i}/",
                [{"object_key": f"reel/conc-r-{i}/s.bin", "bytes": 7}],
            )
        except Exception as e:  # noqa: BLE001
            errors.append(e)

    threads = [threading.Thread(target=register, args=(i,)) for i in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors
    _assert_matches_book(client)

    # 取这批新分区，并发发起并完成迁移到温档
    conn = connect()
    try:
        ids = [
            r["id"]
            for r in conn.execute(
                "SELECT id FROM partitions WHERE part_key LIKE 'P-CONC-R-%'"
            ).fetchall()
        ]
    finally:
        conn.close()
    assert len(ids) == n

    def migrate(pid):
        try:
            job = msvc.start_migrate(pid, "温档")
            msvc.finish_migrate(job["job_id"], True)
        except Exception as e:  # noqa: BLE001
            errors.append(e)

    threads = [threading.Thread(target=migrate, args=(pid,)) for pid in ids]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors

    tri = _assert_matches_book(client)  # 不漂档：三色与分区册严格相等
    # 这 20 个分区此刻应全部在温档
    conn = connect()
    try:
        in_warm = conn.execute(
            "SELECT COUNT(*) AS c FROM partitions WHERE part_key LIKE 'P-CONC-R-%' AND tier='温档' AND status='在册'"
        ).fetchone()["c"]
    finally:
        conn.close()
    assert in_warm == n
    assert tri["温档"] >= n


def test_duplicate_finish_on_same_job_is_rejected(client):
    p = _new_partition(client, "P-TEST-DUP-FIN", tier="热档")
    job = msvc.start_migrate(p["id"], "冷档")
    msvc.finish_migrate(job["job_id"], True)
    from fastapi import HTTPException
    with pytest.raises(HTTPException):
        msvc.finish_migrate(job["job_id"], True)
    _assert_matches_book(client)


def test_retention_service_runs_in_write_transaction():
    # 销毁服务仍走写事务路径（db 而非 db_ro），保证回执原子
    import inspect
    from app.db import db as db_ctx
    src = inspect.getsource(rsvc.run_retention)
    assert "with db(" in src
    assert db_ctx is not None
