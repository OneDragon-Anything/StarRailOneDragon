"""W62 件1:恢复局(locked-resume)检测纯函数(ADR-0329)。

对局中进入过战斗后 exe 异常退出,重进继续该局回备战画面 = 游戏侧锁定
「只能出战」——商店按钮点击零响应(实锤,currency_war_prep.md:16)。bot 接手
(启动时 session 全新但画面在非 1-1 备战态)会走备战分支 → PrepDirector →
策略发开商店 → 点击落空 → 重试链耗尽 → run 失败(根因=流程层缺状态判定)。

本模块把 battle_loop 备战分支的**判定/探针裁决/锁定解除**抽成纯函数(单帧锁
可测),运行时只做薄接线(见 operations/battle_loop.py 备战分支稳定门后)。
"""
from __future__ import annotations


def resume_candidate(is_new_match: bool, plane: int, round_num: int) -> bool:
    """恢复局候选判据(W62 设计章1.2):新 match(无本局记录)+ 首个备战相位 round>1。

    - ``is_new_match=True``(session 全新,不可能有本局任一轮真实决策/结算记录)
      且 ``round_num>1`` 或 ``plane>1`` → True(恢复局候选,需探针确认);
    - ``is_new_match=True`` 且 ``round_num==1``/``plane==1`` → False(正常新局 r1);
    - ``is_new_match=False``(cw_match 已在,续跑/局中)→ 恒 False(不进入检测)。
    """
    if not is_new_match:
        return False
    return round_num > 1 or plane > 1


def probe_resolve(shop_opened_after_click: bool) -> str:
    """探针裁决(W62 设计章1.3):一次「点商店→验『按钮-收起』出现」。

    锁定唯一可观测特征 = 商店按钮零响应(实锤)。商店可开 = 非锁定('normal');
    不可开 = 锁定确认('locked')。返回词与调用方分支一一对应。
    """
    return 'normal' if shop_opened_after_click else 'locked'


def locked_after_start_battle(progressed: bool) -> bool:
    """锁定模式出战结果 → 锁标志是否保留(W62 设计章1.5 解除条件)。

    ``progressed=True``(StartBattle 完成验证:备战标识消失,出战成功)→ False(解除,
    游戏侧锁定随该节点出战解除,下个备战相位落常规循环);``False``(出战未落地)
    → True(保锁重试,连续失败由 stall 哨兵/unknown 兜底,不新增死循环路径)。
    """
    return not progressed
