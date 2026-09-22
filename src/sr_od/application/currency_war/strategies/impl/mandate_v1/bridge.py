"""cw4 桥:mandate_v1 决策本体(decision 桶纯函数面)。

新核形态 = 新 ``CwStrategy`` 子类,STRATEGY_ID='mandate_v1'
(config 切 strategy_id 即换核)。实现体分两层:

- 本模块(decision 桶,纯函数):``decide_prep_frame`` = 三遍编排 + 帧
  稳定截断(决策输入 = obs(黑板)+ session 容器直读;依赖矩阵:
  decision 只可依 data/kernel);
- 注册桥壳 ``strategies/mandate_v1_strategy.py``(app 桶):零逻辑复制的
  纯注册壳(``__module__`` 守卫要求壳类定义于本模块;生产路径职责分界 =
  画面 op 只做观察 + 调一个决策入口,**不加生产接线步**,R191 裁决)。

商店线口径(步4b,STEP34_REPORT 裁量 #1 的接线兑现;ADR-0517 迁移批
后形态):
``decide_shop_screen`` = 序列兼容驱动器(循环调 ``shop.decide_shop_action``
单动作核,输入 = 容器单例
``game_state_of(session)``;生产执行侧入口 =
``decide_shop_action``,由商店画面 op 单动作循环消费)
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
    EncounterPick,
)
from sr_od.application.currency_war.kernel.cw_game_state import (
    GameState,
)
from sr_od.application.currency_war.kernel.cw_vocab import (
    CwAction,
    CwActionObsParam,
    CwActionPickEncounterParam,
    CwActionRefreshNodeOptionsParam,
)
from sr_od.application.currency_war.strategies.impl.flow import (
    CwFlowStrategy,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1 import entry
from sr_od.application.currency_war.strategies.impl.mandate_v1.mandate_state import (
    state_of,
)

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_registry import (
        DecisionV2Registry,
    )
    from sr_od.application.currency_war.strategies.impl.cw_strategy import (
        StrategySession,
    )

# config 属 app 桶,decision 桶禁 import(cw_strategy.py 字符串注解先例);
# 实例由调用方(注册桥壳)按参注入。
CurrencyWarConfig = 'CurrencyWarConfig'


def _launch_front_check(gs: GameState) -> CwAction | None:
    """前置发射位:armed 帧短路三遍编排,产出发射意图(发射决策的
    策略层宿主;旧达标臂发射决策迁驻,design §2.3)。

    - 判定核 = kernel ``readiness_launch_decision``(线成员谓词注入
      单一源 = statefn.predicates.line_members,禁内联第二实现);
    - 质量推迟帧(armed ∧ defer_by_quality)不发射,分键
      ``launch_quality_defer_frames``;评估异常帧分键
      ``launch_quality_eval_error`` 后照常发射(fail-open 防死锁,
      ADR-0570 分界)——键单一源 = kernel cw_launch_admission 常量;
    - armed ∧ 帧级金判定 ``in_launch_spend_zone`` 命中(禁内联金息线
      比较)→ 受限商店访问意图 ``CwActionOpenShopParam()``(**普通开店
      形态**;进出店 = 普通 OpenShop/0n 路径,访问内消费由策略侧自限
      接管,详设 §2.10);
      **每武装段至多一次**(段旗 cw4_launch_spend_visited,失武装复位;
      复位后再武装仍命中允许新段再访);段内已访问 → 落无条件发射
      (旧形态「访问后照发」跨帧等价,金不回落无死循环);
      **不经 S1 开店闩与 CwActionOpenShopParam 节流**(前置发射位短路
      三遍编排,空转防护 = 段旗);
    - armed ∧ 未命中 → CwActionStartBattleParam 终点意图(词表现成);
    - 非 armed → 段旗复位,返回 None = 原三遍编排接管(非 armed 帧零变化)。

    终态契约 §2.1:gs/config 构造注入——入参即容器;策略器状态读口 =
    ``state_of(gs)``(gs.strategy_state 同源接线,漏斗/构造点单一写入)。
    """
    from sr_od.application.currency_war.kernel.cw_economy import (
        gold_of,
        in_launch_spend_zone,
    )
    from sr_od.application.currency_war.kernel.cw_launch_admission import (
        LAUNCH_QUALITY_DEFER_FRAMES_KEY,
        LAUNCH_QUALITY_EVAL_ERROR_KEY,
        readiness_launch_decision,
    )
    from sr_od.application.currency_war.kernel.cw_vocab import (
        CwActionOpenShopParam,
        CwActionStartBattleParam,
    )
    from sr_od.application.currency_war.strategies.impl.mandate_v1.deploy_plan import (
        has_deployable,
    )
    from sr_od.application.currency_war.strategies.impl.mandate_v1.statefn.predicates import (
        line_members,
    )
    _st = state_of(gs)
    _decision = readiness_launch_decision(
        gs, getattr(_st, 'target_comp', None), line_members=line_members,
        deploy_plan_available_fn=has_deployable)
    if not _decision.get('armed'):
        _st.cw4_launch_spend_visited = False   # 武装段结束,段旗复位
        return None
    _ct = _st.cw4_counters
    _quality = _decision.get('quality')
    if _decision.get('quality_eval_error'):
        if isinstance(_ct, dict):
            _ct[LAUNCH_QUALITY_EVAL_ERROR_KEY] = \
                _ct.get(LAUNCH_QUALITY_EVAL_ERROR_KEY, 0) + 1
    elif isinstance(_quality, dict) and _quality.get('defer_by_quality'):
        if isinstance(_ct, dict):
            _ct[LAUNCH_QUALITY_DEFER_FRAMES_KEY] = \
                _ct.get(LAUNCH_QUALITY_DEFER_FRAMES_KEY, 0) + 1
        return None   # 质量推迟帧:本帧不发射(防死锁语义 kernel 单一源)
    if in_launch_spend_zone(gold_of(gs), gs):
        if not _st.cw4_launch_spend_visited:
            _st.cw4_launch_spend_visited = True
            return CwActionOpenShopParam()   # 普通开店形态(详设 §2.10)
        # 段内已访问:落无条件发射
    return CwActionStartBattleParam()


def launch_restricted_session_active(gs: GameState) -> bool:
    """受限会话派生标记(armed ∧ 金达息线;发射帧受限消费的策略侧自限门,
    迭代 changes/2026-09-21-shop-refresh-terminal 详设 §2.10)。

    判定与 :func:`_launch_front_check` 前置发射位同源:armed 判定核 =
    kernel ``readiness_launch_decision``(线成员/部署计划谓词注入同参,
    单一源纪律同款),金判定 = kernel ``saturation_line`` 派生链直读
    (禁字面量式)——**恰落线帧视为受限(gold >= g*)**:kernel 预算闸
    在 gold == g* 帧拒一切正成本动作(花后必跌破 g*),派生标记对齐该
    带内拒域,闸退役后同边界不失守;入段判定
    (``in_launch_spend_zone`` 严格 >)随前置发射位现状不动,两判定
    并存非复制(g* 单一源同链)。买断制语境(cap_resolved = 0)出辖
    恒 False(同 in_launch_spend_zone 口径)。每帧现算零粘滞:不读不写
    任何段旗/缓存——「每武装段至多一次」的段旗(cw4_launch_spend_visited)
    留守语义不受本标记辖,其写端单一源仍 = _launch_front_check
    (mandate_state 字段注)。

    消费点 = flow.decide_shop_action 受限会话自限(唯一提案产出后经
    kernel ``launch_arbitration_gate`` 谓词检;拒 = 决策改发 CloseShop,
    消费终止语义逐位平移,非改试次优——金出口族红线 5)。
    """
    from sr_od.application.currency_war.kernel.cw_economy import (
        cap_resolved_of_session,
        gold_of,
        saturation_line,
    )
    from sr_od.application.currency_war.kernel.cw_launch_admission import (
        readiness_launch_decision,
    )
    from sr_od.application.currency_war.strategies.impl.mandate_v1.deploy_plan import (
        has_deployable,
    )
    from sr_od.application.currency_war.strategies.impl.mandate_v1.statefn.predicates import (
        line_members,
    )
    _decision = readiness_launch_decision(
        gs, getattr(state_of(gs), 'target_comp', None), line_members=line_members,
        deploy_plan_available_fn=has_deployable)
    if not _decision.get('armed'):
        return False
    cap = cap_resolved_of_session(gs)
    if cap <= 0:
        return False   # 买断制出辖(同 in_launch_spend_zone 口径)
    return gold_of(gs) >= saturation_line(cap)


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

    def __init__(self, gs, config,
                 registry: DecisionV2Registry | None = None) -> None:
        """核构造 + 标定注入(标定批 T-278/ADR-0639;终态契约 §2.1:gs/config
        透传基类构造注入)。

        ``calibration.apply()`` 幂等(只填 None 槽),把 Δ/ε₂ 标定值
        送入 provisional 槽位(生产注入单点;None 期证据门恒不可评
        fail-closed 语义不变)。测试隔离:证据门锁经 ``provisional.
        reset`` fixture 清场,与本注入位无关。"""
        super().__init__(gs, config, registry)
        from sr_od.application.currency_war.strategies.impl.mandate_v1.audit import (
            calibration,
        )
        calibration.apply()

    def decide_prep_screen(self) -> CwAction:
        """备战画面决策(终态零参口 §2.1;单动作;空发射 = CwActionObsParam
        scope='outer_loop' 交回外循环重观察——原 HoldFrame 通道收编,
        用户裁定 2026-09-20)。

        输入 = **容器 game state 直读**(迭代 2026-09-18-prep-obs-
        retirement 阶段 3.5:黑板 gs.prep_obs 读点与缺失抛错防线随黑板
        退役删除——「观察先于决策」前提由画面 op 编排保证,op 入口
        heavy 先于决策调用)。输出 = 决策核发射序列的**首个动作**;
        空序列(含截断截空)→ 空发射 obs(scope='outer_loop')= 本帧无
        动作交回外循环重观察(None 退役,终态契约 §2.2)。帧稳定截断为
        决策核内发射组织,非流程侧契约。入口内务 = 备战帧代次消费
        (方向刷新先于三遍编排)。管线宿主 = self.gs(state_of(gs) 经同源
        接线解析策略器状态;game_state_of(gs) 本体直通)。
        """
        # 方向重估先于决策(触发 = 帧代次标注;ADR-0583 §3.3-①)
        self._consume_prep_direction_frame()
        # —— 前置发射位(达标臂的发射决策驻策略层)。armed 帧短路
        # 三遍编排;非 armed 帧 None = 原编排零变化。
        _launch_action = _launch_front_check(self.gs)
        if _launch_action is not None:
            return _launch_action
        # 预算遥测披露(唯一写点 = economy_cycle.disclose_budget;落点 =
        # 原装配缝调用位——前置发射位判定之后,非 armed 帧才到达,armed
        # 短路帧维持不披露,零行为变化)。披露面禁决策消费(语义锚 =
        # mandate_state.py 披露字段注释与守卫锁 test_cw_budget_disclosure)。
        from sr_od.application.currency_war.strategies.impl.mandate_v1.economy_cycle import (
            disclose_budget,
        )
        # 宿主双槽 = gs(state 槽给容器现值,session 槽给 state_of(gs) 同源
        # 解析——经 self.state 传递会让下游 game_state_of 解析一次性空容器)。
        disclose_budget(self.gs, self.gs, self.registry)
        actions = decide_prep_frame(self.gs, self.config,
                                    registry=self.registry)
        return actions[0] if actions else CwActionObsParam(scope='outer_loop')

    def decide_encounter(self) -> CwActionPickEncounterParam | CwActionRefreshNodeOptionsParam:
        """遭遇分支选卡(终态零参口;候选 = ``gs.encounter`` payload):E-2
        判据落码(kernel/cw_encounter_selection.py 单一源)。

        暗装优先(fail-closed):三常量/两组定谳未就绪 → 恒最低档 + 零刷新,
        reason 带门诊断(e3-simple 归因串,D_enc 口读值与 live 判别子随行
        ——E-3 配对采集通道)。窗口读源 = GameState 结算观测环(E-2 平级
        新结构);同档并列次序 = tiebreak 映射(钻>装备>金币>末档)。
        历史 EV 候选核(mandate_v1/encounter.py)搁置让位、保留禁删;基线
        ``cw_events.decide_encounter`` 零触碰(其他策略核行为不变)。
        入口内务 = 备战帧代次消费(覆写不落基类实现,须自带)。
        刷新闸输入源 = ``gs.encounter_refresh_left`` 剩余语义观察真值(用户
        裁定 2026-09-21,全域规范 = op-layer.md §1.4;剩余 ≤0 或 None =
        已刷尽/未观察 → refresh_used=True,判据按原评分直接选卡)。
        输出包装(终态契约 §2.2):刷新建议 = CwActionRefreshNodeOptionsParam,选卡 =
        CwActionPickEncounterParam(两型互斥单发)。
        """
        self._consume_prep_direction_frame()
        payload = self.gs.encounter.value
        if payload is None:
            raise ValueError(
                'decide_encounter: gs.encounter payload 槽离屏'
                '(None = 观察层失约,禁静默按空态决策)')
        options = payload.options
        _left = self.gs.encounter_refresh_left.value
        refresh_used = not (_left is not None and int(_left) > 0)
        from sr_od.application.currency_war.kernel import (
            cw_encounter_selection,
        )
        pick: EncounterPick = cw_encounter_selection.decide_encounter(
            options, self.gs, refresh_used=refresh_used)
        if pick.refresh:
            return CwActionRefreshNodeOptionsParam(reason=pick.reason)
        return CwActionPickEncounterParam(idx=pick.idx, reason=pick.reason)

    def decide_shop_screen(self, session: StrategySession | None = None,
                           config: CurrencyWarConfig | None = None) -> list:
        """商店序列兼容驱动器(mandate 覆写;ADR-0517 迁移批 + ADR-0583 降格;
        形参 = 兼容宿主(sim/回放/序列锁调用面照旧传),决策已零参化)。

        生产执行侧已改调 :meth:`decide_shop_action`(单动作循环,
        商店画面 op 决策动作 node);本驱动器保留给 sim 引擎/回放/既有序列锁——
        驱动 = 逐帧调单动作核 + 容器逻辑态直写推进期望态
        (上报函数族委托分支串;T-163 起零
        simulate 前瞻消费),终结动作(CwActionRefreshShopParam)截停
        序列、CwActionCloseShopParam 收尾不入序列(与旧截断器的输出形态对齐)。与旧波
        批的输出等价是条件命题(波批逻辑态直写无残差时逐位一致;逻辑态残差史见
        ADR-0517 §消灭的 bug 类)——帧级序列锁不预期保持绿,按锁纪律重推
        语义。观察帧缺失 = 观察层失约,抛错(禁静默按空态决策)。rng 中立。
        覆写存在理由 = mandate 特有记账(下方已买件/段序号/续段 token)。
        """
        from sr_od.application.currency_war.kernel import cw_vocab as cw_state
        from sr_od.application.currency_war.kernel.cw_action_report.buy_card import (
            report_action_buy_card_param,
        )
        from sr_od.application.currency_war.kernel.cw_action_report.level_up import (
            report_action_level_up_param,
        )
        from sr_od.application.currency_war.kernel.cw_action_report.sell_bench import (
            report_action_sell_bench_param,
        )
        from sr_od.application.currency_war.kernel.cw_action_report.sell_deployed import (
            report_action_sell_deployed_param,
        )
        from sr_od.application.currency_war.kernel.cw_action_report.swap_deploy import (
            report_action_swap_deploy_param,
        )
        from sr_od.application.currency_war.kernel.cw_game_state import (
            ChannelSig,
            ShopActionExecuted,
        )
        # 驱动器同路(W6 波 4,设计件 §2.2-3):决策读容器单例 + 期望态
        # 推进 = 逐动作直调上报函数(动作 op 重组批④:快照三件组内聚,
        # 双抄写段退役)。在屏前置 = gs.shop.value is not None,离屏 =
        # 观察层失约抛错(黑板契约容器化等价物)。
        gs = self.gs
        if gs.shop.value is None:
            raise ValueError(
                'mandate_v1.decide_shop_screen: 容器商店 payload 离屏'
                '(shop=None;黑板契约:商店观察段是唯一写者;'
                'None=观察层失约,禁静默按空态决策)')
        _sig = ChannelSig(family='logic_action', actor='MandateV1Strategy',
                          mode='compute',
                          group_id=f'act:MandateV1Strategy@{gs.write_seq + 1}')
        # 本访问已买件(carried 融合:R2-N1 刚买件首卖偏好;驱动器在循环
        # 内登记,与生产执行侧同一载体)。状态宿主 = self.state(终态契约
        # §2.5 impl 桶;与旧 state_of(session) 同一对象,§2.6 过渡桥)。
        self.state.cw4_visit_bought_names = []
        # T-82 段序号置位(sim/replay 商店 visit 入口;生产对应位 =
        # 商店画面 op 观察 node,sim 引擎发射帧仲裁段的商店
        # 决策同样经本驱动器,一并推进):visit = 腾席拒绝结论的输入不
        # 变性段,入口 +1 使上一 visit/上一域残留 token/闩按序号不等失效。
        self.state.cw4_segment_serial += 1
        out: list = []
        for _ in range(512):   # 防御上界:决策循环不收敛 = 策略器 bug 响亮暴露
            a = self.decide_shop_action()   # 零参单动作核(终态契约 §2.1)
            if isinstance(a, cw_state.CwActionCloseShopParam):
                return out
            if isinstance(a, (cw_state.CwActionBuyCardParam,)):
                self.state.cw4_visit_bought_names.append(a.card.name or '')
            out.append(a)
            # T-82 续段 token 写入(sim/replay 驱动器位):驱动器采纳并
            # append = 动作确认执行(终结 op 由引擎执行后重观察,其执行
            # 不触停摆结论输入);策略器入口读后即清,下一帧据其判定 M2
            # 停摆续段缓存命中。
            self.state.cw4_frame_action_record = (
                type(a).__name__, self.state.cw4_segment_serial)
            if isinstance(a, cw_state.CwActionRefreshShopParam):
                return out      # 终结 op:序列到止(重观察语境;原
                # CompTransaction 邻接终结已随批2b R3 删除)
            # 期望态推进 = 逐动作直调上报函数(引擎入口委托分支串,
            # design.md §2;单动作核逐帧恰一动作 = 击数恒 1)。
            if isinstance(a, cw_state.CwActionBuyCardParam):
                report_action_buy_card_param(gs, a, _sig)
            elif isinstance(a, cw_state.CwActionSellBenchParam):
                report_action_sell_bench_param(gs, a, _sig)
            elif isinstance(a, cw_state.CwActionSellDeployedParam):
                report_action_sell_deployed_param(gs, a, _sig)
            elif isinstance(a, cw_state.CwActionSwapDeployParam):
                report_action_swap_deploy_param(gs, a, _sig)
            elif isinstance(a, (cw_state.CwActionLevelUpParam,
                                cw_state.CwActionLevelUpShopParam)):
                report_action_level_up_param(
                    gs, a, _sig,
                    executed=ShopActionExecuted(levelup_clicks=1))
        from sr_od.application.currency_war.kernel.cw_game_state import (
            bench_is_full,
            gold_of,
        )
        raise RuntimeError(
            'decide_shop_screen 驱动器 512 帧未收敛(策略器 bug:'
            f'末态 gold={gold_of(gs)} '
            f'bench={bench_is_full(gs)})')


def decide_prep_frame(session: StrategySession, config: object,
                      *, registry: DecisionV2Registry | None = None,
                      ) -> list[CwAction]:
    """三遍编排 + 帧稳定截断(纯函数;R189-4 结构签名;决策输入 =
    容器 game state 直读,迭代阶段 3.5 去 obs 形参)。

    ev_arm 模式参数取 ``config.ev_arm``(缺省 full;非法值回落 full)。
    截断语境供给(R196 症5):conditional 类名-槽一致性复检消费的
    bench 占用槽位集,容器 kind 口现读派生。
    """
    ev_arm = getattr(config, 'ev_arm', 'full')
    if ev_arm not in entry.EV_ARM_VALUES:
        ev_arm = 'full'
    emitted = entry.emit(session, config,
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
    # 复检语境 = 生成期占用容器下标集(容器 kind 口直取,统一词表坐标系;
    # P4 容器形:占席条目枚举下标 = 槽位下标)
    from sr_od.application.currency_war.kernel.cw_game_state import (
        bench_entries_of,
        game_state_of,
    )
    bench_slots = set(range(len(bench_entries_of(game_state_of(session)))))
    return entry.truncate_frame_stable(actions, session,
                                       bench_slots=bench_slots)
