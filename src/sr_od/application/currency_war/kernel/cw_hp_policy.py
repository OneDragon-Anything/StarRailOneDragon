"""货币战争 hp 施门 kernel 政策层(决策消费面的统一门 + 可信位读口)。

**辖域**:决策内存消费面消费 hp 前对「门前真值」施加的政策修正单点。
容器 ``GameState.hp`` 是门前真值(记录面,不经门,fields.md §3.2.13);
门后消费值不入记录。两层接口:

1. :func:`apply_hp_freshness_gate` —— 结算新鲜度门**本体**(纯函数,显式参数、
   零 session/容器依赖);
2. :func:`decision_hp` —— 决策读口(装配层:容器真值 + 结算锚 + 时基派生
   装配后调门本体);
3. :func:`hp_decision_trusted_of` —— hp 决策可信位容器版单一实现(定谳二:
   ``bs.hp.source in ('observation', 'carried')``)。

**依赖方向**:本模块只 import kernel 内类型(类型注解经 TYPE_CHECKING),
禁反向依赖策略实现层(策略层 ``strategies/impl/cw_strategy.gated_hp`` 改
薄委托本模块门本体,消费点零改动续用)。

**消费同门申报纪律**(承接 ADR-0583 §2.4):新增 hp 决策消费点要么经
:func:`decision_hp` / 上游门后值传递,要么登记豁免。豁免清单 = 记录面
(journal 快照/遥测 recorder/局终写口)+ 写侧对账面(``cw_reconcile``)+
投影过渡桥(``board_state_bridge`` 搬运)+ 逻辑写端(效果账本 hp 支付)。
kernel 决策簇挂账读点(``cw_comps.maybe_pivot`` 保命分位 /
``cw_performance.is_run_dead`` 死局门,生产调用面现空、测试仓经桥调用)
重挂生产消费时必经本层读口,禁按旧注释直读 ``bs.hp.value``。

门幂等(同 gap 窗内重复施门值不变):读口可在装配层与消费层叠加施门而不
判分叉——过渡期(统一 state 迁移,详见 r5-migration-plan.md)CwWorkFrame 帧
hp 已被上游施门,经桥视图再过本门值不变。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_game_state import GameState
    from sr_od.application.currency_war.kernel.cw_strategy_session import (
        StrategySession,
    )

#: 可信窗宽度:仅紧邻上一节点(gap==1)的结算值可覆盖现读。
#: 值 = ``gated_hp`` 现行字面提取(语义依据 = 该函数 docstring r68/r69
#: 实证记录:结算屏「小队生命值NN」权威,防陈 hp 冻结毒化)。
HP_FRESH_GAP_TRUSTED: int = 1

#: 不可信放宽窗上界:现读不可信时放宽到 gap≤3(hp 只在战斗结算变,
#: 非战斗节点隔断时结算值本就仍真;r69 实证:r5 非战斗 + r6 现读失败
#: → 旧 gap==1 判陈旧回退 100 假值喂 pivot);窗外(结算连失,如 boss
#: conf=0 冻结场景)仍拒。
HP_FRESH_GAP_UNTRUSTED_MAX: int = 3


def apply_hp_freshness_gate(current_hp: int | None, last_hp: int | None,
                            last_t: int | None, now_t: int | None,
                            current_readable: bool) -> int | None:
    """结算新鲜度门本体(语义与波 2 前策略层 ``gated_hp`` 逐位等价)。

    - 锚缺任一(``last_hp``/``last_t``/``now_t`` 为 None)→ 恒等返回
      ``current_hp``(None 现读恒等支穿透,ADR-0491);
    - 锚全时 ``gap = now_t - last_t``:可信窗(``gap ==
      HP_FRESH_GAP_TRUSTED``)与放宽窗(``current_readable=False`` 且
      ``HP_FRESH_GAP_TRUSTED < gap <= HP_FRESH_GAP_UNTRUSTED_MAX``)→
      返回 ``last_hp``,窗外返回 ``current_hp``。
    - **None 语义**:门不产兜底值;None 现读非恒等豁免——锚全时在窗内
      同样被结算值覆盖(现役同型语义:门只决定「是否被结算值覆盖」),
      窗外 None 穿透为 None,消费面按 ADR-0495 保守(血线条件不触发/
      授权位 fail-closed)。
    - **幂等**:门后值再过门不变(同 gap 窗内重复施门值不变)。
    - **时基契约**:``now_t``/``last_t`` 必须同式派生——产出位统一经
      ``cw_plane_table.node_t_of``(前序位面实际长度和 + 轮次;schedule
      回退态与旧字面量 ``(plane-1)*9+round_num`` 逐位相同)。结算锚写点
      (``cw_screen_battle_wait`` → ``session.last_hp_t``)与决策读口
      (:func:`decision_hp` 及策略层 gated_hp 消费位)禁单侧改式,单侧
      改式 = gap 判域静默漂移。**迁移期申报**:cw_screen_prep 环入口路径
      两处 now_t 写侧预施门仍为旧字面量(禁触在飞面,统一 state prep 链线
      辖域;原终饰两点已随旧链删除消亡),其消费切换挂 prep 链批次(P3 段
      该两处与锚新式混算 gap=3,值面影响=现读优先于结算优先的覆盖选择,
      值通常一致;边界 P2r7→P3r1 与锚缺席态行为不变)。
      ``NodeKey`` 缺席 → ``now_t=None`` = 恒等支;与现役 adapter 形态
      (缺省 plane/round=1 → t=1)在锚在场时 gap≤0 判负同回
      ``current_hp``,行为等价。
    """
    if last_hp is None or now_t is None or last_t is None:
        return current_hp
    gap = now_t - last_t
    if gap == HP_FRESH_GAP_TRUSTED or (
            not current_readable
            and HP_FRESH_GAP_TRUSTED < gap <= HP_FRESH_GAP_UNTRUSTED_MAX):
        return last_hp
    return current_hp


def _node_t_of(bs: GameState, session: StrategySession) -> int | None:
    """决策时基读口(单一源 = ``cw_plane_table.node_t_of``,schedule 派生,
    与结算锚写点同式禁单侧改式,见 :func:`apply_hp_freshness_gate` 时基
    契约);NodeKey 缺席 = None = 门恒等支。"""
    node = bs.node.value
    if node is None:
        return None
    from sr_od.application.currency_war.kernel.cw_plane_table import node_t_of
    return node_t_of(session, node.plane, node.round_num)


def decision_hp(bs: GameState, session: StrategySession) -> int | None:
    """决策面 hp 读口(门后消费值;hp 决策消费点统一经本口,禁旁路直读
    ``bs.hp.value`` 手写第二门)。

    装配序:门前真值 = ``bs.hp.value``;``current_readable`` =
    ``bs.hp.source == 'observation'``(定谳二·本帧真读位,「最近观察」
    语义);``now_t`` 自 ``bs.node`` 派生(NodeKey 缺席 → None);
    ``last_hp``/``last_t`` = session 结算锚(鸭子属性读,缺席 = None →
    门恒等支)。可信位判定另经 :func:`hp_decision_trusted_of`,禁与本口
    混写双位判定。
    """
    last_hp = getattr(session, 'last_hp', None)
    last_t = getattr(session, 'last_hp_t', None)
    return apply_hp_freshness_gate(
        bs.hp.value, last_hp, last_t, _node_t_of(bs, session),
        bs.hp.source == 'observation')


def hp_decision_trusted_of(bs: GameState) -> bool:
    """hp 决策可信位容器版单一实现(定谳二):
    ``(bs.hp.source in ('observation', 'carried'))``。

    映射保序(旧口径 ``hp_readable or hp_trusted`` 在容器来源二分下恒等):
    observation ⊆ 两支并集;carried 支 = 沿用真值帧放行语义(ADR-0428,
    ADR-0431 同节点帧龄门收编后的容器形态);prior(开局先验,ADR-0559)/
    logic(推算值)支两位皆 False = fail-closed(ADR-0448 血线谓词唯一
    收口 / ADR-0495 None 保守)。``sig.quality['hp']`` 词表
    (real_read/prior/same_node_carried)保留为判读证据,不参与决策位。
    语义只在生产容器单例上成立——过渡桥/合成口产出的视图 hp source 恒
    observation(可信位恒 True,失真申报面在桥 docstring 与迁移方案)。
    新增可信位消费点一律走本函数(容器消费形态)或
    ``cw_discipline_rules.hp_decision_trusted``,禁手写双位判定
    (W393 A1.1 单一源纪律)。
    """
    return bs.hp.source in ('observation', 'carried')
