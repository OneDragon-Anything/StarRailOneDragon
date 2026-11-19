"""恢复局(locked-resume)探针裁决纯函数。

对局中进入过战斗后 exe 异常退出,重进继续该局回备战画面 = 游戏侧锁定
「只能出战」——商店按钮点击零响应(已实测确认,currency_war_prep.md:16)。
锁定唯一可观测特征 = 商店可开性 → 探针(识别性点击)是唯一裁决手段。

判据变化申报(2026-11-19-resume-rebuild design §2.3):恢复局候选判定
(旧 ``resume_candidate``:新 match ∧ 轮次/位面门)已退役——探针触发门 =
``opened_via == 'takeover' ∧ not probed``(接管局必经,含 1-1 接管照探
= 有意变更:无锁则探针必「可开」走常规,结果正确),候选判定不再以
纯函数形态存在。相位轮次读数保留于 ``Match.locked_round`` 遥测链
(读法 = cw_observation.read_phase_round,与判定解耦,锁定确认时同帧
写入)。本模块现役 = 探针裁决(probe_resolve)与锁定解除
(locked_after_start_battle)两个纯函数(单帧可测),运行时薄接入 =
operations/cw_screen/cw_screen_prep.py 段1 b 查 / 段3b。
"""
from __future__ import annotations


def probe_resolve(shop_opened_after_click: bool) -> str:
    """探针裁决:一次「点商店→验『按钮-收起』出现」。

    锁定唯一可观测特征 = 商店按钮零响应(已实测确认)。商店可开 = 非锁定('normal');
    不可开 = 锁定确认('locked')。返回词与调用方分支一一对应。
    """
    return 'normal' if shop_opened_after_click else 'locked'


def locked_after_start_battle(progressed: bool) -> bool:
    """锁定模式出战结果 → 锁标志是否保留(解除条件)。

    ``progressed=True``(出战**单击已执行**——出战域收缩语义:op 零判效,
    结束后画面由外循环下一帧重判)→ False(解除,
    游戏侧锁定随该节点出战解除,下个备战相位落常规循环);``False``(未执行)
    → True(保锁重试,连续失败由 stall 哨兵/unknown 兜底,不新增死循环路径)。
    """
    return not progressed
