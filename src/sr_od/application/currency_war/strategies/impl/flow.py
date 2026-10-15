"""货币战争 主流程驱动核(CwFlowStrategy;自 decision_v2/strategy.py 迁入,
策略统一迁移批——底稿 MAP ⓪ A1「迁移白名单」)。

适用范围 = mandate_v1 未覆写的域实现:

- 生命周期并入后的唯一冷建口 create_session(策略器状态工厂接线 + live
  初值 v3_phase='FORM' 一并在此落位)与策略器状态工厂 create_state;
- 方向节拍内化(:meth:`_refresh_direction`;:方向重估从流程侧
  ops 直调收进策略器,触发信号 = 黑板帧刷新代次标注,键守卫贵段每
  game-round 恰一次 + 便宜派生视图段);
- pick 族(decide_invest/supply/encounter/megastar/partner/planner/
  star_tome/wish_trial/box_card + 契约扩员两口 fortune/expert_invite,
  普查迁移);
- 商店序列兼容驱动器 decide_shop_screen 缺省实现(降格出 ABC;
  回放/序列测试消费,mandate 记账在其覆写)与商店单动作
  接口 decide_shop_action(委托 mandate_v1/shop)。

- live 备战决策链 = cw_screen_prep → mandate_v1.bridge → entry.emit
  三遍编排。

本类 ``_abstract=True``(中间辅助 ABC,StrategyManager 不注册;
decide_prep_screen 保持 abstract——具现 =
``strategies.impl.mandate_v1.bridge.MandateV1Strategy``,生产注册壳 =
``strategies/mandate_v1_strategy.py``)。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel import cw_comps, cw_events
from sr_od.application.currency_war.kernel.cw_comps import get_comp
from sr_od.application.currency_war.kernel.cw_game_state import (
    GameState,
    ShopActionExecuted,
    gold_of,
    plane_of,
    round_num_of,
    shop_payload_content_cards,
)
from sr_od.application.currency_war.kernel.cw_intention import (
    IntentionState,
    clear_p1_recipe,
    p1_early_pair,
    pair_target_comp,
    update_p1_recipe,
)
from sr_od.application.currency_war.kernel.cw_registry import (
    DEFAULT_REGISTRY,
    DecisionV2Registry,
)
from sr_od.application.currency_war.kernel.cw_vocab import (
    Action,
    CwActionCloseShopParam,
    CwActionPickBoxCardParam,
    CwActionPickEncounterParam,
    CwActionPickExpertInviteParam,
    CwActionPickFortuneParam,
    CwActionPickInvestEnvParam,
    CwActionPickInvestStrategyParam,
    CwActionPickMegastarParam,
    CwActionPickPartnerParam,
    CwActionPickPlannerParam,
    CwActionPickStarTomeParam,
    CwActionPickSupplyParam,
    CwActionPickWishTrialParam,
    CwActionRefreshInvestCardsParam,
    CwActionRefreshNodeOptionsParam,
    CwActionRefreshSupplyParam,
)
from sr_od.application.currency_war.strategies.impl.cw_strategy import (
    CwStrategy,
    StrategySession,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1 import (
    encounter_pick,
    invest_env,
    invest_strategy,
    session_scope,
    supply,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.mandate_state import (
    StrategyState,
)
from sr_od.application.currency_war.strategies.impl.pick_bias import (
    PICK_BIAS,
    effect_pick_bias,
)

if TYPE_CHECKING:
    pass

# config 属 app 层,impl 层禁 import(cw_strategy.py 字符串注解先例);
# 实例由调用方按参注入。
CurrencyWarConfig = 'CurrencyWarConfig'

class CwFlowStrategy(CwStrategy[StrategyState]):
    """主流程驱动核(生命周期 + 战略层意向 + pick 族 + 备战主流程栈)。

    泛型绑定(设计正本 §1/§8.5/§8.6-6):本核即 mandate_v1
    流程核,``_TState`` 在此绑定为本实现的私有状态类型 StrategyState
    (基类 ``create_state`` 返回类型随之收窄)——框架基类仍只以泛型参数
    携带,零感知字段;kernel/one_dragon 零 import 本类型(布局锁定约束)。

    行为锚见各方法 docstring 与 sim 契约测试。
    """

    STRATEGY_ID: str = ''            # 中间辅助 ABC,不注册(_abstract=True)
    STRATEGY_NAME: str = '主流程驱动核(内部基类)'
    _abstract: bool = True

    def __init__(self, gs, config, registry: DecisionV2Registry | None = None):
        """终态契约 §2.1 构造注入(gs/config 归基类);registry 可注入
        (A/B:两套注册表各跑一分支);缺省=标定版。"""
        super().__init__(gs, config)
        self.registry = registry or DEFAULT_REGISTRY

    # ===== 生命周期(终态契约 §2.1:状态 = 实例属性,构造即冷建)=====

    def _create_state(self) -> StrategyState:
        """策略器状态对象工厂钩子实现(session.md §3.1/§5.1;决策-2)。

        每局冷建 StrategyState(本核即 mandate_v1 流程核;sim 初始相位注入
        经 ensure_strategy_state 构造入口,不经本钩子)。live 初值
        v3_phase='FORM'(原 on_match_start 的唯一非零缺省随
        生命周期并入迁入冷建口)。
        """
        st = StrategyState()
        st.v3_phase = 'FORM'
        return st

    # ===== 镜像族观察写者(mandate_v1 单分支)=====

    def write_shop_mirrors(self, state: GameState,
                           _ms: StrategyState) -> None:
        """逐帧写 ``v3_b_t`` 板面目标线支撑计数(纯遥测观测面)。

        口径 = B_t(件级单一源 ``cw_deploy_logic.
        board_target_line_weight``:deployed 中全羁绊 ∩
        SYSTEM_LINE_FACTIONS 非空件数,希儿本人单卡计入;bench 囤件
        不计入)。选 B_t 替代的依据:旧 ``v3_form_score``(min(2,
        engines+0.3×frac)/2 封顶连续量)在决策关键帧(boss 前/终局)
        恒常数 1.0 零方差、预测力为零;B_t 全样本有方差且是唯一
        p<0.001 显著代理(判读边界:预测力集中于 boss 战存活深度,
        对伤害差/终局 hp 仅弱正)。

        边界:本方法写 ``v3_b_t`` 与 ``v3_form_ok`` 两个观测键——旧
        ``v3_form_score`` 随本口径替换停用(历史账本只读,不再有写者)。
        ``v3_form_ok`` 写端已从停用 v2 相位机接回板面现读(死镜像处置批
        form_ok 死镜像处置:旧写端在 mandate_v1 下无写者恒 False,与
        发出判据核 出战就绪现读对账必然全量不一致——判读单一源 =
        第三十四局前后判读已定案);判据单一源 =
        ``cw_launch_admission.readiness_form_ok``(与发出 出战就绪同式,
        零第二实现)。``v3_phase`` 维持无写端停用缺省 ''(相位机已亡,
        无现读语义可接)。``v3_mirror_key`` 轮键戳照常盖章(键语义 =
        「本轮已写」,重复写守卫据此不重复触发)。纯遥测恢复:
        两字段不进任何判据(「form_score 降级纯遥测观测,不进
        判据」口径由 B_t 延续),写者本身零行为面。
        已知边界(如实声明):生产侧商店观察帧若 board 未播种,
        form_progress 现读恒 False——该帧族的 form_ok 读数是「观察帧
        board 口径」,与部署放行判定「轮入口全量 state 口径」存在帧差,判读
        时以 sim 账本(全量 state)为准。
        (终态契约 §2.5 impl 层:状态宿主 = 显式 ``_ms`` 形参。)
        """
        from sr_od.application.currency_war.kernel.cw_deploy_logic import (
            board_target_line_weight,
        )
        from sr_od.application.currency_war.kernel.cw_game_state import (
            deployed_rows_of,
        )
        from sr_od.application.currency_war.kernel.cw_launch_admission import (
            readiness_form_ok,
        )
        front, back = deployed_rows_of(state)
        deployed = [d for d in (*front, *back) if d is not None]
        # (无回退补缺:策略层禁读执行侧簿记,消费口只剩 game
        #  state——容器 deployed 空 = 板面真空的事实态,照写 0 不虚构。)
        # 件级计数:名字列表保留重复件(同名多件各计 1,禁 frozenset 去重)
        dep_names = [(getattr(d, 'char_id', '') or '') for d in deployed]
        _ms.v3_b_t = board_target_line_weight(dep_names)
        # form_ok 镜像现读写端(死镜像处置,见 docstring;判据单一源 =
        # readiness_form_ok,与发出 出战就绪同式)
        from sr_od.application.currency_war.kernel.cw_game_state import (
            plane_of as _plane_of,
        )
        from sr_od.application.currency_war.kernel.cw_game_state import (
            round_num_of as _round_num_of,
        )
        _ms.v3_form_ok = readiness_form_ok(
            state, getattr(_ms, 'target_comp', None))
        _ms.v3_mirror_key = (_plane_of(state), _round_num_of(state))

    # ===== 方向节拍内化(原战略层 update_target 并入为策略器私有
    #       刷新,触发信号 = 黑板帧刷新代次标注,非契约成员)=====

    def _ensure_intention(self, _ms) -> IntentionState:
        """意向状态机惰性就位(原 update_target 首段,原样保留;
        view 类帧刷新同样需要 ist 在位,故独立成共用段)。"""
        ist = _ms.v3_intention
        if not isinstance(ist, IntentionState):
            ist = _ms.v3_intention = IntentionState()
        return ist

    def _refresh_direction(self, state: GameState,
                           _ms: StrategyState) -> None:
        """方向节拍贵段(每 game-round 恰一次;键守卫)。

        意向层机器停用后,贵段 = **P1 过渡配方链驱动**
        (``update_p1_recipe``——配方对派生/冻结标志,line_and_upgrade
        §1.6 保留项);位面适用范围以窗口谓词承载(``plane2_started_of``
        布尔标志,宪法第 2 条合规——P1 配方物化触发的整改形态,非
        ``_plane_v == 1`` 位面字面量;P2 起停驱并清配方锁
        ``clear_p1_recipe``)。终局线选择不经本段——候选-锁定制在
        session_scope 前置段(``refresh_line_if_needed``,两入口先于
        本段执行)。便宜段 = 派生视图刷新
        (:meth:`_refresh_direction_views`),每次 full 帧入口一次。
        """
        ist = self._ensure_intention(_ms)
        key = (plane_of(state), round_num_of(state))
        if _ms.v3_intention_key != key:
            _ms.v3_intention_key = key
            if not session_scope.plane2_started_of(state):
                update_p1_recipe(state, ist, self.registry)
            else:
                # 进 P2:配方锁退场 + 开局面键同点清空(写端单一出口,
                # review-37 P1——P2 未锁窗禁消费过期 P1 配方;幂等,
                # 空对/已清帧 no-op)。
                clear_p1_recipe(ist, _ms)
                # 过渡锁定槽同点清空(清空点 = 进位面 2,统一保护集
                # design §2.1):位面 2 起过渡域关闭,槽只服务过渡域
                # 语义,与配方锁退场同帧出清无跨域残留;幂等(空槽 no-op)。
                _ms.transition_locked_systems = frozenset()
        self._refresh_direction_views(state, _ms)

    def _refresh_direction_views(self, state: GameState,
                                 _ms: StrategyState) -> None:
        """派生视图刷新(便宜段;view 类帧入口只走本段)。

        键面归一后的写位分布:

        - ``target_comp``(锁定线槽)**本段零写**——终态单写者 =
          ``session_scope.write_line_lock``(硬规则/时点兜底命中帧,
          P1 锁定局「互不覆写」的落地);
        - P1 未锁帧 = 过渡配方物化链写 ``opening_recipe_comp``
          (配方对伪阵容;窗口谓词覆盖——P2 起停写;空窗帧按
          ``p1_early_pair`` 无门槛方向物化,「空窗期同样有方向」的
          已登记语义保持);
        - ``v3_core_names`` = 现行方向(锁定线优先,未锁 = 配方)核心名。
        """
        ist = self._ensure_intention(_ms)
        comp = getattr(_ms, 'target_comp', None)
        if comp is None and not session_scope.plane2_started_of(state):
            pair = tuple(getattr(ist, 'p1_pair', ()) or ()) \
                or p1_early_pair(state, ist)
            _ms.opening_recipe_comp = pair_target_comp(pair) if pair else None
        direction = comp if comp is not None \
            else getattr(_ms, 'opening_recipe_comp', None)
        _ms.v3_core_names = set(direction.core_chars) if direction else set()
        if ist.last_event and ist.last_event not in (
                _ms.v3_last_intention_event,):
            log.info('[cw][d2] 意向 %s mode=p1_recipe(%s)',
                     ist.phase, ist.last_event)
        _ms.v3_last_intention_event = ist.last_event

    # ===== 决策入口统一内务:黑板帧代次消费(/§3.4)=====

    def _consume_prep_direction_frame(self) -> None:
        """备战黑板帧代次消费(备战入口与 pick 族入口共用;触发面)。

        帧 = full → :meth:`_refresh_direction` 全程(键新则状态机 + 评分遥测);
        帧 = view(破墙派生帧/finalize 买后暂存帧)→ 只刷派生视图;帧 = none
        → 读后复位即返回。
        读后即复位 'none'(消费即清,防同帧重复刷新;
        复位 = 读协议半部,非新鲜度宣告——帧类写点收敛归流程观察段,§3.4/D6)。
        刷新失败不阻塞决策(沿用原 ops 侧守卫语义,日志哨兵 [cw!] 保持)。
        终态契约 §2.1:决策输入一律 self.gs/self.state 自取(零参)。"""
        cls = self.gs.frame_class_prep
        if cls not in ('full', 'view'):
            return
        self.gs.frame_class_prep = 'none'
        try:
            if cls == 'full':
                self._refresh_direction(self.gs, self.state)
            else:
                self._refresh_direction_views(self.gs, self.state)
        except Exception as e:   # noqa: BLE001  方向刷新失败不阻塞决策(沿用旧向)
            log.warning('[cw!][strategy] 方向刷新异常(沿用旧方向): %s', e)

    def _consume_shop_direction_frame(self) -> None:
        """商店黑板帧代次消费(decide_shop_action 入口)。

        visit 首段 full 帧 → 刷新(键同只刷视图,视图源 = 商店入口帧 state);
        续段 none 帧 → 保持首段值(= 旧 ``_target_seeded``「仅首段重估」语义)。
        不捕获异常:与原 ops 侧 ``cw_op_buy_cards`` 首段直调的失败面一致
        (无守卫)。终态契约 §2.1:决策输入一律 self.gs/self.state 自取。"""
        cls = self.gs.frame_class_shop
        if cls not in ('full', 'view'):
            return
        self.gs.frame_class_shop = 'none'
        if cls == 'full':
            self._refresh_direction(self.gs, self.state)
        else:
            self._refresh_direction_views(self.gs, self.state)

    # ===== pick 族(事件/选卡决策;判据单源 = 策略层 mandate_v1(投资两屏
    # ===== /遭遇) / kernel cw_events/cw_comps(其余画面))=====
    # 终态契约 §2.1/§2.2:入口零参(候选 = gs payload 槽;离屏 None =
    # 观察层失约抛错,details §2.1 三分语义),输出 = 单一 CwAction——
    # 选卡 = per-screen 子类型,刷新建议 = 三刷新动作(与选卡互斥单发,
    # kernel 纯函数返回值由入口包装转动作,判据零触碰)。

    #: invest 刷新建议同帧去重键(StrategyState.scratch 键,局级生命周期)。
    _INVEST_ADVICE_MEMO_KEY = 'cw4_flow_invest_advice_key'

    def _require_slot_options(self, slot: object, slot_name: str) -> list:
        """payload 槽候选读口(黑板契约:进决策时 None = 观察层失约抛错,
        禁静默按空候选决策;details §2.1)。

        **选卡族失效触发集中挂点**(shop_session §4.2 读数协议②;批
        3.6):本读口 = 全部 pick 决策入口(三选一/二选一选卡族)共用
        的候选槽读口,prep/shop 决策不经此口——任何选卡帧在此失效金位
        账面(选中即失效实读,不枚举单项效果;刷新建议帧同样适用 = 保守侧,
        多失效一拍的代价 = 下次实读锚定)。
        """
        from sr_od.application.currency_war.strategies.impl.mandate_v1.criteria import (
            shop_session as _shop_sess,
        )
        _shop_sess.note_pick_frame(self.gs)
        value = getattr(slot, 'value', None)
        if value is None:
            raise ValueError(
                f'decide: payload 槽离屏(None = 观察层失约,'
                f'禁静默按空态决策;槽 = {slot_name})')
        return value

    def decide_invest_strategy(self) -> CwActionPickInvestStrategyParam | CwActionRefreshInvestCardsParam:
        """投资策略 3 选 1(终态零参口;候选 = ``gs.invest_strategy_opts``)。"""
        return self._decide_invest('strategy', self.gs.invest_strategy_opts,
                                   'invest_strategy_opts',
                                   CwActionPickInvestStrategyParam)

    def decide_invest_env(self) -> CwActionPickInvestEnvParam | CwActionRefreshInvestCardsParam:
        """投资环境 3 选 1(终态零参口;候选 = ``gs.invest_env_opts``)。"""
        return self._decide_invest('env', self.gs.invest_env_opts,
                                   'invest_env_opts',
                                   CwActionPickInvestEnvParam)

    def _decide_invest(self, kind: str, slot: object, slot_name: str,
                       pick_param_cls: type) -> CwActionPickInvestStrategyParam | CwActionPickInvestEnvParam | CwActionRefreshInvestCardsParam:
        """投资策略/投资环境共用决策核(原 decide_invest 双相拆分)。
        ``pick_param_cls`` = 屏别词表类(词表拆类后由各入口显式传入,
        输出 = 该类实例)。
        两轴判据单一源均在策略层(kind 分派;宪法五「衍生估值/评序归
        策略层」;意向解析留 flow,三参同源直通):
        - env → ``invest_env.decide``/``decide_pick``
          (:meth:`_decide_invest_env_frame`;判据正本 = strategy-docs
          28 号稿);
        - strategy → ``invest_strategy.decide``/``decide_pick``
          (:meth:`_decide_invest_strategy_frame`;判据正本 =
          strategy-docs/29_invest_strategy_screen.md)。
        (用户裁定 2026-09-08「投资选卡优先经济、然后是终局阵容,
        不为过渡阵容服务」):两轴对齐源均 = 意向状态 D*① 三参
        (locked_comp/demoted_endgame/evicted 同源 ist)传入策略层;旧
        ``target_comp`` 对 invest kind 不消费(P1 期它是过渡配方对物化的
        伪阵容,适用范围错位;encounter 等 pick 族消费面不变,supply 已随
        补给画面策略迁移同源改挂 ist——解析后传 comp 对象)。
        选卡结果喂 CommitSignals——**建议帧跳过喂入、选卡帧保留**(喂入
        面申报见 :meth:`_feed_invest_strategy_signals`;env 侧喂入已随环境
        轴迁移删除)。
        三闸点击链留 handler——闸全败帧 handler 同访问再调本入口取选卡:
        同帧去重 memo(scratch 键 = (kind,候选元组))保证「建议帧首调发
        建议、紧随重调落选卡后键清」——重入访问(新候选/同候选)恢复首调
        语义。memo 命中的落选卡改调策略层 ``decide_pick`` 纯选卡口(decide
        是纯函数,重调仍返建议;缺此口则建议帧三闸全败时 op round_fail,
        现实可达路径)。
        """
        options = list(self._require_slot_options(slot, slot_name))
        # 入口内务(:pick 入口入触发面;消费最近一次备战黑板帧)
        self._consume_prep_direction_frame()
        _ist = self._ensure_intention(self.state)
        if kind == 'env':
            return self._decide_invest_env_frame(options, pick_param_cls, _ist)
        return self._decide_invest_strategy_frame(options, pick_param_cls, _ist)

    def _decide_invest_strategy_frame(self, options: list, pick_param_cls: type,
                                      ist: IntentionState,
                                      ) -> CwActionPickInvestStrategyParam | CwActionRefreshInvestCardsParam:
        """投资策略轴决策(策略层单一源 = ``invest_strategy.decide``;判据
        正本 = strategy-docs 投资策略画面篇):纯值出口在此包装动作词表,
        op handler 与观察写槽零改动。同帧去重 memo 语义与 env 侧同构
        (键 = (kind,候选元组)):建议帧首调发逐卡刷新建议(slots = 策略层
        动作集,与选卡互斥——旧 kernel 单口非互斥返回的语义分界),紧随
        重调落选卡走 :func:`invest_strategy.decide_pick` 同一评分基线,
        零选卡漂移。"""
        out = invest_strategy.decide(
            options, self.gs,
            locked_comp=ist.locked_comp,
            demoted_endgame=ist.demoted_endgame,
            evicted=frozenset(ist.evicted),
            config=self.config)
        memo_key = ('strategy', tuple(options))
        if isinstance(out, invest_strategy.StrategyRefreshSuggestion):
            if self.state.scratch.get(self._INVEST_ADVICE_MEMO_KEY) == memo_key:
                # 同帧重调(handler 三闸全败回退)= 建议已发,落选卡并清键
                #(键清 = 下一访问恢复首调建议语义)。
                self.state.scratch.pop(self._INVEST_ADVICE_MEMO_KEY, None)
                out = invest_strategy.decide_pick(
                    options, self.gs,
                    locked_comp=ist.locked_comp,
                    demoted_endgame=ist.demoted_endgame,
                    evicted=frozenset(ist.evicted),
                    config=self.config)
            else:
                self.state.scratch[self._INVEST_ADVICE_MEMO_KEY] = memo_key
                return CwActionRefreshInvestCardsParam(slots=tuple(out.slots),
                                                       reason=out.reason)
        # 选卡结果喂 CommitSignals(条件活遥测;建议帧不落此段)。
        self._feed_invest_strategy_signals(options)
        return pick_param_cls(idx=out.idx, reason=out.reason)

    def _feed_invest_strategy_signals(self, options: list) -> None:
        """所选帧对各线的 affinity → 阵容分贡献(策略 2.0 权重;纯遥测,
        决策面零消费——投资源不参与证明自身的反自馈检查现状即合规)。
        喂入面申报(29 号稿 §4 遥测条款):建议帧跳过喂入——
        常规建议帧被帧级门拦定义型 → affinity 键喂入恒空,跳过即零漂移;
        E-豁免角例外 = 被禁定义型卡不拦建议帧,该帧会喂入非空
        affinity,跳过 = 纯遥测漂移(决策面零消费、罕见角,如实申报)。
        best-effort:信号喂入失败不影响决策。"""
        try:
            from sr_od.application.currency_war.kernel.cw_comps import augment_affinity
            scores: dict[str, float] = {}
            for opt in options:
                aff = augment_affinity(opt)
                for comp_name, v in aff.items():
                    scores[comp_name] = max(scores.get(comp_name, 0.0), v)
            if scores:
                from sr_od.application.currency_war.kernel.cw_transition import (
                    CommitSignals,
                )
                _cs = self.state.commit_signals
                if _cs is None:
                    _cs = self.state.commit_signals = CommitSignals()
                _cs.add('invest_strategy', scores)
        except Exception:   # noqa: BLE001  信号喂入 best-effort
            pass

    def _decide_invest_env_frame(self, options: list, pick_param_cls: type,
                                 ist: IntentionState,
                                 ) -> CwActionPickInvestEnvParam | CwActionRefreshInvestCardsParam:
        """投资环境轴决策(策略层单一源 = ``invest_env.decide``;判据正本
        = strategy-docs/28_invest_env_screen.md):纯值出口在此包装动作词表,
        op handler 与观察写槽零改动。
        同帧去重 memo 语义不变(键同策略轴结构 = (kind,候选元组)):
        建议帧首调发建议——环境屏 = 整组重掷(单全局钮,handler 只消费
        slots 真值哨兵,输出契约 = slots 全帧槽位);紧随重调落选卡——decide 是纯函数,再调仍返建议,落选卡走
        :func:`invest_env.decide_pick` 同一评分基线,零选卡漂移。"""
        out = invest_env.decide(
            options, self.gs,
            locked_comp=ist.locked_comp,
            demoted_endgame=ist.demoted_endgame,
            evicted=frozenset(ist.evicted),
            config=self.config)
        memo_key = ('env', tuple(options))
        if isinstance(out, invest_env.RefreshSuggestion):
            if self.state.scratch.get(self._INVEST_ADVICE_MEMO_KEY) == memo_key:
                # 同帧重调(handler 刷新闸全败回退)= 建议已发,落选卡并清键
                #(键清 = 下一访问恢复首调建议语义)。
                self.state.scratch.pop(self._INVEST_ADVICE_MEMO_KEY, None)
                out = invest_env.decide_pick(
                    options, self.gs,
                    locked_comp=ist.locked_comp,
                    demoted_endgame=ist.demoted_endgame,
                    evicted=frozenset(ist.evicted),
                    config=self.config)
            else:
                self.state.scratch[self._INVEST_ADVICE_MEMO_KEY] = memo_key
                return CwActionRefreshInvestCardsParam(
                    slots=tuple(range(len(options))), reason=out.reason)
        return pick_param_cls(idx=out.idx, reason=out.reason)

    def decide_supply(self) -> CwActionPickSupplyParam | CwActionRefreshSupplyParam:
        """补给选装备/出钻(终态零参口;候选 = ``gs.supply`` payload)。
        判据单一源 = 策略层 ``supply.decide``(三级字典序 钻>终局角色>
        装备 + 刷新「三级全空才刷」,次数闸内嵌 decide;纯值出口在此包装
        动作词表,op handler 与观察写槽零改动)。意向解析照 invest 兄弟
        入口同源 ist:locked_comp 套名经 get_comp 解析(空串 = 未锁 None
        无告警,解析失败 None + 告警哨兵,decide_box_card 同款)、
        demoted_endgame 直通。"""
        options = self._require_slot_options(self.gs.supply,
                                             'supply').options
        self._consume_prep_direction_frame()   # 入口内务
        _ist = self._ensure_intention(self.state)
        locked_comp = None
        if _ist.locked_comp:
            locked_comp = get_comp(_ist.locked_comp)
            if locked_comp is None:
                # 注册表漂移:按未锁口径选卡(保守向——漏提权非错提权)
                log.warning('[cw!][supply] locked_comp 解析失败(%s),'
                            '按未锁口径选卡', _ist.locked_comp)
        out = supply.decide(options, self.gs, locked_comp,
                            _ist.demoted_endgame)
        if isinstance(out, supply.SupplyRefreshSuggestion):
            return CwActionRefreshSupplyParam(reason=out.reason)
        return CwActionPickSupplyParam(idx=out.idx, reason=out.reason)

    def decide_encounter(self) -> CwActionPickEncounterParam | CwActionRefreshNodeOptionsParam:
        """遭遇选档/分支刷新(终态零参口;候选 = ``gs.encounter`` payload)。
        判据单一源 = 策略层 ``encounter_pick.decide``(能力态直通形:κ_S
        三态 + 经验档层 + 奖励序数 tiebreak + 刷新阀;判据正本 =
        strategy-docs/31 号稿);刷新次数闸内嵌 decide(读
        ``gs.encounter_refresh_left`` 剩余语义,用户裁定 2026-09-21,
        全域规范 = op-layer.md §1.4;None = 未观察 → 不可刷 fail-closed),
        不设 refresh_used 预计算。纯值出口在此包装动作词表,op handler
        与观察写槽零改动(照 decide_supply 先例)。"""
        options = self._require_slot_options(self.gs.encounter,
                                             'encounter').options
        self._consume_prep_direction_frame()   # 入口内务
        out = encounter_pick.decide(options, self.gs)
        if isinstance(out, encounter_pick.EncounterRefreshSuggestion):
            return CwActionRefreshNodeOptionsParam(reason=out.reason)
        return CwActionPickEncounterParam(idx=out.idx, reason=out.reason)

    def decide_megastar(self) -> CwActionPickMegastarParam:
        """巨星选候选(终态零参口;候选 = 容器 ``megastar_opts``,值域 =
        标准化门保证的规范名,op-layer.md §1.1):委托
        ``cw_comps.select_megastar`` 拿角色名 → 名在 options 命中该 idx。
        非空候选恒命中(``select_megastar`` 选择序 + naive 层保证),候选
        空不可达(画面 op 守卫 fail 零盲发),本函数无缺省支。"""
        options = self._require_slot_options(self.gs.megastar_opts,
                                             'megastar_opts')
        self._consume_prep_direction_frame()   # 入口内务
        available = [o.char_id for o in options if o.char_id]
        chosen_name = cw_comps.select_megastar(
            self.gs, session_scope.direction_comp_of(self.gs), available)
        if chosen_name:
            for o in options:
                if o.char_id == chosen_name:
                    return CwActionPickMegastarParam(
                        idx=o.idx,
                        reason=f"select_megastar 命中 {chosen_name}")
        raise AssertionError(
            'select_megastar 对非空候选恒返回成员(naive 层保证);'
            '候选空不可达(画面侧守卫 fail)')

    def decide_partner(self) -> CwActionPickPartnerParam:
        """选择伙伴(终态零参口;候选 = ``gs.partner_opts``):优先
        ``config.character_build_around`` / ``target.core_chars`` 命中;否则 idx=0。
        ⚠️ OCR 未就绪(char_id 全空 → 命中恒失败 → idx=0 = 今天盲点 stage 立绘,随阶段5)。"""
        options = self._require_slot_options(self.gs.partner_opts,
                                             'partner_opts')
        self._consume_prep_direction_frame()   # 入口内务
        wants: list[str] = list(getattr(self.config, 'character_build_around', []) or [])
        _dir_c = session_scope.direction_comp_of(self.gs)
        if _dir_c is not None:
            wants += list(_dir_c.core_chars)
        for o in options:
            if o.char_id and o.char_id in wants:
                return CwActionPickPartnerParam(idx=o.idx, reason=f"命中偏好/核心 {o.char_id}")
        return CwActionPickPartnerParam(idx=0, reason="fallback(OCR 未就绪,char_id 空)")

    def decide_planner(self) -> CwActionPickPlannerParam:
        """银狼策划事件(终态零参口;候选 = ``gs.planner_opts``;r104 用户定调:
        接入策略模块由它定;委托 cw_events.decide_planner)。

        升费卡打分含银狼线/在场判定(state.bench+deployed 的 char_id),
        target_comp 决定银狼线加成。"""
        options = self._require_slot_options(self.gs.planner_opts,
                                             'planner_opts')
        self._consume_prep_direction_frame()   # 入口内务
        pick = cw_events.decide_planner(
            options, self.gs, session_scope.direction_comp_of(self.gs))
        return CwActionPickPlannerParam(idx=pick.idx, reason=pick.reason)

    def decide_star_tome(self) -> CwActionPickStarTomeParam:
        """星徽秘典四选一(终态零参口;候选 = ``gs.star_tome_opts``;r104 接入
        策略模块;原 loop 内联 board 匹配迁此)。

        打分:①target_comp.all_factions 命中(终局线需要的阵营星徽 = +40);
        ②board 已有该阵营(板上已有=边际价值高,board 计数 ×8);
        ③当前配方框架阵营命中(双轨期过渡配方需要,+15)。无命中 fallback idx=0。"""
        options = self._require_slot_options(self.gs.star_tome_opts,
                                             'star_tome_opts')
        self._consume_prep_direction_frame()   # 入口内务
        if not options:
            return CwActionPickStarTomeParam(idx=0)
        fw = getattr(self.state, 'transition_framework', '')
        _fw_facs: set[str] = set()
        if fw:
            from sr_od.application.currency_war.knowledge.cw_line_facts import (
                FRAMEWORK_FACTIONS,
            )
            _fw_facs = set(FRAMEWORK_FACTIONS.get(fw, ()) or ())
        _dir_c = session_scope.direction_comp_of(self.gs)
        _tgt_facs: set[str] = set(
            _dir_c.all_factions or []) if _dir_c is not None else set()
        best_i, best_s = 0, -1.0
        for i, name in enumerate(options):
            s = 0.0
            from one_dragon.utils import str_utils
            if name in _tgt_facs:
                s += PICK_BIAS.tome_target_faction
            _board = (self.gs.board.value or {})
            hit = next((b for b, n in _board.items()
                        if n > 0 and str_utils.find_by_lcs(b, name, percent=0.8)), None)
            if hit is not None:
                s += PICK_BIAS.tome_board_hit * _board[hit]
            if name in _fw_facs:
                s += PICK_BIAS.tome_framework_faction
            if s > best_s:
                best_i, best_s = i, s
        return CwActionPickStarTomeParam(idx=best_i)

    def decide_wish_trial(self) -> CwActionPickWishTrialParam:
        """祈愿试炼选卡(终态零参口;候选 = ``gs.wish_trial_opts``)。

        options = 各卡 objective 文字(OCR)。打分:①金币类(直接经济,阵容无关
        稳妥)+25;②target/框架阵营相关词命中 +20;③「刷新/购买」类操作向
        (与 DP 攒息协同)+10;无信息 fallback idx=0。"""
        options = self._require_slot_options(self.gs.wish_trial_opts,
                                             'wish_trial_opts')
        self._consume_prep_direction_frame()   # 入口内务
        if not options:
            return CwActionPickWishTrialParam(idx=0)
        _dir_c = session_scope.direction_comp_of(self.gs)
        _tgt_facs: set[str] = set(
            _dir_c.all_factions or []) if _dir_c is not None else set()
        fw = getattr(self.state, 'transition_framework', '')
        _fw_facs: set[str] = set()
        if fw:
            from sr_od.application.currency_war.knowledge.cw_line_facts import (
                FRAMEWORK_FACTIONS,
            )
            _fw_facs = set(FRAMEWORK_FACTIONS.get(fw, ()) or ())
        best_i, best_s = 0, -1.0
        for i, obj in enumerate(options):
            s = effect_pick_bias(self.gs, obj)
            if '金币' in obj:
                s += PICK_BIAS.wish_gold
            if any(f in obj for f in (_tgt_facs | _fw_facs)):
                s += PICK_BIAS.wish_faction
            if '刷新' in obj or '购买' in obj:
                s += PICK_BIAS.wish_operation
            if s > best_s:
                best_i, best_s = i, s
        return CwActionPickWishTrialParam(idx=best_i)

    def decide_box_card(self) -> CwActionPickBoxCardParam:
        """武装箱/节点弹窗装备卡 4 选 1(终态零参口;候选 =
        ``gs.box_card_names``;薄壳;armory-box-value 定稿设计
        §2.2-§2.5)。锚 = 意向状态 locked_comp 两态(get_comp 失败落未锁 +
        日志哨兵,保守向);打分唯一住共享机器 ``pick_equipment``(序数
        分档 + 近兑现 + 通用输出先验,design §2.2/§2.3),本壳零打分实现。
        库存账(design §2.5):备用 ``gs.equips`` 现值(近兑现对数)+
        部署位/备战席穿戴账(合计进总持有,需求守卫)。effect_pick_bias
        通道随薄壳化移除(恒 0 无行为差,处置声明见 design §1.4)。
        无信息 fallback idx=0(机器 names 空契约)。"""
        names = self._require_slot_options(self.gs.box_card_names,
                                           'box_card_names')
        self._consume_prep_direction_frame()   # 入口内务
        if not names:
            return CwActionPickBoxCardParam(idx=0)
        _ist = self._ensure_intention(self.state)
        locked = _ist.locked_comp
        key_equips: list[str] = []
        if locked:
            comp = get_comp(locked)
            if comp is None:
                # 注册表漂移:按未锁态打分(保守向——漏提权非错提权)
                log.warning('[cw!][box] locked_comp 解析失败(%s),按未锁态打分',
                            locked)
            else:
                key_equips = list(comp.key_equips or ())
        # 终态契约 §B:spare 库存打分源 = gs.equips(镜像停用)。
        spare = list(self.gs.equips.value or [])
        # 在身装备(game state 唯一消费口:策略禁读执行侧
        # 簿记)—— deployed 单成员带
        # equips,bench 槽位视图成员 = Unit(含 equips 透传)。
        from sr_od.application.currency_war.kernel.cw_game_state import (
            bench_units_of,
            deployed_rows_of,
        )
        _gs_wear = self.gs
        _wf, _wb = deployed_rows_of(_gs_wear)
        worn = [eq
                for _u in (*_wf, *_wb, *bench_units_of(_gs_wear))
                if _u is not None
                for eq in (getattr(_u, 'equips', None) or [])]
        from sr_od.application.currency_war.kernel.cw_equip_value import (
            pick_equipment,
        )
        return CwActionPickBoxCardParam(idx=pick_equipment(
            names, key_equips=tuple(key_equips),
            owned_spare=spare,
            owned_total=spare + worn))

    # ===== 契约扩员新入口(普查迁移;判据
    # ===== 并入 kernel,本壳零打分实现,委托同构 decide_box_card 先例)=====

    def decide_fortune(self) -> CwActionPickFortuneParam:
        """命运卜者强化三选一(终态零参口;候选 = ``gs.fortune_opts``
        OCR 卡文;判据单一源 = kernel ``decide_fortune`` 战力关键词权重
        argmax,无匹配缺省首卡,handler 侧无越界兜底——返回词表外/None =
        调用方具名 fail 零盲发,idx 越界 = 调用方守卫断言
        (``cw_screen_fortune.py::CwScreenFortune.act`` 决策出口守卫))。"""
        texts = list(self._require_slot_options(self.gs.fortune_opts,
                                                'fortune_opts'))
        self._consume_prep_direction_frame()   # 入口内务
        return CwActionPickFortuneParam(idx=cw_events.decide_fortune(texts))

    def decide_expert_invite(self) -> CwActionPickExpertInviteParam:
        """专家邀请函选卡(终态零参口;候选 = ``gs.expert_invite`` 弹窗
        载体(卡羁绊解析 + 板面羁绊计数,写端 = CwScreenExpertInvite);
        判据单一源 = kernel ``choose_expert_index`` 三级语义原样(在场
        浓度版),idx = -1 表现金为王。

        行为分叉申报:kernel 判据与 13_pick_family.md E9 在案规格(目标线
        成员优先 → 池浓度)分叉,已登记待办:独立行为变更(迁移报告),本
        入口保持实码行为、不擅自切规格。"""
        payload = self._require_slot_options(self.gs.expert_invite,
                                             'expert_invite')
        self._consume_prep_direction_frame()   # 入口内务
        return CwActionPickExpertInviteParam(idx=cw_events.choose_expert_index(
            list(payload.card_bonds), dict(payload.board)))

    def decide_shop_action(self) -> Action:
        """商店单动作决策接口(/2/5;升格入契约面;
        终态零参口 §2.1:决策输入一律 self.gs/self.state/self.config)。

        输入 = gs 容器(黑板契约容器化,设计件《商店黑板容器化方案》
        §2.2-1:入口观察/单动作逻辑态直写/世界写点);输出 = **恰一个
        动作**,全函数永不 None——「无动作可做」由 ``CwActionCloseShopParam`` 恒可用
        终结表达(决策 5/6)。决策本体 = ``mandate_v1/shop.
        decide_shop_action``(选择序 = 决策本体候选扫描序,逐帧恰取一个
        动作)。执行侧单动作循环逐帧调用本接口;sim/兼容路径走
        :meth:`decide_shop_screen` 驱动器(同核循环化)。
        观察帧缺失 = 观察层失约,抛错(禁静默按空态决策)。
        入口内务 = 帧代次消费(:meth:`_consume_shop_direction_frame`;
        方向刷新在决策读视图之前完成,内化锚)。
        受限会话自限(分层依据 = flow/README.md §1 决策控制分层铁律):
        决策本体产出唯一提案后,受限会话活跃帧(出战就绪 ∧ 金超利息线
        派生标记,每帧现算 = bridge.launch_restricted_session_active)经
        kernel ``launch_arbitration_gate`` 谓词检(与 flow 闸同源同参,零
        判定数学复制)——拒 = 决策改发 ``CwActionCloseShopParam``(消费
        终止非改试次优,金出口族红线 5),受阻分键 ``launch_arbitrage_
        gate_blocked`` 落策略器状态 cw4_counters;非受限会话帧现行为逐位
        不变。生产单动作循环与回放/序列驱动器同经本口,两面同源自限
        (kernel 模块头「两面共用判定核」拓扑)。"""
        from sr_od.application.currency_war.strategies.impl.mandate_v1 import (
            shop,
        )
        # 决策入口容器契约(设计件《商店黑板容器化方案》§2.2-1):
        # 输入 = 容器单例,无二次快照;在屏前置 = ``gs.shop.value is not
        # None`` 才可决策——离屏帧进决策 = 观察层失约同型抛错(黑板契约
        # None 检查的容器等价物,「禁静默按空牌面决策」语义不变)。开店态
        # OCR 失读窗 = 容器沿用上一开店牌面(喂入口失读不写),照旧决策、
        # 执行侧核对兜底。
        gs = self.gs
        if gs.shop.value is None:
            raise ValueError(
                'decide_shop_action: 容器商店 payload 离屏(shop=None)'
                '(黑板契约容器化:在屏前置 gs.shop.value is not None;'
                'None=观察层失约,禁静默按空态决策)')
        # 未观察门(观察态落容器字段,策略消费只走 game state):主域观察锚
        # 主账未按屏幕真值锚定(接管/重置/账失效事件后,备战环 heavy 观察
        # 尚未置位)时商店决策的关键输入(席面)不可信——返回恒可用终结
        # CwActionCloseShopParam 交商店画面 op 执行收店,外循环全分支重判自然落回备战节点,heavy
        # 观察完成锚定后再进店;店内不做任何原地重建(读屏重建出口已停用)。
        # 判定单一源 = kernel cw_game_state.tracked_unobserved;跳过事件
        # 留痕与连续跳过熔断在执行侧商店画面 op 的 CwActionCloseShopParam 出口。
        from sr_od.application.currency_war.kernel.cw_game_state import (
            tracked_unobserved,
        )
        if tracked_unobserved(self.gs):
            log.info('[cw][shop] tracked 未观察(待备战 heavy 观察锚定)'
                     '→ CwActionCloseShopParam 交回外循环重判')
            return CwActionCloseShopParam()
        # 入口刷新先于镜像/决策(方向视图 = 本帧语境;内化锚)
        self._consume_shop_direction_frame()
        # v3_b_t 逐帧镜像写者(纯遥测,零行为面;口径与边界见
        # write_shop_mirrors docstring。旧 v3_form_score 已随口径
        # 替换停用,历史账本只读)。写位 = 决策核入口 = 生产单
        # 动作循环与序列驱动器(decide_shop_screen)共同必经点。
        self.write_shop_mirrors(gs, self.state)
        # 决策本体宿主 = gs(state_of(gs) → 同源接线策略器状态;
        # game_state_of(gs) 本体直通——经 self.state 传递会让 kernel 侧
        # game_state_of 解析到一次性空容器,禁)。
        action = shop.decide_shop_action(gs, gs, self.config,
                                         registry=self.registry)
        # 动作发出帧受限消费·策略侧自限(详设 §2.10;flow 闸停用前的先行落地
        # ——受限会话内自限先拦,闸永不触拒,行为与现役逐位一致)。标记
        # 派生与谓词皆 kernel 单一源直调;金读 = 容器读口 gold_of,与 flow
        # 闸闭包同帧同值(决策与检之间零动作,期望态无推进)。
        from sr_od.application.currency_war.kernel.cw_launch_arbitrage import (
            KEY_GATE_BLOCKS,
            launch_arbitration_gate,
        )
        from sr_od.application.currency_war.strategies.impl.mandate_v1.bridge import (
            launch_restricted_session_active,
        )
        if not launch_restricted_session_active(gs):
            return action   # 非受限会话帧:现行为逐位不变(零检零遥测)
        _ok, _why = launch_arbitration_gate(action, gold_of(gs), gs)
        if _ok:
            return action
        # 拒 = 消费终止:本动作不执行,决策改发 CloseShop 收访问(评估序
        # 不变、不跳过高位改试低位 = 金出口族红线 5 逐位平移,非改试次优)。
        # 受阻遥测分键 = kernel 常量(现役 flow 闸闭包同键写入 cw4_counters,
        # run-1 两写点按动作互斥不自增;run-2 闸停用后本写点为唯一写点,
        # 分键宿主随拒拍落 strategy_state,详设 §2.10)。
        _ct = getattr(self.state, 'cw4_counters', None)
        if isinstance(_ct, dict):
            _ct[KEY_GATE_BLOCKS] = _ct.get(KEY_GATE_BLOCKS, 0) + 1
        return CwActionCloseShopParam()

    def decide_shop_screen(self, session: StrategySession | None = None,
                           config: CurrencyWarConfig | None = None
                           ) -> list[Action]:
        """商店序列兼容驱动器(缺省实现;降格出 ABC;形参 = 兼容宿主
        (回放/序列测试调用面照旧传),决策已零参化,本体不消费)。

        回放/既有序列测试消费(生产执行侧走单动作循环):逐帧调
        :meth:`decide_shop_action`(单动作核,帧代次消费在核入口)+ 逐动作
        直调上报函数推进期望态(kernel/cw_action_report 函数族;零
        simulate 前瞻消费),终结动作(CwActionRefreshShopParam)截停、
        ``CwActionCloseShopParam`` 收尾不入序列。本缺省 = 通用
        循环(不绑 mandate 判据);mandate 特有记账(已买件/段序号/续段
        token)在 ``MandateV1Strategy.decide_shop_screen`` 覆写。观察帧
        缺失 = 观察层失约,抛错。"""
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
        )
        # 驱动器同路(设计件 §2.2-3):决策读容器单例 + 期望态
        # 推进 = 逐动作直调上报函数(动作 op 重组:快照三件组已内聚
        # 买牌上报,双抄写段停用);逐域期望态由投影测试钉住
        # (test_shop_projection_logic,测试 M1)。帧缺失 = 容器离屏 =
        # 观察层失约同型抛错(在屏前置)。
        gs = self.gs
        if gs.shop.value is None:
            raise ValueError(
                'decide_shop_screen 驱动器: 容器商店 payload 离屏'
                '(shop=None;黑板契约:观察段是唯一写者;None=观察层失约,'
                '禁静默按空态决策)')
        _sig = ChannelSig(family='logic_action', actor='CwFlowStrategy',
                          mode='compute',
                          group_id=f'act:CwFlowStrategy@{gs.write_seq + 1}')

        def _report(a) -> None:
            """逐动作直调上报函数(上报函数族分支;离线驱动无落地门,k 判据
            与生产执行侧 merge_buy_k 同源派生,禁按动作对象预估的第二实现)。"""
            if isinstance(a, cw_state.CwActionBuyCardParam):
                # 满席才评多买(容器 kind 口逐槽占用;与旧「槽表全占用」
                # 形态逐位等价——刻意不走 bench_is_full,其随 BenchView.
                # capacity 走,节省工位改写帧读数不同,本驱动器改形不改
                # 语义;bench 未观察 = 不满 = 单买,零漂移)。
                _k = 1
                from sr_od.application.currency_war.kernel.cw_game_state import (
                    slot_occupies,
                )
                _view = gs.bench.value
                if _view is not None and all(
                        s is not None and slot_occupies(s.kind)
                        for s in _view.slots):
                    from sr_od.application.currency_war.kernel.cw_game_state import (
                        bench_entries_of,
                        deployed_rows_of,
                    )
                    from sr_od.application.currency_war.kernel.cw_merge_simulate import (
                        merge_buy_k,
                    )
                    _front, _back = deployed_rows_of(gs)
                    _k = max(1, merge_buy_k(
                        a.card.name, a.card.star or 1, bench_entries_of(gs),
                        [d for d in (*_front, *_back) if d is not None],
                        shop_payload_content_cards(gs.shop.value)
                        if gs.shop.value is not None else []))
                report_action_buy_card_param(
                    gs, a, _sig, executed=ShopActionExecuted(bought_count=_k))
            elif isinstance(a, cw_state.CwActionSellBenchParam):
                report_action_sell_bench_param(gs, a, _sig)
            elif isinstance(a, cw_state.CwActionSellDeployedParam):
                report_action_sell_deployed_param(gs, a, _sig)
            elif isinstance(a, cw_state.CwActionSwapDeployParam):
                report_action_swap_deploy_param(gs, a, _sig)
            elif isinstance(a, (cw_state.CwActionLevelUpParam,
                                cw_state.CwActionLevelUpShopParam)):
                report_action_level_up_param(
                    gs, a, _sig, executed=ShopActionExecuted(levelup_clicks=1))

        out: list[Action] = []
        for _ in range(512):   # 防御上界:决策循环不收敛 = 策略器 bug 响亮暴露
            a = self.decide_shop_action()   # 零参单动作核(终态契约 §2.1)
            if isinstance(a, cw_state.CwActionCloseShopParam):
                return out
            out.append(a)
            if isinstance(a, cw_state.CwActionRefreshShopParam):
                return out      # 终结 op:序列到止(重观察语境)
            _report(a)
        from sr_od.application.currency_war.kernel.cw_game_state import (
            bench_is_full,
        )
        raise RuntimeError(
            'decide_shop_screen 驱动器 512 帧未收敛(策略器 bug:'
            f'末态 gold={gold_of(gs)} '
            f'bench={bench_is_full(gs)})')
