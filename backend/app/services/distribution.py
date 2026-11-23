"""三色分布的唯一生成口径（全局架构：打开总览即时重算，无持久分布账）。

口径（DISTRIBUTION_CALIBER）：
  取分区册 partitions 中 status='在册' 的分区，按 tier（温层列）分组计数。

不变量：
  1. 唯一事实源是分区册温层列；本模块不写任何表、不落快照、不读互证流水。
  2. replay_distribution 是纯函数：给定同一批分区册行，任意时刻重放结果一致，
     诊断页（互证）改任何数都无法影响它——诊断不是业务回执，盖不住重算结果。
  3. 三类业务回执（登记/迁移完成/销毁成功）只改分区册，且在各自单事务内原子提交；
     因此重算结果与分区册永远同刷，不存在“分布条已变、分区册未变”的中间态。
"""
from __future__ import annotations

from app.config import TIERS
from app.db import db_ro

# 选定口径标识，随接口返回，便于按口径重放与排错。
DISTRIBUTION_CALIBER = "在册分区按温层列即时分组重算"
# 架构标识：全局只此一种，禁止与“分布账世代”口径混用。
DISTRIBUTION_ARCH = "recompute_on_open"


def replay_distribution(partition_rows) -> dict:
    """纯函数：由分区册行重放三色分布。

    入参为可迭代的映射（sqlite3.Row / dict 均可），每行至少含 tier、status。
    输出固定三档键，缺失档位为 0，并附在册总数。同输入必同输出（可重放）。
    """
    counts = {tier: 0 for tier in TIERS}
    on_book = 0
    for row in partition_rows:
        if row["status"] != "在册":
            continue
        on_book += 1
        tier = row["tier"]
        # 非约定温层不计入三色，避免脏数据伪装成某一档
        if tier in counts:
            counts[tier] += 1
    return {
        "口径": DISTRIBUTION_CALIBER,
        "架构": DISTRIBUTION_ARCH,
        "在册总数": on_book,
        "三色": {tier: counts[tier] for tier in TIERS},
    }


def current_distribution(conn=None) -> dict:
    """从分区册即时重算当前三色分布（总览唯一入口）。"""
    def _q(c):
        rows = c.execute("SELECT tier, status FROM partitions").fetchall()
        return replay_distribution(rows)

    if conn is not None:
        return _q(conn)
    with db_ro() as c:
        return _q(c)


def cross_check(conn=None) -> dict:
    """片库诊断对账：独立重算三色分布，校验各档之和与在册总数自洽。

    诊断侧只读分区册、只出对账结论，不产生业务回执、不修改任何分布数；
    对不上时给出明确拒因，绝不假装绿。
    """
    def _q(c):
        rows = c.execute("SELECT tier, status FROM partitions").fetchall()
        dist = replay_distribution(rows)
        on_book = c.execute(
            "SELECT COUNT(*) AS c FROM partitions WHERE status='在册'"
        ).fetchone()["c"]
        tier_sum = sum(dist["三色"].values())
        consistent = tier_sum == dist["在册总数"] == on_book
        return {
            "一致": consistent,
            "口径": dist["口径"],
            "架构": dist["架构"],
            "在册总数_独立计数": on_book,
            "三色重算": dist["三色"],
            "三色之和": tier_sum,
            "拒因": None if consistent else "三色之和与在册分区数不一致，分区册存在非约定温层或脏数据",
        }

    if conn is not None:
        return _q(conn)
    with db_ro() as c:
        return _q(c)
