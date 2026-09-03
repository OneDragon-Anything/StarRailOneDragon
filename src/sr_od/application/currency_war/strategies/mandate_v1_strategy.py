"""货币战争 · 新核 mandate_v1 注册桥(照抄 DecisionV2Live 模式)。

``strategies/`` 是生产注册面(StrategyManager 只扫描本目录 BUILTIN 源);
实现本体在 ``decision/cw4/bridge.py``(不在扫描面内)。本文件是桥:
零逻辑复制的壳子类——``__module__`` 守卫(只注册「定义于本模块」的类)
要求壳子类在此定义(ADR-0290 同款;见 decision_v2_strategy.py 头注)。

本壳(app 桶)同时承载**步3 装配缝**(§6.4-R R191 裁决):obs→Snapshot
装配半部(``decision_assembly.snapshot_from_obs``)与 ``prep_brain.assemble``
import 执行面/app 桶词汇,decision 桶禁依(adapter 分拆先例)——装配链在
此覆写注入,decision 桶保持纯函数面(``bridge.decide_from_turn``)。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from sr_od.application.currency_war.decision.cw4.bridge import (
    MandateV1Strategy,
)
from sr_od.application.currency_war.decision.decision_v2.prep_brain import (
    assemble,
)
from sr_od.application.currency_war.decision_assembly import snapshot_from_obs

if TYPE_CHECKING:
    from sr_od.application.currency_war.decision.cw_strategy import (
        StrategySession,
    )
    from sr_od.application.currency_war.decision.decision_v2.turn_state import (
        TurnState,
    )
    from sr_od.application.currency_war.kernel.cw_prep_actions import (
        PrepObservation,
    )


class MandateV1Live(MandateV1Strategy):
    """mandate_v1 生产注册壳:零决策逻辑复制,全部行为继承 ``MandateV1Strategy``。

    唯一覆写 = 装配缝(``_assemble_turn``):``snapshot_from_obs`` →
    ``prep_brain.assemble``(读同一黑板 prep_obs_frame,幂等/单一写端/
    快照拷贝纪律保持;registry 经 ``self.registry`` 单源注入,P6)。
    类属性重申仅为注册面自描述(GUI 显示/StrategyInfo 元数据);
    实现单一源在 ``decision/cw4/``,改行为去那边,别在此加逻辑。
    """

    STRATEGY_ID: str = 'mandate_v1'
    STRATEGY_NAME: str = '新数学框架核(mandate_v1;三遍化决策序)'
    AUTHOR: str = 'OneDragon'
    VERSION: str = '0.1'
    DESCRIPTION: str = ('cw4 新核:证明 pass→升档器求值位→骨架 pass'
                        '(M1-M7)→EV pass(criteria 七面);序列契约 v2'
                        ' 帧稳定截断发射')

    def _assemble_turn(self, obs: PrepObservation,
                       session: StrategySession) -> TurnState:
        return assemble(snapshot_from_obs(obs, session), session,
                        registry=self.registry)
