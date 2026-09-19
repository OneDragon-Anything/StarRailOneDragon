"""sim 重做·相位枚举与观测帧(重做设计稿 §2.0.1 交互模型)。

相位枚举 = 实机画面对应的交互状态机,与画面建档
(``docs/game/screens/currency_war_*.md``)一一对应,策略器据此路由
决策(与实机 flow 层同构)。

观测帧 = 容器 ``GameState`` 快照引用 + 相位(设计稿 §2.0.1「sim 输出
的观测帧 = 容器 GameState 快照 + 相位」)。帧携带的选项载荷按相位
填充:加相位 = 加观测帧字段,策略接口稳定(§2.5 候选 B 定稿理由②)。
sim 是唯一状态推进者;帧只读呈现 sim 真值,不含评判面。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from sr_od.application.currency_war.kernel.cw_events import (
    EncounterOption,
    SupplyOption,
)
from sr_od.application.currency_war.kernel.cw_game_state import (
    GameState,
    NodeKey,
)


class CwSimPhase(Enum):
    """交互相位(设计稿 §2.0.1 相位枚举,值 = 实机画面对应状态机名)。"""

    #: 开局投资环境选卡(RunConfig.env_present 为真时;U07②开局无策略选卡)
    OPENING_ENV = 'opening_env'
    #: 备战(商店/买/升/部署/卖)
    PREP = 'prep'
    #: 局中投资策略选卡(U07 固定轮次 P1r3/P2r2/P3r2 各一次)
    INVEST_OFFER = 'invest_offer'
    #: 遭遇选档(M16)
    ENCOUNTER_OFFER = 'encounter_offer'
    #: 补给 3 选 1(M18)
    SUPPLY_PICK = 'supply_pick'
    #: 补给箱 4 选 1 装备(M17)
    BOX_PICK = 'box_pick'
    #: 晶矿逐晶矿点选(M17)
    REWARD_BALL = 'reward_ball'
    #: 事件浮层族(巨星/伙伴/专家邀请/Fate/骇入等,M22)
    EVENT_OVERLAY = 'event_overlay'
    #: 节点结算(M12)
    SETTLEMENT = 'settlement'
    #: 位面过渡(M03)
    PLANE_TRANSITION = 'plane_transition'
    #: 局终(HP 归零/P3 未观测披露/节点走完)
    GAME_OVER = 'game_over'


#: 选卡族相位(帧 options 载荷的消费者;环境/策略 offer 共用结构,U08
#: 「环境 offer 结构与 U07 同构」)。
CARD_OFFER_PHASES: frozenset[CwSimPhase] = frozenset({
    CwSimPhase.OPENING_ENV,
    CwSimPhase.INVEST_OFFER,
})


@dataclass(frozen=True)
class RewardBall:
    """晶矿面板一晶矿(M17/U23:晶矿内容入账语义;分布参数候实机数据,
    首版以实测样本单例披露)。"""

    #: 晶矿档位色签(实测样本 1 大金晶矿+5 蓝晶矿+2 灰晶矿;词表随 U23 回填定型)
    color: str
    #: 内容物描述(金/装备名/角色名/补给箱;入账通道按内容分派)
    content: str


@dataclass(frozen=True)
class CwSimObservation:
    """观测帧:相位 + 容器权威态 + 相位载荷(策略接口稳定面)。"""

    phase: CwSimPhase
    #: 容器单例(sim 真值已写 obs 渠道;策略读口与 live 同构)
    gs: GameState
    #: 当前节点键(prep 族相位的局内坐标;GAME_OVER 帧保留末节点)
    node: NodeKey
    #: 选卡族候选卡名(invest_offer/opening_env;三选一语义,U08 首版 3 张)
    options: tuple[str, ...] = ()
    #: 补给 3 选项(supply_pick)
    supply_options: tuple[SupplyOption, ...] = ()
    #: 遭遇档位集(encounter_offer;U22 定稿口径结构占位)
    encounter_options: tuple[EncounterOption, ...] = ()
    #: 箱候选装备名(box_pick,4 选 1)
    box_options: tuple[str, ...] = ()
    #: 晶矿面板(reward_ball;逐晶矿点选)
    balls: tuple[RewardBall, ...] = ()
    #: 浮层类别名(event_overlay;megastar/partner/expert/planner/fate/aha/hack)
    overlay_kind: str = ''
    #: 浮层选项文本(event_overlay)
    overlay_options: tuple[str, ...] = ()
    #: 随局披露面(sim-only 简化档采样值/当用区间/未建模清单;纯观测,
    #: 重做设计稿保真度分层声明「逐局披露」的载体)
    disclosures: dict[str, object] = field(default_factory=dict)
