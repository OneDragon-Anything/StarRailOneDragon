"""cw4 桥:mandate_v1 决策本体(decision 桶纯函数面)。

新核形态 = 新 ``CwStrategy`` 子类,STRATEGY_ID='mandate_v1'
(config 切 strategy_id 即换核)。实现体分两层:

- 本模块(decision 桶,纯函数):``decide_prep_frame`` = 三遍编排 + 帧
  稳定截断(决策输入 = obs(黑板)+ session 容器直读;依赖矩阵:
  decision 只可依 data/kernel);
- 注册桥壳 ``strategies/mandate_v1_strategy.py``(app 层):零逻辑复制的
  纯注册壳(``__module__`` 守卫要求壳类定义于本模块;生产路径职责分界 =
  画面 op 只做观察 + 调一个决策入口,**不加生产接线步**,R191 裁决)。

商店线口径:
``decide_shop_screen`` = 序列兼容驱动器(循环调 ``shop.decide_shop_action``
单动作核,输入 = 容器单例
``game_state_of(session)``;生产执行侧入口 =
``decide_shop_action``,由商店画面 op 单动作循环消费)。
该驱动器自 起降格出 ABC(基类缺省实现 = flow 层通用循环;
本类覆写保留 mandate 特有记账:已买件名单/段序号/续段 token)。
战略层方向重估自 起内化进策略器(flow 层
``_refresh_direction``,触发 = 黑板帧刷新代次标注)——旧「透传声明」
(规格未给 cw4 战略层新形态,R189-1 ④-2 ②)随基类去策略专属语义
一并消解,mandate 不再持有/覆写任何战略层直调面;换线权威 =
意向状态机(方向判据在 decide_prep_screen 三遍内承载,换线出口
申报面见 mandate_v1/proof.py;原 ab_core_swap 模块 docstring 影子面
载体已删除)。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from sr_od.application.currency_war.kernel.cw_game_state import (
    GameState,
)
from sr_od.application.currency_war.kernel.cw_vocab import (
    Action,
    CwAction,
    CwActionObsParam,
)
from sr_od.application.currency_war.strategies.impl.flow import (
    CwFlowStrategy,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1 import (
    entry,
    session_scope,
)
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

# config 属 app 层,decision 桶禁 import(cw_strategy.py 字符串注解先例);
# 实例由调用方(注册桥壳)按参注入。
CurrencyWarConfig = 'CurrencyWarConfig'


def _launch_front_check(gs: GameState) -> CwAction | None:
    """前置动作发出点:出战就绪帧短路三遍编排,产出动作发出意图(动作发出
    决策的策略层宿主;旧达标分支决策迁驻,design §2.3)。

    - 判定核 = kernel ``readiness_launch_decision``(线成员谓词注入
      单一源 = statefn.predicates.line_members,禁内联第二实现);
    - 质量推迟帧(出战就绪 ∧ defer_by_quality)不发出,分键
      ``launch_quality_defer_frames``;评估异常帧分键
      ``launch_quality_eval_error`` 后照常发出(fail-open 防死锁,
      分界)——键单一源 = kernel cw_launch_admission 常量;
    - 出战就绪 ∧ 帧级金判定 ``in_launch_spend_zone`` 命中(禁内联金利息线
      比较)→ 受限商店访问意图 ``CwActionOpenShopParam()``(**普通开店
      形态**;进出店 = 普通 OpenShop/0n 路径,访问内消费由策略侧自限
      接管,详设 §2.10);
      **每个出战就绪段至多一次**(段旗 cw4_launch_spend_visited,脱离出战
      就绪复位;复位后再次出战就绪仍命中允许新段再访);段内已访问 → 落无条件发出
      (旧形态「访问后照发」跨帧等价,金不回落无死循环);
      **不经 S1 开店标志与 CwActionOpenShopParam 节流**(前置动作发出点短路
      三遍编排,空转防护 = 段旗);
    - 出战就绪 ∧ 未命中 → CwActionStartBattleParam 终点意图(词表现成);
    - 非出战就绪 → 段旗复位,返回 None = 原三遍编排接管(非出战就绪帧零变化)。

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
        _st.cw4_launch_spend_visited = False   # 出战就绪段结束,段旗复位
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
        return None   # 质量推迟帧:本帧不发出(防死锁语义 kernel 单一源)
    if in_launch_spend_zone(gold_of(gs), gs):
        if not _st.cw4_launch_spend_visited:
            _st.cw4_launch_spend_visited = True
            return CwActionOpenShopParam()   # 普通开店形态(详设 §2.10)
        # 段内已访问:落无条件发出
    return CwActionStartBattleParam()


def launch_restricted_session_active(gs: GameState) -> bool:
    """受限会话派生标记(出战就绪 ∧ 金达利息线;动作发出帧受限消费的策略侧自限门,
    分层依据 = flow/README.md §1 决策控制分层铁律)。

    判定与 :func:`_launch_front_check` 前置动作发出点同源:出战就绪判定核 =
    kernel ``readiness_launch_decision``(线成员/部署计划谓词注入同参,
    单一源纪律同款),金判定 = kernel ``saturation_line`` 派生链直读
    (禁字面量式)——**恰落线帧视为受限(gold >= g*)**:kernel 预算闸
    在 gold == g* 帧拒一切正成本动作(花后必跌破 g*),派生标记对齐该
    带内拒域,闸停用后同边界不失守;入段判定
    (``in_launch_spend_zone`` 严格 >)随前置动作发出点现状不动,两判定
    并存非复制(g* 单一源同链)。买断制语境(cap_resolved = 0)不在设计
    范围内,恒 False(同 in_launch_spend_zone 口径)。每帧现算零粘滞:不读不写
    任何段旗/缓存——「每个出战就绪段至多一次」的段旗(cw4_launch_spend_visited)
    留在原位语义不受本标记覆盖,其写端单一源仍 = _launch_front_check
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
        return False   # 买断制不在设计范围内(同 in_launch_spend_zone 口径)
    return gold_of(gs) >= saturation_line(cap)


class MandateV1Strategy(CwFlowStrategy):
    """新核(mandate_v1):三遍化决策序(证明→骨架→EV)+ 单动作循环发出。

    继承 ``CwFlowStrategy``(主流程驱动核,impl/flow.py)复用生命周期
    冷建口、方向节拍内化刷新与 pick 族缺省实现(基线
    零改动);备战线决策与商店线驱动器被本类覆写为 cw4 形态
    (entry 三遍编排 / shop 商店波记账)。
    """

    _abstract: bool = False   # 覆写 flow 基类的辅助 ABC 位:本类 = 可注册的活策略核
    STRATEGY_ID: str = 'mandate_v1'
    STRATEGY_NAME: str = '新数学框架核(mandate_v1;九段全扫工序)'
    AUTHOR: str = 'OneDragon'
    VERSION: str = '0.1'
    DESCRIPTION: str = ('cw4 新核:备战九段全扫工序(溢出自救→消耗品→'
                        '晶矿→升级→商店会话→部署→装备工具→凑息→出战)'
                        ';单动作循环发射(帧稳定截断为决策核内发射'
                        '组织,非流程侧契约)')

    def __init__(self, gs, config,
                 registry: DecisionV2Registry | None = None) -> None:
        """核构造(终态契约 §2.1:gs/config 透传基类构造注入)。

        (原 ``calibration.apply()`` P76 两槽注入位已删除——
        V_C_MINUS_V_F/E2_CONCENTRATION_BAND 槽位不迁移,
        line_and_upgrade §1.6;audit/calibration.py 一并移除。)"""
        super().__init__(gs, config, registry)

    def decide_prep_screen(self) -> CwAction:
        """备战画面决策(终态零参口 §2.1;单动作;空动作发出 = CwActionObsParam
        scope='outer_loop' 返回主循环重新观察——原 HoldFrame 通道并入,
        用户裁定 2026-09-20)。

        输入 = **容器 game state 直读**(黑板帧已删除:黑板 gs.prep_obs 读点与缺失抛错防线
        随之删除——「观察先于决策」前提由画面 op 编排保证,op 入口
        heavy 先于决策调用)。输出 = 决策核发出序列的**首个动作**;
        空序列(含截断截空)→ 空动作发出 obs(scope='outer_loop')= 本帧无
        动作返回主循环重新观察(None 路径已停用,终态契约 §2.2)。帧稳定截断为
        决策核内动作发出组织,非流程侧契约。入口内务 = 备战帧代次消费
        (方向刷新先于三遍编排)。管线宿主 = self.gs(state_of(gs) 经同源
        接线解析策略器状态;game_state_of(gs) 本体直通)。
        """
        # 节点边界处理 + 方向签名前置(契约 B/C:两入口调同一对函数,
        # 时序 = 边界 → 签名 → 决策;line_and_upgrade §3 执行时序节)。
        # 本批(3.1)只写新增键族,现行决策零影响;备战/商店统一行为。
        session_scope.handle_node_boundary(self.gs)
        session_scope.refresh_line_if_needed(self.gs)
        # 方向重估先于决策(触发 = 帧代次标注)
        self._consume_prep_direction_frame()
        # —— 前置动作发出点(达标分支的动作发出决策驻策略层)。出战就绪帧短路
        # 三遍编排;非出战就绪帧 None = 原编排零变化。
        _launch_action = _launch_front_check(self.gs)
        if _launch_action is not None:
            return _launch_action
        # 预算遥测披露(唯一写点 = economy_cycle.disclose_budget;落点 =
        # 原装配缝调用位——前置动作发出点判定之后,非出战就绪帧才到达,
        # 出战就绪短路帧维持不披露,零行为变化)。披露面禁决策消费(语义锚 =
        # mandate_state.py 披露字段注释与守卫测试 test_economy 预算遥测
        # 披露节)。
        from sr_od.application.currency_war.strategies.impl.mandate_v1.economy_cycle import (
            disclose_budget,
        )
        # 宿主双槽 = gs(state 槽给容器现值,session 槽给 state_of(gs) 同源
        # 解析——经 self.state 传递会让下游 game_state_of 解析一次性空容器)。
        disclose_budget(self.gs, self.gs, self.registry)
        actions = decide_prep_frame(self.gs, self.config,
                                    registry=self.registry)
        return actions[0] if actions else CwActionObsParam(scope='outer_loop')

    def decide_shop_action(self) -> Action:
        """商店单动作入口(mandate 覆写 = 两项前置内务;决策本体 =
        flow 基类现行决策,零改动)。

        节点边界处理与方向签名前置(契约 B/C)与备战入口调同一对
        函数——商店决策入口的统一行为(shop_session §1:入口首查节点
        边界检测与标记检查,标记检查位归 3.6 会话重排接线),时序 =
        边界 → 签名 → 决策(line_and_upgrade §3 执行时序节)。生产
        单动作循环与 :meth:`decide_shop_screen` 驱动器都经本口,两面
        同源;本批(3.1)只写新增键族,现行商店决策零影响。
        """
        session_scope.handle_node_boundary(self.gs)
        session_scope.refresh_line_if_needed(self.gs)
        return super().decide_shop_action()

    def decide_shop_screen(self, session: StrategySession | None = None,
                           config: CurrencyWarConfig | None = None) -> list:
        """商店序列兼容驱动器(mandate 覆写;迁移批 + 降格;
        形参 = 兼容宿主(sim/回放/序列测试调用面照旧传),决策已零参化)。

        生产执行侧已改调 :meth:`decide_shop_action`(单动作循环,
        商店画面 op 决策动作 node);本驱动器保留给回放/既有序列测试——
        驱动 = 逐帧调单动作核 + 容器逻辑态直写推进期望态
        (逐动作直调上报函数族),终结动作(CwActionRefreshShopParam)截停
        序列、CwActionCloseShopParam 收尾不入序列(与旧截断器的输出形态对齐)。与旧波
        批的输出等价是条件命题(波批逻辑态直写无残差时逐位一致;逻辑态残差史见
        §消灭的 bug 类)——帧级序列测试不预期保持绿,按测试纪律重推
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
        # 驱动器同路:决策读容器单例 + 期望态
        # 推进 = 逐动作直调上报函数(快照三件组内聚,无双抄写段)。在屏前置 = gs.shop.value is not None,离屏 =
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
        # §2.5 impl 层;与旧 state_of(session) 同一对象,§2.6 过渡桥)。
        self.state.cw4_visit_bought_names = []
        # 段序号置位(驱动器商店 visit 入口;生产对应位 =
        # 商店画面 op 观察 node,一并推进):visit = 腾席拒绝结论的输入不
        # 变性段,入口 +1 使上一 visit/上一域残留 token/标志按序号不等失效。
        self.state.cw4_segment_serial += 1
        out: list = []
        for _ in range(512):   # 防御上界:决策循环不收敛 = 策略器 bug 响亮暴露
            a = self.decide_shop_action()   # 零参单动作核(终态契约 §2.1)
            if isinstance(a, cw_state.CwActionCloseShopParam):
                return out
            if isinstance(a, (cw_state.CwActionBuyCardParam,)):
                self.state.cw4_visit_bought_names.append(a.card.name or '')
            out.append(a)
            # 续段 token 写入(驱动器位):驱动器采纳并
            # append = 动作确认执行(终结 op 由消费侧执行后重观察,其执行
            # 不触停摆结论输入);策略器入口读后即清,下一帧据其判定 M2
            # 停摆续段缓存命中。
            self.state.cw4_frame_action_record = (
                type(a).__name__, self.state.cw4_segment_serial)
            if isinstance(a, cw_state.CwActionRefreshShopParam):
                return out      # 终结 op:序列到止(重观察语境)
            # 期望态推进 = 逐动作直调上报函数(上报函数族分支,
            # 单动作核逐帧恰一动作 = 击数恒 1)。
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
    """备战决策帧(九段全扫 + 帧稳定截断;纯函数;决策输入 =
    容器 game state 直读)。

    截断语境供给:conditional 类名-槽一致性复检消费的 bench 占用槽位集,
    容器 kind 口现读派生。
    """
    emitted = entry.emit(session, config, registry=registry)
    # route_tag 伴带透传(方案 v2.1 §3.3 通道载体主案,并入):
    # 动作发出分支身份自 Emitted.reason 写入动作自带字段,消旧「actions 列表
    # 推导丢弃动作发出分支身份」的丢点。tag 定位 = 策略内部路由键(动作发出分支
    # 构造事实,非放行证据;治理立场:路由键不作放行依据);消费位唯一 = 备战域
    # 执行侧落地门(mandate.mark_s1_route_check)的 S1 清键三路径枚举。
    # 字段不入 action_key(kw_only + metadata 排除),幂等粒度零漂移。
    for _e in emitted:
        _e.action.route_tag = _e.reason
    actions = [e.action for e in emitted]
    # 复检语境 = 生成期占用**槽位表下标集**(动作参数坐标系,单一源 =
    # kernel cw_vocab 坐标契约节:bench_idx = 定长 9 槽表下标,空槽保洞
    # 不移位)。取法 = bench_view_slots_of 全槽表逐位 + slot_occupies
    # kind 谓词——禁用 bench_entries_of(紧缩序)枚举下标代替:备战席
    # 前部有洞时紧缩枚举下标 ≠ 槽位表下标,复检错杀合法引用(占用槽
    # 被判空),发出被截空后世界不变 → 备战环「本帧无动作」活锁(sim
    # 多种子实证:非验收 seed 首局 P1r1 凑息分支卖后部槽被错杀至看门狗;
    # 实机同链路同受害)。语义与 P4 翻形前一致({全槽表枚举 | 槽非空})。
    from sr_od.application.currency_war.kernel.cw_game_state import (
        bench_view_slots_of,
        game_state_of,
        slot_occupies,
    )
    bench_slots = {i for i, s in enumerate(bench_view_slots_of(game_state_of(session)))
                   if s is not None and slot_occupies(s.kind)}
    return entry.truncate_frame_stable(actions, session,
                                       bench_slots=bench_slots)
