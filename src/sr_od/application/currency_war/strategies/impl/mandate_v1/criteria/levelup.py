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
    from sr_od.application.currency_war.kernel.cw_registry import (
        DecisionV2Registry,
    )
    from sr_od.application.currency_war.kernel.cw_state import (
        GameState,
    )
    from sr_od.application.currency_war.strategies.impl.cw_strategy import (
        StrategySession,
    )

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
    from sr_od.application.currency_war.strategies.impl.mandate_v1.statefn.interest import (
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


def level_spend_blocked(state: GameState, session: StrategySession,
                        registry: DecisionV2Registry | None = None) -> bool:
    """危机带内整批经验授权让位保命面(实机复盘 g_20260904_054904
    p2r1 候选③:hp=1 败即死帧 9×LevelUpShop 36g,m3_batch 批授权把
    67% 金转为本帧零收益经验)。M3 发射位(mandate/shop 两域)消费。

    两支,全部单一源判据,零新自由参数:
    - ``discipline.blood_budget_levelup_blocked``(decision_v2 同源,
      P21 已证:hp ≤ 停升级线内升级收益到账 ≥1 战之后,EV=−C−I 严格
      负,敏感网格全负域免 β)——cw4 栈 M3 此前未消费该门,同帧
      decision_v2 侧已停、cw4 侧照发 = 双栈语义断层(p2r1 实证帧);
    - P2 危机带 ``discipline.p2_crisis_band``(hp ≤ ceil(2×vd_p2_loss)
      ≈41 = P21 d=2「到账更慢」档;经验收益兑现链 ≥2 战,与危机带
      搜索停付同一判据、同一血线单一源——P48 三段管辖 λ>0 段
      「转化优先、S 线降级」;与 arbiter._crisis_buy_gate_open 同语义
      族成对:停未来面、开当轮转化面)。
    ALL IN 豁免(位面末 boss 战花光,[18])两支共享——blood_budget_
    levelup_blocked 内含,危机支同判让位(末战花光是时机不是血线
    判断)。hp 不可信帧由 blood_budget 支 fail-closed 拒付(危机会
    在内)。
    """
    from sr_od.application.currency_war.kernel.cw_discipline_rules import (
        blood_budget_levelup_blocked,
        p2_crisis_band,
    )
    from sr_od.application.currency_war.kernel.cw_registry import (
        DEFAULT_REGISTRY,
    )
    reg = registry if registry is not None else DEFAULT_REGISTRY
    if blood_budget_levelup_blocked(state, session, reg):
        return True
    if _plane_last_battle(state, session):
        return False    # ALL IN 窗:停手让位(与血预算支同一豁免序)
    return p2_crisis_band(state, reg)


def _plane_last_battle(state: GameState, session: StrategySession) -> bool:
    """位面末最后一战判定(cw4 消费面;单一源 =
    decision_v2.discipline.plane_last_battle 的重导出委托,禁第二实现;
    模块私有——非判据面函数,不入契约/旁路枚举表)。"""
    from sr_od.application.currency_war.kernel.cw_discipline_rules import (
        plane_last_battle as _plb,
    )
    return _plb(state, session)


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
