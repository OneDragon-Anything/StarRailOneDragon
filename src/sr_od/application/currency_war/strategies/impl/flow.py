"""货币战争 主流程驱动核(CwFlowStrategy;自 decision_v2/strategy.py 迁入,
策略统一迁移批——底稿 MAP ⓪ A1「迁移白名单」)。

辖域 = mandate_v1 未覆写的域实现:

- 生命周期收编后的唯一冷建口 create_session(策略器状态工厂接线 + live
  初值 v3_phase='FORM' 一并在此落位)与策略器状态工厂 create_state;
- 方向节拍内化(:meth:`_refresh_direction`;ADR-0583:方向重估从流程侧
  ops 直调收进策略器,触发信号 = 黑板帧刷新代次标注,键守卫贵段每
  game-round 恰一次 + 便宜派生视图段);
- ``session.pending_round_outcomes`` 槽 = 观察半累积面(决策消费侧已退);
- pick 族(decide_invest/supply/encounter/megastar/partner/planner/
  star_tome/wish_trial/box_card + 契约扩员三口 fortune/expert_invite/
  equip_pick,普查迁移批 2);
- 商店序列兼容驱动器 decide_shop_screen 缺省实现(降格出 ABC,
  ADR-0583;sim/回放/序列锁消费,mandate 记账在其覆写)与商店单动作
  接口 decide_shop_action(ADR-0517,委托 mandate_v1/shop)。

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
from sr_od.application.currency_war.kernel import cw_comps, cw_equip_value, cw_events
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
    hoard_target_set,
    p1_early_pair,
    pair_target_comp,
    update_intention,
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
    CwActionPickEquipParam,
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
from sr_od.application.currency_war.strategies.impl.mandate_v1.mandate_state import (
    StrategyState,
)
from sr_od.application.currency_war.strategies.impl.pick_bias import (
    PICK_BIAS,
    effect_pick_bias,
)

if TYPE_CHECKING:
    pass

# config 属 app 桶,impl 桶禁 import(cw_strategy.py 字符串注解先例);
# 实例由调用方按参注入。
CurrencyWarConfig = 'CurrencyWarConfig'

# ===== 面③出辖观察件(锁生成可行性;纯观测零行为)=====
# lock_gen_feasibility_obs_* 族(低血带新开 lock 开启率/切阵后 N 轮内亡率/
# 死区面计数)。落位申报:消费位在本文件(strategies 侧)而非
# kernel.cw_intention——分键带判定需消费 p1/p2_blood_floor 域谓词与
# λ 血带锚(strategies 层判据单一源),kernel 观察位禁反向 import
# strategies(布局依赖矩阵);本观察件随 update_intention 生产驱动面
# (CwFlowStrategy._refresh_direction 贵段)同频触发。
#: 分键前缀(键族与 241/245 键族零交集;键写入
#: strategy_state.cw4_counters,经局终快照链/sim 轮差分入账本)。
LOCK_GEN_FEASIBILITY_OBS_PREFIX: str = 'lock_gen_feasibility_obs_'

#: 锁开事件判定 = last_event 转移入锁类前缀(信号锁 'lock:'/强锁
#: 'forced_lock:'/P2 移交 'handoff_lock:';撤销/驱逐/降格前缀不辖)。
_LOCK_EVENT_PREFIXES: tuple[str, ...] = ('lock:', 'forced_lock:',
                                         'handoff_lock:')


def bump_lock_gen_feasibility_obs(_ms: StrategyState,
                                  state: GameState,
                                  ist: IntentionState,
                                  pre_last_event: str) -> None:
    """面③出辖观察件计数(纯观测零行为,只写计数不改任何判定/发射)。

    三键:
    - ``..._lock_open_total``:锁开事件分母(信号锁/强锁/移交锁全计,
      由 last_event 转移入 ``_LOCK_EVENT_PREFIXES`` 判定);
    - ``..._lock_open_lowband``:分子——锁开帧在 λ 低血带(带判定 =
      ``hp_decision_trusted`` ∧ ``HP_BAND_NEAR_DEATH`` 血带结构锚单一源,
      禁字面量第二份;引血带键 = 合法概率路由——自检:观察分键的带
      判定不做任何行为分支)。「低血带新开 lock 开启率」
      由读端按两键比值派生,禁把率写进计数(只记不判);
    - ``..._boss_neardeath_p1|p2``:boss 节点濒死帧死区面计数(R1 存疑-1
      兑付:λ 表濒死 boss 格全禁/空 ⇒ lock 生成可行性门在 boss 窗濒死帧
      行为化即恒闭,死区人口分授权域申报不留白;P1/P2 授权域不同禁混键;
      boss token 词表与 discipline.plane_last_battle 同款)。

    辖域:随状态机贵段同频(每 game-round 恰一次);降格终局吸收态帧
    (状态机短路)不计。第三测量「切阵后 N 轮内亡率」(771014 型 =
    p2 濒死带 ∧ 新开 lock ∧ ≤2 轮内 hp0)不在本载体:策略层结构性不可见
    hp0(hp0 即局终无后续决策帧),归档案层
    离线派生(decisions 锁事件 × rounds hp 轨迹 join),申报义务在案。
    (终态契约 §2.5 impl 桶:计数宿主 = 显式 ``_ms`` 形参。)
    """
    if ist.demoted_endgame:
        return   # 降格终局吸收态:状态机短路帧不计(与意向帧计数同拍缺席)
    counters = getattr(_ms, 'cw4_counters', None)
    if not isinstance(counters, dict):
        return
    from sr_od.application.currency_war.kernel.cw_discipline_rules import (
        hp_decision_trusted,
    )
    from sr_od.application.currency_war.strategies.impl.mandate_v1.statefn.lambda_death import (
        HP_BAND_NEAR_DEATH,
    )
    from sr_od.application.currency_war.strategies.impl.mandate_v1.statefn.predicates import (
        p1_blood_floor,
        p2_blood_floor,
    )
    # 双形态归一退役(装配源换源收口):调用面全为容器直喂
    #(商店线 W6 波4 已切;备战线随 PrepObservation.state 槽退役改容器
    # 单例,同函数),帧兼容支随消点删除,入参即容器。
    if ist.last_event != pre_last_event \
            and ist.last_event.startswith(_LOCK_EVENT_PREFIXES):
        _k_total = LOCK_GEN_FEASIBILITY_OBS_PREFIX + 'lock_open_total'
        counters[_k_total] = counters.get(_k_total, 0) + 1
        # hp 决策可信位读口(统一 state 迁移波 2,hp施门下沉kernel政策层
        # 设计 §2.3)。商店线容器直喂时该位按容器真实 source 判
        #(原桥视图恒 True 失真窗随直喂消亡);本件纯观测零行为。
        _gs = state
        hp = _gs.hp.value
        if hp is not None and hp_decision_trusted(_gs) \
                and hp <= HP_BAND_NEAR_DEATH:
            _k_low = LOCK_GEN_FEASIBILITY_OBS_PREFIX + 'lock_open_lowband'
            counters[_k_low] = counters.get(_k_low, 0) + 1
    from sr_od.application.currency_war.kernel.cw_game_state import (
        node_kind_of,
    )
    # node 单一源 = gs 推导(终态契约 §A′:session 识别优先源退役,同
    # cw_discipline_rules 重锚口径)。
    node = node_kind_of(state) or ''
    if node == 'boss':
        if p1_blood_floor(state):
            _k_dz = LOCK_GEN_FEASIBILITY_OBS_PREFIX + 'boss_neardeath_p1'
        elif p2_blood_floor(state):
            _k_dz = LOCK_GEN_FEASIBILITY_OBS_PREFIX + 'boss_neardeath_p2'
        else:
            return   # 域外帧不入键(hp 缺读/带外帧防污染死区读数)
        counters[_k_dz] = counters.get(_k_dz, 0) + 1


class CwFlowStrategy(CwStrategy[StrategyState]):
    """主流程驱动核(生命周期 + 战略层意向 + pick 族 + 备战主流程栈)。

    泛型绑定(设计正本 §1/§8.5/§8.6-6,迁移批次三):本核即 mandate_v1
    流程核,``_TState`` 在此绑定为本实现的私有状态类型 StrategyState
    (基类 ``create_state`` 返回类型随之收窄)——框架基类仍只以泛型参数
    携带,零感知字段;kernel/one_dragon 零 import 本类型(布局锁辖)。

    行为锚见各方法 docstring 与 sim 契约锁。
    """

    STRATEGY_ID: str = ''            # 中间辅助 ABC,不注册(_abstract=True)
    STRATEGY_NAME: str = '主流程驱动核(内部基类)'
    _abstract: bool = True

    def __init__(self, gs, config, registry: DecisionV2Registry | None = None):
        """终态契约 §2.1 构造注入(gs/config 归基类);registry 可注入
        (A/B:两套注册表各跑一臂);缺省=标定版。"""
        super().__init__(gs, config)
        self.registry = registry or DEFAULT_REGISTRY

    # ===== 生命周期(终态契约 §2.1:状态 = 实例属性,构造即冷建)=====

    def _create_state(self) -> StrategyState:
        """策略器状态对象工厂钩子实现(session.md §3.1/§5.1;ADR-0563 决策-2)。

        每局冷建 StrategyState(本核即 mandate_v1 流程核;sim 初始相位注入
        经 ensure_strategy_state 构造入口,不经本钩子)。live 初值
        v3_phase='FORM'(ADR-0583:原 on_match_start 的唯一非零缺省随
        生命周期收编迁入冷建口)。
        """
        st = StrategyState()
        st.v3_phase = 'FORM'
        return st

    # ===== 镜像族观察写者(mandate_v1 单臂)=====

    def write_shop_mirrors(self, state: GameState,
                           _ms: StrategyState) -> None:
        """逐帧写 ``v3_b_t`` 板面目标线承重计数(纯遥测观测面)。

        口径 = B_t(件级单一源 ``cw_deploy_logic.
        board_target_line_weight``:deployed 中全羁绊 ∩
        SYSTEM_LINE_FACTIONS 非空件数,希儿本人单卡计入;bench 囤件
        不计入)。选 B_t 替代的依据:旧 ``v3_form_score``(min(2,
        engines+0.3×frac)/2 封顶连续量)在决策关键帧(boss 前/终局)
        恒常数 1.0 零方差、预测力为零;B_t 全样本有方差且是唯一
        p<0.001 显著代理(判读边界:预测力集中于 boss 战存活深度,
        对伤害差/终局 hp 仅弱正)。

        边界:本方法写 ``v3_b_t`` 与 ``v3_form_ok`` 两个观测键——旧
        ``v3_form_score`` 随本口径替换退役(历史账本只读,不再有写者)。
        ``v3_form_ok`` 写端已从退役 v2 相位机接回板面现读(死镜像处置批
        form_ok 死镜像处置:旧写端在 mandate_v1 下无写者恒 False,与
        发射判据核 armed 现读对账必然全量不一致——判读单一源 =
        第三十四局前后判读定谳);判据单一源 =
        ``cw_launch_admission.readiness_form_ok``(与发射 armed 同式,
        零第二实现)。``v3_phase`` 维持无写端退役缺省 ''(相位机已亡,
        无现读语义可接)。``v3_mirror_key`` 轮键戳照常盖章(键语义 =
        「本轮已写」,sim 引擎缺写守卫据此不重复触发)。纯遥测恢复:
        两字段不进任何判据(ADR-0353「form_score 降级纯遥测观测,不进
        判据」口径由 B_t 延续),写者本身零行为面。
        已知边界(如实声明):生产侧商店观察帧若 board 未播种,
        form_progress 现读恒 False——该帧族的 form_ok 读数是「观察帧
        board 口径」,与部署放行判定「轮入口全量 state 口径」存在帧差,判读
        时以 sim 账本(全量 state)为准。
        (终态契约 §2.5 impl 桶:状态宿主 = 显式 ``_ms`` 形参。)
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
        # readiness_form_ok,与发射 armed 同式)
        from sr_od.application.currency_war.kernel.cw_game_state import (
            plane_of as _plane_of,
        )
        from sr_od.application.currency_war.kernel.cw_game_state import (
            round_num_of as _round_num_of,
        )
        _ms.v3_form_ok = readiness_form_ok(
            state, getattr(_ms, 'target_comp', None))
        _ms.v3_mirror_key = (_plane_of(state), _round_num_of(state))

    # ===== 方向节拍内化(ADR-0583;原战略层 update_target 收编为策略器私有
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
        """方向重估全程(full 类帧入口;ADR-0583 §3.1)。

        键守卫贵段:``update_intention`` 状态机驱动 + 候选线评分遥测供数,
        每 game-round 恰一次(幂等键 = ``(plane, round_num)``,持有者 =
        ``StrategyState.v3_intention_key``,与 kernel ``drive_intention`` 纵深
        防御守卫同键面);便宜段 = 派生视图刷新,每次 full 帧入口一次。
        逐字平移自原 ``update_target``(行为锚:段级重入只刷新派生视图,
        不重复驱动锁线/撤销计数)。
        (终态契约 §2.5 impl 桶:策略器状态 = 显式 ``_ms`` 形参
        (即 self.state),state_of(session) 间接读退役。)
        """
        ist = self._ensure_intention(_ms)
        key = (plane_of(state), round_num_of(state))
        if _ms.v3_intention_key != key:
            _ms.v3_intention_key = key
            # ADR-0366:session 透传(plane_remaining_nodes 读本位面轮数真值);
            # registry 透传(C4 存活轮数门在 v2 换线通道的判据注入,A/B 臂
            # 经构造参替换 registry 即可达;cw_intention 缺省 None=缺省表)
            _lg_pre_event = ist.last_event
            update_intention(state, ist, None,
                             st=_ms, registry=self.registry)
            # 面③出辖观察件(锁生成可行性;纯观测零行为,载体与辖域声明
            # 见 bump_lock_gen_feasibility_obs docstring)——随状态机贵段
            # 同频,每 game-round 恰一次。
            bump_lock_gen_feasibility_obs(_ms, state, ist, _lg_pre_event)
        self._refresh_direction_views(state, _ms)

    def _refresh_direction_views(self, state: GameState,
                                 _ms: StrategyState) -> None:
        """派生视图刷新(便宜段;view 类帧入口只走本段,不触状态机——
        ADR-0583 §3.2)。原 ``update_target`` 无守卫段逐字平移:get_comp
        解析 + P1 配方对物化 + ``target_comp``/``v3_core_names`` 写入 +
        意向事件日志。(状态宿主 = 显式 ``_ms`` 形参,同上。)"""
        ist = self._ensure_intention(_ms)
        comp = get_comp(ist.locked_comp) if ist.locked_comp else None
        # `w578_target_comp_wire/`:P1 配方锁帧物化——ADR-0357 后 locked_comp 在配方锁局恒空,
        # state_of(session).target_comp 恒 None → 部署选人/评分管线/投资装备钩子等
        # 既有 target 消费者全盲(实机断链:引擎件躺 bench、散脸占板)。
        # 把已锁配方对物化为伪 comp(单一口径=cw_intention.pair_target_comp
        # docstring);①锁局 locked_comp 优先,本分支不辖;P2+/空对不物化
        # (不越 ADR-0357 辖域)。
        _plane_v = (plane_of(state) if isinstance(state, GameState)
                    else int(getattr(state, 'plane', 1) or 1))
        if comp is None and _plane_v == 1:
            # P1 目标不空窗(经济冻结批):配方对退场帧(p1_pair=() 空窗)
            # 不落 None——按 p1_early_pair 方向物化(单一源=
            # cw_intention.p1_early_pair;ADR-0372 买入门同款读法:空窗期
            # 同样有方向,不该因为不够锁而没方向;实机局
            # g_20260904_042657 p1r7-r9 经济冻结根)。旧形态 None →
            # 消费者(部署/评分/准备域引擎)全盲,0 买 0 刷。
            # **冻结语义衔接(ADR-0616 §2.2/§3.3 裁决①)**:F=True 帧
            # update_intention 已把 p1_pair 钉在 frozen_pair(重派生抑制),
            # 本段首选取 ist.p1_pair 即物化冻结方向,冻结期方向零漂移;
            # 空窗帧的 early 面已并批在任纪律(同一夺席算子作用于无门槛
            # 合格集,cw_intention.p1_early_pair 内聚,裁决①)
            # ——本段只消费产出,不复制派生。P1 外不辖(维持旧辖域:
            # P2+ 终局线走 locked_comp / 强制 assignment 通道)。
            pair = tuple(getattr(ist, 'p1_pair', ()) or ()) \
                or p1_early_pair(state, ist)
            if pair:
                comp = pair_target_comp(pair)
        _ms.target_comp = comp
        hoard = hoard_target_set(state, ist)
        _ms.v3_core_names = set(comp.core_chars) if comp else set()
        if ist.last_event and ist.last_event not in (
                _ms.v3_last_intention_event,):
            log.info('[cw][d2] 意向 %s mode=%s(%s)',
                     ist.phase, hoard.mode, ist.last_event)
        _ms.v3_last_intention_event = ist.last_event

    # ===== 决策入口统一内务:黑板帧代次消费(ADR-0583 §3.2/§3.4)=====

    def _consume_prep_direction_frame(self) -> None:
        """备战黑板帧代次消费(备战入口与 pick 族入口共用;ADR-0583 §3.2 触发面)。

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
        """商店黑板帧代次消费(decide_shop_action 入口;ADR-0583 §3.3-②)。

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

    # ===== pick 族(事件/选卡决策;判据单源 = kernel cw_events/cw_comps)=====
    # 终态契约 §2.1/§2.2:入口零参(候选 = gs payload 槽;离屏 None =
    # 观察层失约抛错,details §2.1 三分语义),输出 = 单一 CwAction——
    # 选卡 = per-screen 子类型,刷新建议 = 三刷新动作(与选卡互斥单发,
    # kernel 纯函数返回值由入口包装转动作,判据零触碰)。

    #: invest 刷新建议同帧去重键(StrategyState.scratch 键,局级生命周期)。
    _INVEST_ADVICE_MEMO_KEY = 'cw4_flow_invest_advice_key'

    def _require_slot_options(self, slot: object, slot_name: str) -> list:
        """payload 槽候选读口(黑板契约:进决策时 None = 观察层失约抛错,
        禁静默按空候选决策;details §2.1)。"""
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
        P1 两 kind 同一实现(委托 ``decide_event``)。
        ADR-0597(用户裁定 2026-09-08「投资选卡优先经济、然后是终局阵容,
        不为过渡阵容服务」):对齐源 = D* 预期终局方向——本入口从意向状态解析
        D*① 三参(locked_comp/demoted_endgame/evicted 同源于 ist)传 kernel,
        D*② 由 decide_event 内直算 detect_signals(单帧单读,§5.4);旧
        ``target_comp`` 对 invest kind 停止消费(P1 期它是过渡配方对物化的
        伪 comp,辖域错位;supply/encounter 等 pick 族消费面不变)。
        ADR-0209(接线 1/6):选卡结果喂 CommitSignals(策略 2.0/环境 1.0 权重;
        affinity 表把所选卡映射到 comp 分贡献)——**纯遥测保留,决策面零消费**
        (投资源不参与证明自身的反自馈检查现状即合规 = D*② ①层排除
        承载,ADR-0597 §5.3)。

        输出包装(终态契约 §2.2 刷新建议动作化):kernel refresh_slots 非空
        → ``CwActionRefreshInvestCardsParam(slots)``;否则 ``pick_param_cls(idx)``。三闸点击链
        留 handler——闸全败帧 handler 同访问再调本入口取选卡:同帧去重
        (scratch 键 = (kind, 候选元组))保证「建议帧首调发建议、紧随重调
        落选卡后键清」——重入访问(新候选/同候选)恢复首调语义,等价旧
        CwActionPickEventParam 单返回「idx + refresh_slots 并载、闸败回退选卡」行为。
        """
        options = list(self._require_slot_options(slot, slot_name))
        # 入口内务(ADR-0583 §3.2:pick 入口入触发面;消费最近一次备战黑板帧)
        self._consume_prep_direction_frame()
        _ist = self._ensure_intention(self.state)
        pick = cw_events.decide_event(
            options, self.config, self.gs,
            locked_comp=_ist.locked_comp,
            demoted_endgame=_ist.demoted_endgame,
            evicted=frozenset(_ist.evicted),
        )
        # 信号喂入:所选卡对各线的 affinity → comp 分贡献
        try:
            from sr_od.application.currency_war.kernel.cw_comps import augment_affinity
            src = 'invest_strategy' if kind == 'strategy' else 'invest_env'
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
                _cs.add(src, scores)
        except Exception:   # noqa: BLE001  信号喂入 best-effort
            pass
        memo_key = (kind, tuple(options))
        if pick.refresh_slots:
            if self.state.scratch.get(self._INVEST_ADVICE_MEMO_KEY) == memo_key:
                # 同帧重调(handler 三闸全败回退)= 建议已发,落选卡并清键
                #(键清 = 下一访问恢复首调建议语义)。
                self.state.scratch.pop(self._INVEST_ADVICE_MEMO_KEY, None)
            else:
                self.state.scratch[self._INVEST_ADVICE_MEMO_KEY] = memo_key
                return CwActionRefreshInvestCardsParam(slots=tuple(pick.refresh_slots),
                                          reason=pick.reason)
        return pick_param_cls(idx=pick.option_idx, reason=pick.reason)

    def decide_supply(self) -> CwActionPickSupplyParam | CwActionRefreshSupplyParam:
        """补给选装备/出钻(终态零参口;候选 = ``gs.supply`` payload)。
        刷新闸输入源 = ``gs.supply_refresh_left`` 剩余语义观察真值(details
        §2.3;剩余 ≤0 或 None = 已刷尽/未观察 → refresh_used=True,kernel
        按原评分直接选卡)。"""
        options = self._require_slot_options(self.gs.supply,
                                             'supply').options
        _left = self.gs.supply_refresh_left.value
        refresh_used = not (_left is not None and int(_left) > 0)
        self._consume_prep_direction_frame()   # ADR-0583 入口内务
        pick = cw_events.decide_supply(options, self.gs,
                                       self.state.target_comp, self.config,
                                       refresh_used)
        if pick.refresh:
            return CwActionRefreshSupplyParam(reason=pick.reason)
        return CwActionPickSupplyParam(idx=pick.idx, reason=pick.reason)

    def decide_encounter(self) -> CwActionPickEncounterParam | CwActionRefreshNodeOptionsParam:
        """遭遇难度/词缀避开(终态零参口;候选 = ``gs.encounter`` payload)。
        刷新闸输入源 = ``gs.encounter_refresh_left`` 剩余语义观察真值(用户
        裁定 2026-09-21,全域规范 = op-layer.md §1.4;剩余 ≤0 或 None =
        已刷尽/未观察 → refresh_used=True,kernel 按原评分直接选卡)。"""
        options = self._require_slot_options(self.gs.encounter,
                                             'encounter').options
        _left = self.gs.encounter_refresh_left.value
        refresh_used = not (_left is not None and int(_left) > 0)
        self._consume_prep_direction_frame()   # ADR-0583 入口内务
        pick = cw_events.decide_encounter(options, self.gs,
                                          self.state.target_comp, self.config,
                                          refresh_used=refresh_used)
        if pick.refresh:
            return CwActionRefreshNodeOptionsParam(reason=pick.reason)
        return CwActionPickEncounterParam(idx=pick.idx, reason=pick.reason)

    def decide_megastar(self) -> CwActionPickMegastarParam:
        """巨星选候选(终态零参口;候选 = 容器 ``megastar_opts``,值域 =
        标准化门保证的规范名,op-layer.md §1.1):委托
        ``cw_comps.select_megastar`` 拿角色名 → 名在 options 命中该 idx。
        非空候选恒命中(``select_megastar`` 选择序 + naive 层保证),候选
        空不可达(画面 op 守卫 fail 零盲发),本函数无缺省支。"""
        options = self._require_slot_options(self.gs.megastar_opts,
                                             'megastar_opts')
        self._consume_prep_direction_frame()   # ADR-0583 入口内务
        available = [o.char_id for o in options if o.char_id]
        chosen_name = cw_comps.select_megastar(self.gs, self.state.target_comp, available)
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
        self._consume_prep_direction_frame()   # ADR-0583 入口内务
        wants: list[str] = list(getattr(self.config, 'character_build_around', []) or [])
        if self.state.target_comp is not None:
            wants += list(self.state.target_comp.core_chars)
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
        self._consume_prep_direction_frame()   # ADR-0583 入口内务
        pick = cw_events.decide_planner(options, self.gs, self.state.target_comp)
        return CwActionPickPlannerParam(idx=pick.idx, reason=pick.reason)

    def decide_star_tome(self) -> CwActionPickStarTomeParam:
        """星徽秘典四选一(终态零参口;候选 = ``gs.star_tome_opts``;r104 接入
        策略模块;原 loop 内联 board 匹配迁此)。

        打分:①target_comp.all_factions 命中(终局线需要的阵营星徽 = +40);
        ②board 已有该阵营(板上已有=边际价值高,board 计数 ×8);
        ③当前配方框架阵营命中(双轨期过渡配方需要,+15)。无命中 fallback idx=0。"""
        options = self._require_slot_options(self.gs.star_tome_opts,
                                             'star_tome_opts')
        self._consume_prep_direction_frame()   # ADR-0583 入口内务
        if not options:
            return CwActionPickStarTomeParam(idx=0)
        fw = getattr(self.state, 'transition_framework', '')
        _fw_facs: set[str] = set()
        if fw:
            from sr_od.application.currency_war.knowledge.cw_line_facts import (
                FRAMEWORK_FACTIONS,
            )
            _fw_facs = set(FRAMEWORK_FACTIONS.get(fw, ()) or ())
        _tgt_facs: set[str] = set()
        if self.state.target_comp is not None:
            _tgt_facs = set(self.state.target_comp.all_factions or [])
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
        """祈愿试炼选卡(终态零参口;候选 = ``gs.wish_trial_opts``;r104 接入
        策略模块;原固定第1张)。

        options = 各卡 objective 文字(OCR)。打分:①金币类(直接经济,阵容无关
        稳妥)+25;②target/框架阵营相关词命中 +20;③「刷新/购买」类操作向
        (与 DP 攒息协同)+10;无信息 fallback idx=0。"""
        options = self._require_slot_options(self.gs.wish_trial_opts,
                                             'wish_trial_opts')
        self._consume_prep_direction_frame()   # ADR-0583 入口内务
        if not options:
            return CwActionPickWishTrialParam(idx=0)
        _tgt_facs: set[str] = set()
        if self.state.target_comp is not None:
            _tgt_facs = set(self.state.target_comp.all_factions or [])
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
        self._consume_prep_direction_frame()   # ADR-0583 入口内务
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
        # 终态契约 §B:spare 库存打分源 = gs.equips(镜像退役)。
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

    # ===== 契约扩员 12→15 三入口(普查迁移批 2;F-overlay-01/02/03 判据
    # ===== 收编 kernel,本壳零打分实现,委托同构 decide_box_card 先例)=====

    def decide_fortune(self) -> CwActionPickFortuneParam:
        """命运卜者强化三选一(终态零参口;候选 = ``gs.fortune_opts``
        OCR 卡文;判据单一源 = kernel ``decide_fortune`` 战力关键词权重
        argmax,无匹配缺省首卡,handler 侧越界防御同落首卡)。"""
        texts = list(self._require_slot_options(self.gs.fortune_opts,
                                                'fortune_opts'))
        self._consume_prep_direction_frame()   # ADR-0583 入口内务
        return CwActionPickFortuneParam(idx=cw_events.decide_fortune(texts))

    def decide_expert_invite(self) -> CwActionPickExpertInviteParam:
        """专家邀请函选卡(终态零参口;候选 = ``gs.expert_invite`` 弹窗
        载体(卡羁绊解析 + 板面羁绊计数,写端 = CwScreenExpertInvite);
        判据单一源 = kernel ``choose_expert_index`` 三级语义原样(在场
        浓度版),idx = -1 表现金为王。

        行为分叉申报:kernel 判据与 13_pick_family.md E9 在案规格(目标线
        成员优先 → 池浓度)分叉,已挂账独立行为变更(迁移批 2 报告),本
        入口保持实码行为、不擅自切规格。"""
        payload = self._require_slot_options(self.gs.expert_invite,
                                             'expert_invite')
        self._consume_prep_direction_frame()   # ADR-0583 入口内务
        return CwActionPickExpertInviteParam(idx=cw_events.choose_expert_index(
            list(payload.card_bonds), dict(payload.board)))

    def decide_equip_pick(self) -> CwActionPickEquipParam:
        """选择装备三选一(终态零参口;候选 = ``gs.equip_pick_opts``
        OCR 卡名带;判据单一源 = kernel ``decide_equip_overlay_pick``,
        key_fit 子串 +100 / 泛用关键词 +1.0,并列取首卡)。

        locked_comp 意向读随判据迁策略侧(终态契约 §2.5 参数注入桶):
        本入口自 ``self.state`` 取值注入 kernel,handler 零意向读。"""
        texts = list(self._require_slot_options(self.gs.equip_pick_opts,
                                                'equip_pick_opts'))
        self._consume_prep_direction_frame()   # ADR-0583 入口内务
        _ist = self._ensure_intention(self.state)
        return CwActionPickEquipParam(idx=cw_equip_value.decide_equip_overlay_pick(
            texts, locked_comp=_ist.locked_comp))

    def decide_shop_action(self) -> Action:
        """商店单动作决策接口(ADR-0517 决策 1/2/5;ADR-0583 升格入契约面;
        终态零参口 §2.1:决策输入一律 self.gs/self.state/self.config)。

        输入 = gs 容器(黑板契约容器化,设计件《商店黑板容器化方案》
        §2.2-1:入口观察/单动作逻辑态直写/sim 引擎写);输出 = **恰一个
        动作**,全函数永不 None——「无动作可做」由 ``CwActionCloseShopParam`` 恒可用
        终结表达(决策 5/6)。决策本体 = ``mandate_v1/shop.
        decide_shop_action``(选择序 = 决策本体候选扫描序,逐帧恰取一个
        动作)。执行侧单动作循环逐帧调用本接口;sim/兼容路径走
        :meth:`decide_shop_screen` 驱动器(同核循环化)。
        观察帧缺失 = 观察层失约,抛错(禁静默按空态决策)。
        入口内务 = 帧代次消费(:meth:`_consume_shop_direction_frame`;
        方向刷新在决策读视图之前完成,ADR-0583 内化锚)。
        受限会话自限(分层依据 = flow/README.md §1 决策控制分层铁律):
        决策本体产出唯一提案后,受限会话活跃帧(armed ∧ 金超息线
        派生标记,每帧现算 = bridge.launch_restricted_session_active)经
        kernel ``launch_arbitration_gate`` 谓词检(与 flow 闸同源同参,零
        判定数学复制)——拒 = 决策改发 ``CwActionCloseShopParam``(消费
        终止非改试次优,金出口族红线 5),受阻分键 ``launch_arbitrage_
        gate_blocked`` 落策略器状态 cw4_counters;非受限会话帧现行为逐位
        不变。生产单动作循环与 sim/replay 驱动器同经本口,两面同源自限
        (kernel 模块头「两面共用判定核」拓扑)。"""
        from sr_od.application.currency_war.strategies.impl.mandate_v1 import (
            shop,
        )
        # 决策入口容器契约(W6 波 4,设计件《商店黑板容器化方案》§2.2-1):
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
        # 未观察门(观察态落容器字段,策略消费只走 game state):tracked
        # 主账未按屏幕真值锚定(接管/重置/账失效事件后,备战环 heavy 观察
        # 尚未置位)时商店决策的关键输入(席面)不可信——返回恒可用终结
        # CwActionCloseShopParam 交商店画面 op 执行收店,外循环全分支重判自然落回备战节点,heavy
        # 观察完成锚定后再进店;店内不做任何原地重建(读屏重建出口已退役)。
        # 判定单一源 = kernel cw_game_state.tracked_unobserved;跳过事件
        # 留痕与连续跳过熔断在执行侧商店画面 op 的 CwActionCloseShopParam 出口。
        from sr_od.application.currency_war.kernel.cw_game_state import (
            tracked_unobserved,
        )
        if tracked_unobserved(self.gs):
            log.info('[cw][shop] tracked 未观察(待备战 heavy 观察锚定)'
                     '→ CwActionCloseShopParam 交回外循环重判')
            return CwActionCloseShopParam()
        # 入口刷新先于镜像/决策(方向视图 = 本帧语境;ADR-0583 内化锚)
        self._consume_shop_direction_frame()
        # v3_b_t 逐帧镜像写者(纯遥测,零行为面;口径与边界见
        # write_shop_mirrors docstring。旧 v3_form_score 已随口径
        # 替换退役,历史账本只读)。写位 = 决策核入口 = 生产单
        # 动作循环与 sim decide_shop_screen 驱动器共同必经点。
        self.write_shop_mirrors(gs, self.state)
        # 决策本体宿主 = gs(state_of(gs) → 同源接线策略器状态;
        # game_state_of(gs) 本体直通——经 self.state 传递会让 kernel 侧
        # game_state_of 解析到一次性空容器,禁)。
        action = shop.decide_shop_action(gs, gs, self.config,
                                         registry=self.registry)
        # 发射帧受限消费·策略侧自限(详设 §2.10;flow 闸退役前的先行落地
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
        # run-1 两写点按动作互斥不自增;run-2 闸退役后本写点为唯一写点,
        # 分键宿主随拒拍落 strategy_state,详设 §2.10)。
        _ct = getattr(self.state, 'cw4_counters', None)
        if isinstance(_ct, dict):
            _ct[KEY_GATE_BLOCKS] = _ct.get(KEY_GATE_BLOCKS, 0) + 1
        return CwActionCloseShopParam()

    def decide_shop_screen(self, session: StrategySession | None = None,
                           config: CurrencyWarConfig | None = None
                           ) -> list[Action]:
        """商店序列兼容驱动器(缺省实现;ADR-0583 降格出 ABC;形参 = 兼容宿主
        (sim/回放/序列锁调用面照旧传),决策已零参化,本体不消费)。

        sim/回放/既有序列锁消费(生产执行侧走单动作循环):逐帧调
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
        # 驱动器同路(W6 波 4,设计件 §2.2-3):决策读容器单例 + 期望态
        # 推进 = 逐动作直调上报函数(动作 op 重组批④:快照三件组已内聚
        # 买牌上报,双抄写段退役);逐域期望态由投影直锁钉住
        # (test_cw_shop_projection_logic,锁 M1)。帧缺失 = 容器离屏 =
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
            """引擎入口委托分支串(design.md §2;离线驱动无落地门,k 判据
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
