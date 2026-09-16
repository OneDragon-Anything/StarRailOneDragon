"""cw4 桥:mandate_v1 决策本体(decision 桶纯函数面)。

新核形态 = 新 ``CwStrategy`` 子类,STRATEGY_ID='mandate_v1'
(config 切 strategy_id 即换核)。实现体分两层:

- 本模块(decision 桶,纯函数):``decide_from_turn`` = 三遍编排 + 帧
  稳定截断(依赖矩阵:decision 只可依 data/kernel——obs→Snapshot 的
  装配半部 import 执行面词汇,归 app 桶 ``decision_assembly.py``);
- 注册桥壳 ``strategies/mandate_v1_strategy.py``(app 桶):持有
  obs→snapshot→assemble 装配链(步3 内部装配缝:``prep_brain.assemble``
  读同一黑板 ``session.prep_obs_frame``,④-5 单一源;幂等/单一写端/
  快照纪律保持;生产路径职责分界 = 画面 op 只写黑板 + 调一个决策入口,
  **不加生产接线步**,R191 裁决)。

商店线口径(步4b,STEP34_REPORT 裁量 #1 的接线兑现;ADR-0517 迁移批
后形态):
``decide_shop_screen`` = 序列兼容驱动器(循环调 ``shop.decide_shop_action``
单动作核,黑板=``session.prep_obs_frame`` + 容器单例
``game_state_of(session)``;生产执行侧入口 =
``decide_shop_action``,由 cw_op_buy_cards.run_buy_waves 单动作循环消费)
——sim A/B 证明面=商店波(SIM_CONSUMPTION_MAP Q1)自此有行为载体。
该驱动器自 ADR-0583 起降格出 ABC(基类缺省实现 = flow 层通用循环;
本类覆写保留 mandate 特有记账:已买件名单/段序号/续段 token)。
战略层方向重估自 ADR-0583 起内化进策略器(flow 层
``_refresh_direction``,触发 = 黑板帧刷新代次标注)——旧「透传声明」
(规格未给 cw4 战略层新形态,R189-1 ④-2 ②)随基类去策略专属语义
一并消解,mandate 不再持有/覆写任何战略层直调面;换线权威 =
意向状态机(方向判据在 decide_prep_screen 三遍内承载,影子面声明见
sim/ab_core_swap.py 模块 docstring 与 mandate_v1/proof.py)。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from sr_od.application.currency_war.kernel.cw_events import (
    EncounterOption,
    EncounterPick,
)
from sr_od.application.currency_war.kernel.cw_game_state import (
    GameState,
    shop_payload_content_cards,
)
from sr_od.application.currency_war.kernel.cw_vocab import (
    CwAction,
)
from sr_od.application.currency_war.strategies.impl.flow import (
    CwFlowStrategy,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1 import entry
from sr_od.application.currency_war.strategies.impl.mandate_v1.mandate_state import (
    state_of,
)

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_prep_actions import (
        PrepObservation,
    )
    from sr_od.application.currency_war.kernel.cw_registry import (
        DecisionV2Registry,
    )
    from sr_od.application.currency_war.strategies.impl.cw_strategy import (
        StrategySession,
    )
    from sr_od.application.currency_war.strategies.impl.mandate_v1.turn_state import (
        TurnState,
    )

# config 属 app 桶,decision 桶禁 import(cw_strategy.py 字符串注解先例);
# 实例由调用方(注册桥壳)按参注入。
CurrencyWarConfig = 'CurrencyWarConfig'


class MandateV1Strategy(CwFlowStrategy):
    """新核(mandate_v1):三遍化决策序(证明→骨架→EV)+ 单动作循环发射。

    继承 ``CwFlowStrategy``(主流程驱动核,impl/flow.py)复用生命周期
    冷建口、方向节拍内化刷新(ADR-0583)与 pick 族缺省实现(基线
    零改动);备战线决策与商店线驱动器被本类覆写为 cw4 形态
    (entry 三遍编排 / shop 商店波记账)。
    """

    _abstract: bool = False   # 覆写 flow 基类的辅助 ABC 位:本类 = 可注册的活策略核
    STRATEGY_ID: str = 'mandate_v1'
    STRATEGY_NAME: str = '新数学框架核(mandate_v1;三遍化决策序)'
    AUTHOR: str = 'OneDragon'
    VERSION: str = '0.1'
    DESCRIPTION: str = ('cw4 新核:证明 pass(线选择/停手线)→升档器'
                        '求值位→骨架 pass(M1-M7 义务)→EV pass(criteria'
                        ' 七面);单动作循环发射(帧稳定截断为决策核内'
                        '发射组织,非流程侧契约)')

    def __init__(self, registry: DecisionV2Registry | None = None) -> None:
        """核构造 + 标定注入(标定批 T-278/ADR-0639)。

        ``calibration.apply()`` 幂等(只填 None 槽),把 Δ/ε₂ 标定值
        送入 provisional 槽位(生产注入单点;None 期证据门恒不可评
        fail-closed 语义不变)。测试隔离:证据门锁经 ``provisional.
        reset`` fixture 清场,与本注入位无关。"""
        super().__init__(registry)
        from sr_od.application.currency_war.strategies.impl.mandate_v1.audit import (
            calibration,
        )
        calibration.apply()

    def decide_prep_screen(self, session: StrategySession,
                           config: CurrencyWarConfig) -> CwAction | None:
        """备战画面黑板决策(单动作契约接口,返回 ``CwAction | None``)。

        输入 = ``session.prep_obs_frame``(缺失即抛错)。输出 = 决策核
        发射序列的**首个动作**;空序列(含截断截空)→ ``None`` = 本帧
        无动作。帧稳定截断为决策核内发射组织,非流程侧契约。入口内务 =
        备战帧代次消费(方向刷新先于三遍编排)。
        """
        obs = session.prep_obs_frame
        if obs is None:
            raise ValueError(
                'mandate_v1.decide_prep_screen: session.prep_obs_frame 缺失'
                '(黑板契约:画面 op 是唯一写者;None=观察层失约,'
                '禁静默按空观察决策)')
        # 方向重估先于决策(触发 = 帧代次标注;ADR-0583 §3.3-①)
        self._consume_prep_direction_frame(session)
        turn = self._assemble_turn(obs, session)
        actions = decide_from_turn(obs, turn, session, config,
                                   registry=self.registry)
        return actions[0] if actions else None

    def _assemble_turn(self, obs: PrepObservation,
                       session: StrategySession) -> TurnState:
        """装配缝缺省:decision 桶无 obs→Snapshot 装配半部(app 桶
        ``decision_assembly.snapshot_from_obs``),由注册桥壳
        ``MandateV1Live`` 覆写注入(adapter 分拆头注同款先例)。"""
        raise NotImplementedError(
            'mandate_v1 装配缝未注入(注册桥壳 MandateV1Live 覆写'
            ' _assemble_turn;直接实例化本类须走注册面)')

    def decide_encounter(self, options: list[EncounterOption],
                         gs: GameState, session: StrategySession,
                         config: CurrencyWarConfig,
                         refresh_used: bool = False) -> EncounterPick:
        """遭遇分支选卡:E-2 判据落码(kernel/cw_encounter_selection.py 单一源)。

        暗装优先(fail-closed):三常量/两组定谳未就绪 → 恒最低档 + 零刷新,
        reason 带门诊断(e3-simple 归因串,D_enc 口读值与 live 判别子随行
        ——E-3 配对采集通道)。窗口读源 = GameState 结算观测环(E-2 平级
        新结构);同档并列次序 = tiebreak 映射(钻>装备>金币>末档)。
        历史 EV 候选核(mandate_v1/encounter.py)搁置让位、保留禁删;基线
        ``cw_events.decide_encounter`` 零触碰(其他策略核行为不变)。
        入口内务 = 备战帧代次消费(覆写不落基类实现,须自带)。
        """
        self._consume_prep_direction_frame(session)
        from sr_od.application.currency_war.kernel import (
            cw_encounter_selection,
        )
        return cw_encounter_selection.decide_encounter(
            options, gs, refresh_used=refresh_used)

    def decide_shop_screen(self, session: StrategySession,
                           config: CurrencyWarConfig) -> list:
        """商店序列兼容驱动器(mandate 覆写;ADR-0517 迁移批 + ADR-0583 降格)。

        生产执行侧已改调 :meth:`decide_shop_action`(单动作循环,
        ``cw_op_buy_cards.run_buy_waves``);本驱动器保留给 sim 引擎/回放/既有序列锁——
        驱动 = 逐帧调单动作核 + 容器逻辑态直写推进期望态
        (``apply_shop_action_logic`` 简单腿 + 合成升星腿;T-163 起零
        simulate 前瞻消费),终结动作(RefreshShop)截停
        序列、CloseShop 收尾不入序列(与旧截断器的输出形态对齐)。与旧波
        批的输出等价是条件命题(波批逻辑态直写无残差时逐位一致;逻辑态残差史见
        ADR-0517 §消灭的 bug 类)——帧级序列锁不预期保持绿,按锁纪律重推
        语义。观察帧缺失 = 观察层失约,抛错(禁静默按空态决策)。rng 中立。
        覆写存在理由 = mandate 特有记账(下方已买件/段序号/续段 token)。
        """
        from sr_od.application.currency_war.kernel import cw_vocab as cw_state
        from sr_od.application.currency_war.kernel.cw_game_state import (
            ChannelSig,
            ShopActionExecuted,
            apply_shop_action_logic,
            bench_slots_of,
            deployed_slots_of,
            game_state_of,
        )
        # 驱动器同路(W6 波 4,设计件 §2.2-3):决策读容器单例 + 逻辑态直写推进
        # 切 apply_shop_action_logic;在屏前置 = gs.shop.value is not None,
        # 离屏 = 观察层失约抛错(黑板契约容器化等价物)。
        gs = game_state_of(session)
        if gs.shop.value is None:
            raise ValueError(
                'mandate_v1.decide_shop_screen: 容器商店 payload 离屏'
                '(shop=None;黑板契约:商店观察段是唯一写者;'
                'None=观察层失约,禁静默按空态决策)')
        _sig = ChannelSig(family='logic_action', actor='MandateV1Strategy',
                          mode='compute',
                          group_id=f'act:MandateV1Strategy@{gs.write_seq + 1}')
        # 本访问已买件(carried 融合:R2-N1 刚买件首卖偏好;驱动器在循环
        # 内登记,与生产执行侧同一载体)。
        state_of(session).cw4_visit_bought_names = []
        # T-82 段序号置位(sim/replay 商店 visit 入口;生产对应位 =
        # cw_op_buy_cards.run_buy_waves 入口,sim 引擎发射帧仲裁段的商店
        # 决策同样经本驱动器,一并推进):visit = 腾席拒绝结论的输入不
        # 变性段,入口 +1 使上一 visit/上一域残留 token/闩按序号不等失效。
        state_of(session).cw4_segment_serial += 1
        out: list = []
        _pre_bench: list = []
        _pre_dep: list = []
        _pre_shop: list | None = None
        for _ in range(512):   # 防御上界:决策循环不收敛 = 策略器 bug 响亮暴露
            a = self.decide_shop_action(session, config)
            if isinstance(a, cw_state.CloseShop):
                return out
            if isinstance(a, (cw_state.BuyCard,)):
                state_of(session).cw4_visit_bought_names.append(a.card.name or '')
                # 买前快照三件组(升星腿 scratch 基点;必须在直写口写之前
                # 取,失准形态申报见 apply_shop_merge_leg docstring)。
                _pre_bench = list(bench_slots_of(gs))
                _pre_dep = list(deployed_slots_of(gs))
                _payload_now = gs.shop.value
                _pre_shop = (shop_payload_content_cards(_payload_now)
                             if _payload_now is not None else [])
            out.append(a)
            # T-82 续段 token 写入(sim/replay 驱动器位):驱动器采纳并
            # append = 动作确认执行(终结 op 由引擎执行后重观察,其执行
            # 不触停摆结论输入);策略器入口读后即清,下一帧据其判定 M2
            # 停摆续段缓存命中。
            _st_rec = state_of(session)
            _st_rec.cw4_frame_action_record = (
                type(a).__name__, _st_rec.cw4_segment_serial)
            if isinstance(a, cw_state.RefreshShop):
                return out      # 终结 op:序列到止(重观察语境;原
                # CompTransaction 邻接终结已随批2b R3 删除)
            # 逻辑态直写推进 = apply_shop_action_logic(设计件 §2.2-3 驱动器同路;
            # 回执 kernel 判据派生,单动作核逐帧恰一动作 = 击数恒 1)。
            _exec = ShopActionExecuted(
                bought_count=1 if isinstance(a, cw_state.BuyCard) else None,
                levelup_clicks=1 if isinstance(a, cw_state.LevelUp) else None,
                refresh_paid=(int(getattr(a, 'cost', 0) or 0)
                              if isinstance(a, cw_state.RefreshShop) else None))
            apply_shop_action_logic(gs, a, executed=_exec,
                                    produced_by=type(a).__name__, sig=_sig)
            from sr_od.application.currency_war.kernel.cw_game_state import (
                apply_shop_merge_leg,
            )
            # 升星腿对非 BuyCard 自 no-op,pre_* 透传即可。
            apply_shop_merge_leg(gs, a, sig=_sig, pre_bench=_pre_bench,
                                 pre_deployed=_pre_dep, pre_shop=_pre_shop)
        from sr_od.application.currency_war.kernel.cw_game_state import (
            bench_is_full,
            gold_of,
        )
        raise RuntimeError(
            'decide_shop_screen 驱动器 512 帧未收敛(策略器 bug:'
            f'末态 gold={gold_of(gs)} '
            f'bench={bench_is_full(gs)})')


def decide_from_turn(obs: PrepObservation, turn: TurnState,
                     session: StrategySession, config: object,
                     *, registry: DecisionV2Registry | None = None,
                     ) -> list[CwAction]:
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
    # route_tag 伴带透传(方案 v2.1 §3.3 通道载体主案,ADR-0596 收编):
    # 发射臂身份自 Emitted.reason 写入动作自带字段,消旧「actions 列表
    # 推导丢弃发射臂身份」的丢点。tag 定位 = 策略内部路由键(发射分支
    # 构造事实,非放行证据,T-153 治理立场对表);消费位唯一 = 备战域
    # 执行侧落地门(mandate.mark_s1_route_check)的 S1 清键三路径枚举。
    # 字段不入 action_key(kw_only + metadata 排除),幂等粒度零漂移。
    for _e in emitted:
        _e.action.route_tag = _e.reason
    actions = [e.action for e in emitted]
    # 复检语境 = 生成期占用容器下标集(容器读口直取,统一词表坐标系)
    from sr_od.application.currency_war.kernel.cw_game_state import (
        bench_slots_of,
        game_state_of,
    )
    bench_slots = {i for i, b in enumerate(bench_slots_of(game_state_of(session)))
                   if b is not None}
    return entry.truncate_frame_stable(actions, session,
                                       bench_slots=bench_slots)
