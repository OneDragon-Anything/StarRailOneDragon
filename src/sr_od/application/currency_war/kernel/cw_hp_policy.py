"""货币战争 hp 施门 kernel 政策层(决策消费面的统一读口)。

**辖域**:决策内存消费面消费 hp 的统一读口单点。终态契约(2026-09-16-
strategy-terminal-contract)识别防御锚退役后,本层收敛为 **gs.hp 直读**:
「上一真值」职责由结算覆盖写端(``cw_screen_battle_wait`` §3.5.1)+
carried 语义(fields.md §2.1)承载;旧结算新鲜度门
(``apply_hp_freshness_gate``,session.last_hp/last_hp_t 锚 + gap 窗)
随锚退役删除——失读窗不再有锚补,实机识别失准走识别优化批
(design §1.3 用户裁定,行为变化登记)。

**依赖方向**:本模块只 import kernel 内类型(类型注解经 TYPE_CHECKING),
禁反向依赖策略实现层(策略层 ``strategies/impl/cw_strategy.gated_hp``
已随锚退役删除,消费点改经本模块 :func:`decision_hp`)。

**消费同门申报纪律**(承接 ):新增 hp 决策消费点要么经
:func:`decision_hp` / 上游门后值传递,要么登记豁免。豁免清单 = 记录面
(journal 快照/遥测 recorder/局终写口)+ 写侧对账面(``cw_reconcile``)+
帧→视图一次性装配面(过渡桥语义,现役存续面见登记集哨兵)+
逻辑写端(效果账本 hp 支付)。
kernel 决策簇挂账读点(``cw_comps.maybe_pivot`` 保命分位 /
``cw_performance.is_run_dead`` 死局门,生产调用面现空、测试仓经桥调用)
重挂生产消费时必经本层读口,禁按旧注释直读 ``gs.hp.value``。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_game_state import GameState
    from sr_od.application.currency_war.kernel.cw_strategy_session import (
        StrategySession,
    )


def decision_hp(gs: GameState, session: StrategySession) -> int | None:
    """决策面 hp 读口(hp 决策消费点统一经本口,禁旁路直读
    ``gs.hp.value`` 手写第二门)。

    终态契约 §A:session 结算锚(last_hp/last_hp_t)与新鲜度门随防御
    缓存退役删除,本口 = ``gs.hp`` 直读——「上一真值」由结算覆盖写端 +
    carried 语义承载(失读窗行为变化登记 design §1.3)。``session``
    形参保留 = 消费点签名稳定(终态切换批随 kernel 参数清单复核定夺)。
    可信位判定另经 :func:`hp_decision_trusted_of`,禁与本口混写双位判定。
    """
    return gs.hp.value


def hp_decision_trusted_of(gs: GameState) -> bool:
    """hp 决策可信位容器版单一实现(定谳二):
    ``(gs.hp.source in ('observation', 'carried'))``。

    映射保序(旧口径 ``hp_readable or hp_trusted`` 在容器来源二分下恒等):
    observation ⊆ 两支并集;carried 支 = 沿用真值帧放行语义(
    同节点帧龄门收编后的容器形态);prior(开局先验)/
    logic(推算值)支两位皆 False = fail-closed(血线谓词唯一
    收口 / None 保守)。``sig.quality['hp']`` 词表
    (real_read/prior/same_node_carried)保留为判读证据,不参与决策位。
    语义只在生产容器单例上成立——过渡桥/合成口产出的视图 hp source 恒
    observation(可信位恒 True,失真申报面在桥 docstring 与迁移方案)。
    新增可信位消费点一律走本函数(容器消费形态)或
    ``cw_discipline_rules.hp_decision_trusted``,禁手写双位判定
    (W393 A1.1 单一源纪律)。
    """
    return gs.hp.source in ('observation', 'carried')
