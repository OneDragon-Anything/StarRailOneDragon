"""货币战争 · decision_v2 序列契约适配器(DecisionV2SeriesAdapter)。

序列决策契约 v1(dd-020,2026-09-03 冻结)§1「迁移期适配(并行使能)」的
**包装形态**实现:现役单动作核(``DecisionV2Strategy``)包一层长度 1 序列的
适配器,行为与现状逐动作重决策等价;新核 = 同接口替换。

为什么是包装子类而非原位改 ``DecisionV2Strategy``(R192 症2,编排者裁决
2026-09-03):①契约 v1 §1 冻结文字即「包一层长度 1 序列的适配器」;
②``decision_v2`` 是换核 A/B 的**冻结基线**(IMPL_DESIGN §4.1「不改一行」
辖 ``decision/decision_v2/strategy.py``)——基线臂必须保持单动作原状,
A/B 对拍与 sim 零漂移门才有不动的参照系;③接口形态由本包装承载,生产经
注册桥(``strategies/decision_v2_strategy.py`` 的 ``DecisionV2Live``)拿到
包装实例,``strategy_id='decision_v2'`` 语义不变。

MRO 注意:本类同时覆写 deprecated 别名 ``decide_prep_action``——父类的
别名实现经 ``self.decide_prep_screen`` 动态派发,若不覆写会落到本包装的
list 返回上,破坏「别名 = 单动作」的存量契约。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from sr_od.application.currency_war.decision.decision_v2.strategy import (
    DecisionV2Strategy,
)

if TYPE_CHECKING:
    from sr_od.application.currency_war.decision.cw_strategy import StrategySession
    from sr_od.application.currency_war.kernel.cw_prep_actions import (
        PrepAction,
        PrepObservation,
    )


class DecisionV2SeriesAdapter(DecisionV2Strategy):
    """长度 1 序列适配器(dd-020 契约 §1;R192 症2 包装形态)。

    - ``decide_prep_screen(session, config) -> list[PrepAction]``:
      ``[父类单动作输出]``——只包壳不改决策,恒长度 1(父类规则序恒出
      动作,含 DeferSpheres 兜底,空批不可达)。
    - ``decide_prep_action(obs, session, config)``:deprecated 别名单动作
      语义保持(写黑板 → 父类单动作接口;见模块 docstring 的 MRO 注意)。
    - 其余钩子全继承冻结基线,零逻辑复制。
    """

    def decide_prep_screen(self, session: StrategySession,
                           config: object) -> list[PrepAction]:
        """契约 v1 接口形态:返回 ``[父类单动作]``(长度 1,dd-020 §1)。"""
        return [super().decide_prep_screen(session, config)]

    def decide_prep_action(self, obs: PrepObservation,
                           session: StrategySession,
                           config: object) -> PrepAction:
        """deprecated 别名(单动作语义保持):写黑板 → 父类单动作接口。

        不经本类 list 覆写(动态派发会破坏别名契约,见模块 docstring)。
        """
        session.prep_obs_frame = obs
        return super().decide_prep_screen(session, config)
