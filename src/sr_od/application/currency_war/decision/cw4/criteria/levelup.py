"""criteria/levelup——升级面判据(§2.3;M3 触发信号 arm1_existence 在
statefn/predicates,不在本域)。

D-BUYNOTE(修复池执行层附注,随批收编):新核买牌/升级发射器内嵌
P48 整买纪律常量判据——``spend_unified`` = XP 仅整批够升级时放行
(181254 r7/r8 各 4 金散买 XP 零收益的防复发锚)。
D-lv7(OPEN 检查点):``pop_slot`` 对「满编+富金+bench 有候补」的
覆盖核查——本模块 ``pop_slot`` 落位并显式给不触发理由进决策迹。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

# 满级(注册表 LEVEL_CAP 同值;pop_slot/lv9_stop 消费)
LEVEL_CAP: int = 9


def arm2_schedule(gold: int, cap_resolved: int, *, gate_open: bool = False,
                  ) -> bool:
    """arm2 调度门(R5-4 范畴定谳:门,无发射;臂①=门关闭恒 false)。

    结构守息门(R26-H1 后保留成分):金下限 g*=10×cap_resolved
    (L-R3-3 引理 1 同源,零 λ 依赖)——arm2 触发的调度类批金条件。
    ``gate_open`` = 升档器信号位(血线地板触发帧解锁:g*→0,R28-2;
    λ 顾问触发帧延迟 arm2 调度类批 ⇒ false)。
    """
    floor = 0 if gate_open else saturation_floor(cap_resolved)
    return gold >= floor


def saturation_floor(cap_resolved: int) -> int:
    """守息线 g* = 10×cap_resolved(单一源=statefn/interest.saturation_line
    的重导出消费口,禁另算)。"""
    from sr_od.application.currency_war.decision.cw4.statefn.interest import (
        saturation_line,
    )
    return saturation_line(cap_resolved)


def spend_unified(clicks_to_next: int, gold: int, click_cost: int) -> bool:
    """P48 整买纪律(D-BUYNOTE):整批 XP 放行判据。

    仅当「一次买齐到下一级」的金够付时放行(clicks×click_cost ≤ gold)
    ——散买 XP(买不够升级)零收益,拦截。M3 义务侧消费(不旁路)。
    """
    if clicks_to_next <= 0:
        return False
    return gold >= clicks_to_next * click_cost


def batch_form(level: int, target_level: int) -> bool:
    """批量成型判据(M3 批形态:目标级差>0 才有批;义务侧消费)。"""
    return level < target_level


def lv9_stop(level: int) -> bool:
    """满级停(LEVEL_CAP=9;义务侧消费)。"""
    return level >= LEVEL_CAP


def pop_slot(deployed_count: int, deploy_cap: int, gold: int,
             bench_candidates: int, floor_gold: int) -> tuple[bool, str]:
    """D-lv7(OPEN 检查点):「满编+富金+bench 有候补 → 升 cap 上人」覆盖。

    返回 (是否发射升 cap 意图, 决策迹理由——不触发时显式理由,
    R189-5 D-lv7 行:「判据合法不触发须显式理由进决策迹」)。
    """
    if deployed_count < deploy_cap:
        return False, 'not_full'          # 未满编:普通 M1 部署辖
    if bench_candidates <= 0:
        return False, 'no_bench_candidate'
    if gold < floor_gold:
        return False, 'gold_below_floor'
    return True, 'full_rich_with_candidate'
