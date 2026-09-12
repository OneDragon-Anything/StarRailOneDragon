"""货币战争 · 新核 mandate_v1 注册壳(生产注册面;策略统一迁移批后形态)。

``strategies/`` 是生产注册面(StrategyManager 只扫描本目录顶层 BUILTIN 源,
忽略 ``impl/`` 子包);实现本体在 ``strategies/impl/mandate_v1/bridge.py``
(不在扫描面内)。本文件是桥:零逻辑复制的壳子类——``__module__`` 守卫
(只注册「定义于本模块」的类)要求壳子类在此定义。manager 另在 discover
收尾强制注册本壳(不依赖扫描发现)。

本壳(app 桶)同时承载**步3 装配缝**(换核 R191 裁决:装配链注入收拢
本壳,impl 桶保持纯函数面;裁决原文已删档,取回口径=ADR-0644):
obs→Snapshot
装配半部(``decision_assembly.snapshot_from_obs``)与
``impl.mandate_v1.assembly.assemble`` import 执行面/app 桶词汇,impl 桶禁依
(adapter 分拆先例)——装配链在此覆写注入,impl 桶保持纯函数面
(``bridge.decide_from_turn``)。
"""
from __future__ import annotations

from sr_od.application.currency_war.decision_assembly import snapshot_from_obs
from sr_od.application.currency_war.kernel.cw_prep_actions import (
    PrepObservation,
)
from sr_od.application.currency_war.strategies.impl.cw_strategy import (
    StrategySession,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.assembly import (
    assemble,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.bridge import (
    MandateV1Strategy,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.turn_state import (
    TurnState,
)


class MandateV1Live(MandateV1Strategy):
    """mandate_v1 生产注册壳:零决策逻辑复制,全部行为继承 ``MandateV1Strategy``。

    唯一覆写 = 装配缝(``_assemble_turn``):``snapshot_from_obs`` →
    ``impl.mandate_v1.assembly.assemble``(读同一黑板 prep_obs_frame,
    幂等/单一写端/快照拷贝纪律保持;registry 经 ``self.registry`` 单源
    注入,P6)。类属性重申仅为注册面自描述(GUI 显示/StrategyInfo 元数据);
    实现单一源在 ``strategies/impl/mandate_v1/``,改行为去那边,别在此加逻辑。
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
