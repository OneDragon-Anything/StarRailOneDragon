"""cw4 桥:mandate_v1 决策本体(decision 桶纯函数面)。

新核形态 = 新 ``CwStrategy`` 子类,STRATEGY_ID='mandate_v1'(§4.1 新
strategy_id 双被测体;config 切 strategy_id 即换核)。实现体分两层:

- 本模块(decision 桶,纯函数):``decide_from_turn`` = 三遍编排 + 帧
  稳定截断(依赖矩阵:decision 只可依 data/kernel——obs→Snapshot 的
  装配半部 import 执行面词汇,归 app 桶 ``decision_assembly.py``,
  decision_v2/adapter.py 头注同款分拆先例);
- 注册桥壳 ``strategies/mandate_v1_strategy.py``(app 桶):持有
  obs→snapshot→assemble 装配链(步3 内部装配缝:``prep_brain.assemble``
  读同一黑板 ``session.prep_obs_frame``,④-5 单一源;幂等/单一写端/
  快照纪律保持;生产路径保持「cw_screen_prep 只写黑板+调一个 decide」,
  契约 §5 职责分界,**不加生产接线步**,R191 裁决)。

商店线口径(步4b,STEP34_REPORT 裁量 #1 的接线兑现):
``decide_shop_screen`` = cw4 商店波决策(``cw4/shop.decide_shop_wave``,
黑板=``session.shop_state_frame``,criteria 七面商店形态+契约 v2 §3.1
截断)——sim A/B 证明面=商店波(SIM_CONSUMPTION_MAP Q1)自此有行为载体。
``update_target`` = **透传声明**(规格未给 cw4 战略层新形态:证明层线
选择在 decide_prep_screen 三遍内承载,contract/sim 消费的战略层钩子沿用
decision_v2 的意向状态机——继承即透传,禁自创,R189-1 ④-2 ② 同款
基线零改动口径);pick 族/prep 侧生命周期钩子同缺省透传。
【R197 症2 裁决落地(编排者裁=方案 a):A/B 期换线权威=上述基线意向
状态机,两臂共用 ``update_target`` ⇒ 两臂换线行为恒等,臂间 diff 归因
不含换线路径;cw4 proof 侧 should_switch/回锁窗/干旱计数=影子面(发
遥测不写 target_comp,实装接线=过线后批)——预注册声明见
sim/ab_core_swap.py 模块 docstring。】
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from sr_od.application.currency_war.decision.cw4 import entry
from sr_od.application.currency_war.decision.decision_v2.strategy import (
    DecisionV2Strategy,
)
from sr_od.application.currency_war.kernel.cw_prep_actions import (
    DeferSpheres,
    PrepAction,
)

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
    from sr_od.application.currency_war.kernel.cw_registry import (
        DecisionV2Registry,
    )

# config 属 app 桶,decision 桶禁 import(cw_strategy.py 字符串注解先例);
# 实例由调用方(注册桥壳)按参注入。
CurrencyWarConfig = 'CurrencyWarConfig'


class MandateV1Strategy(DecisionV2Strategy):
    """新核(mandate_v1):三遍化决策序(证明→骨架→EV)+ 序列发射。

    继承 ``DecisionV2Strategy`` 复用生命周期钩子、战略层
    ``update_target``(透传声明,见模块 docstring)与 pick 族缺省实现
    (基线本体零改动,§4.1);备战线决策与商店线决策均被本类覆写为
    cw4 形态(entry 三遍编排 / shop 商店波)。
    """

    STRATEGY_ID: str = 'mandate_v1'
    STRATEGY_NAME: str = '新数学框架核(mandate_v1;三遍化决策序)'
    AUTHOR: str = 'OneDragon'
    VERSION: str = '0.1'
    DESCRIPTION: str = ('cw4 新核:证明 pass(线选择/停手线)→升档器'
                        '求值位→骨架 pass(M1-M7 义务)→EV pass(criteria'
                        ' 七面);序列契约 v2 帧稳定截断发射')

    def decide_prep_screen(self, session: StrategySession,
                           config: CurrencyWarConfig) -> list[PrepAction]:
        """备战画面黑板决策(契约 v1/v2 接口;dd-020)。

        输入 = ``session.prep_obs_frame``(黑板唯一写者=画面 op);内部
        装配缝(步3)经 ``_assemble_turn``(注册桥壳覆写注入装配链;
        本类缺省 = 未注入即抛错的可观测兜底)。输出 =
        ``list[PrepAction]``(执行序=列表序),经帧稳定截断
        (契约 §3.2 逐类判 + §3.3 fail-closed)。观察帧缺失 = 观察
        层失约,抛错(禁静默按空观察决策)。
        """
        obs = session.prep_obs_frame
        if obs is None:
            raise ValueError(
                'mandate_v1.decide_prep_screen: session.prep_obs_frame 缺失'
                '(黑板契约:画面 op 是唯一写者;None=观察层失约,'
                '禁静默按空观察决策)')
        turn = self._assemble_turn(obs, session)
        return decide_from_turn(obs, turn, session, config,
                                registry=self.registry)

    def _assemble_turn(self, obs: PrepObservation,
                       session: StrategySession) -> TurnState:
        """装配缝缺省:decision 桶无 obs→Snapshot 装配半部(app 桶
        ``decision_assembly.snapshot_from_obs``),由注册桥壳
        ``MandateV1Live`` 覆写注入(adapter 分拆头注同款先例)。"""
        raise NotImplementedError(
            'mandate_v1 装配缝未注入(注册桥壳 MandateV1Live 覆写'
            ' _assemble_turn;直接实例化本类须走注册面)')

    def decide_prep_action(self, obs: PrepObservation,
                           session: StrategySession,
                           config: CurrencyWarConfig) -> PrepAction:
        """deprecated 兼容别名(W971;序列契约后=解包首元素)。

        新核空批合法(契约 §4:本帧无动作可发)——旧单动作签名下
        空批以 ``DeferSpheres`` 控制流动作承载(本环不再尝试,交框架
        重观察;策略器禁用空批表达控制流,DeferSpheres 系词表内合法
        控制流动作)。
        """
        session.prep_obs_frame = obs
        out = self.decide_prep_screen(session, config)
        return out[0] if out else DeferSpheres()

    def decide_shop_screen(self, session: StrategySession,
                           config: CurrencyWarConfig) -> list:
        """商店开画面黑板决策(契约 v1/v2 商店线;步4b 接线)。

        输入 = ``session.shop_state_frame``(黑板唯一写者=商店观察段/
        sim 引擎);决策本体 = ``cw4/shop.decide_shop_wave``(方向/预算
        投影 → criteria 七面发射 → 截断/排序,§4.2 发射面规格);输出
        ``list[Action]``(词表=cw_state.Action 族,截断=契约 v2 §3.1
        商店线域+§3.3 fail-closed)。观察帧缺失 = 观察层失约,抛错
        (禁静默按空态决策)。rng 中立:零局内 rng 消费。
        """
        from sr_od.application.currency_war.decision.cw4 import shop
        state = session.shop_state_frame
        if state is None:
            raise ValueError(
                'mandate_v1.decide_shop_screen: session.shop_state_frame '
                '缺失(黑板契约:商店观察段是唯一写者;None=观察层失约,'
                '禁静默按空态决策)')
        return shop.decide_shop_wave(state, session, config,
                                     registry=self.registry)


def decide_from_turn(obs: PrepObservation, turn: TurnState,
                     session: StrategySession, config: object,
                     *, registry: DecisionV2Registry | None = None,
                     ) -> list[PrepAction]:
    """三遍编排 + 帧稳定截断(纯函数;R189-4 结构签名)。

    ev_arm 模式参数取 ``config.ev_arm``(缺省 full;非法值回落 full)。
    截断语境供给(R196 症5):conditional 类名-槽一致性复检消费的
    bench 占用槽位集,自黑板观察 ``obs.bench_chars`` 现读派生。
    """
    ev_arm = getattr(config, 'ev_arm', 'full')
    if ev_arm not in entry.EV_ARM_VALUES:
        ev_arm = 'full'
    emitted = entry.emit(obs, turn, session, config,
                         ev_arm=ev_arm, registry=registry)
    actions = [e.action for e in emitted]
    bench_slots = {b.slot for b in (obs.bench_chars or [])
                   if b is not None and getattr(b, 'slot', None)}
    return entry.truncate_frame_stable(actions, session,
                                       bench_slots=bench_slots)
