from __future__ import annotations
from fastapi import APIRouter, HTTPException
from app.services import verify as svc
from app.services.distribution import cross_check

router = APIRouter(tags=["互证"])


@router.get("/目录清单")
def inventory():
    return svc.inventory_list()


@router.get("/互证流水")
def runs():
    return svc.list_verify_runs()


@router.post("/互证")
def run():
    return svc.run_verify()


@router.get("/分布对账")
def distribution_cross_check():
    """诊断页只读对账：按总览同一口径即时重算三色并自洽校验。

    诊断侧不持有、也不允许修改分布数；它能做的只有重放重算并报告是否一致。
    """
    return cross_check()


@router.post("/分布对账/改数")
def distribution_tamper_reject(_body: dict | None = None):
    """显式拒绝：诊断页改分布数。诊断改数不是登记/迁移/销毁业务回执，
    在即时重算架构下没有可改的持久分布账，整笔拒绝（403），不得落库、不得盖重算。"""
    raise HTTPException(
        status_code=403,
        detail="拒绝：诊断页不得修改三色分布；分布仅由登记/迁移完成/销毁成功回执经分区册重算生成",
    )
