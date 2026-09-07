"""货币战争 主流程驱动核(CwFlowStrategy;自 decision_v2/strategy.py 迁入,
策略统一迁移批——底稿 MAP ⓪ A1「迁移白名单」)。

辖域 = mandate_v1 未覆写的域实现:

- 生命周期收编后的唯一冷建口 create_session(策略器状态工厂接线 + live
  初值 v3_phase='FORM' 一并在此落位;旧 on_match_start/on_match_end 已随
  ADR-0583 删除)与策略器状态工厂 create_state;
- 方向节拍内化(:meth:`_refresh_direction`;ADR-0583:方向重估从流程侧
  ops 直调收进策略器,触发信号 = 黑板帧刷新代次标注,键守卫贵段每
  game-round 恰一次 + 便宜派生视图段);
- 结算策略半惰性加工(:meth:`_drain_pending_round_outcomes`;旧
  on_round_end 拆两半——观察半归框架观察层即时直写,策略半经
  ``session.pending_round_outcomes`` 待加工槽在此 drain);
- pick 族(decide_invest/supply/encounter/megastar/partner/planner/
  star_tome/wish_trial/box_card);
- 商店序列兼容驱动器 decide_shop_screen 缺省实现(降格出 ABC,
  ADR-0583;sim/回放/序列锁消费,mandate 记账在其覆写)与商店单动作
  接口 decide_shop_action(ADR-0517,委托 mandate_v1/shop)。

**旧备战骨架已删(ADR-0517 迁移批,flow/screen_op.md §8.2 裁决)**:
_decide_prep_action_impl/_main_flow_step 相位机/_free_bench_step 腾席链/
_deploy_up_candidates/_bench_junk_idx/_pseudo_state/_fresh_state 及私有
helper(_is_boss_round/_cap_shortfall/_levelup_engine_ok)= 零生产调用死码
簇(测试直调不算;live 备战决策链 = cw_screen_prep → mandate_v1.bridge →
entry.emit 三遍编排);传递性死码 kernel/cw_deploy_seat(_should_deploy
族)与 session 暂存字段(prep_phase/prep_phase_retry/free_bench_gold_wait)
同批清除。

本类 ``_abstract=True``(中间辅助 ABC,StrategyManager 不注册;
decide_prep_screen 保持 abstract——具现 =
``strategies.impl.mandate_v1.bridge.MandateV1Strategy``,生产注册壳 =
``strategies/mandate_v1_strategy.py``)。
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel import cw_comps, cw_events
from sr_od.application.currency_war.kernel.cw_comps import get_comp
from sr_od.application.currency_war.kernel.cw_discipline_rules import (
    BloodAlarmTracker,
)
from sr_od.application.currency_war.kernel.cw_events import (
    EncounterOption,
    EncounterPick,
    MegastarOption,
    MegastarPick,
    PartnerOption,
    PartnerPick,
    PlannerOption,
    PlannerPick,
    SupplyOption,
    SupplyPick,
)
from sr_od.application.currency_war.kernel.cw_evolution import (
    rollback_weakest,
)
from sr_od.application.currency_war.kernel.cw_intention import (
    IntentionState,
    _v2_comps,
    _visible_chars,
    hoard_target_set,
    line_completion_feasibility,
    p1_early_pair,
    pair_target_comp,
    update_intention,
)
from sr_od.application.currency_war.kernel.cw_performance import (
    RoundOutcome,
)
from sr_od.application.currency_war.kernel.cw_plane_table import NODES_PER_PLANE
from sr_od.application.currency_war.kernel.cw_registry import (
    DEFAULT_REGISTRY,
    DecisionV2Registry,
)
from sr_od.application.currency_war.kernel.cw_state import (
    Action,
    GameState,
    PickEvent,
)
from sr_od.application.currency_war.strategies.impl.cw_strategy import (
    CwStrategy,
    StrategySession,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.mandate_state import (
    state_of,
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

#: 谷底回滚线(点6:转型中遭遇单场掉血 >15 → 回滚一件最弱替换位;
#: 与点4 报警线 20/30 分层并存——15 管转型期单场,20/30 管全局累计)
VALLEY_ROLLBACK_LOSS: int = 15


class CwFlowStrategy(CwStrategy):
    """主流程驱动核(生命周期 + 战略层意向 + pick 族 + 备战主流程栈)。

    方法体逐字平移自 ``decision_v2/strategy.py`` DecisionV2Strategy
    同名方法(出处见各方法 docstring;行为零变更由 sim 契约锁承载)。
    """

    STRATEGY_ID: str = ''            # 中间辅助 ABC,不注册(_abstract=True)
    STRATEGY_NAME: str = '主流程驱动核(内部基类)'
    _abstract: bool = True

    def __init__(self, registry: DecisionV2Registry | None = None):
        """registry 可注入(A/B:两套注册表各跑一臂);缺省=标定版。"""
        super().__init__()
        self.registry = registry or DEFAULT_REGISTRY

    # ===== 生命周期(ADR-0583 收编:唯一冷建口 + 结算策略半惰性加工)=====

    def _drain_pending_round_outcomes(self, session: StrategySession) -> None:
        """结算策略半惰性加工(ADR-0583 §2.5:旧 on_round_end 拆两半的策略半)。

        观察层(cw_screen_battle_wait 结算回路)在结算点即时直写观察字段
        全集(performance.record/last_streak/last_hp+置信门/last_hp_t)并把
        ``RoundOutcome`` 追加进 ``session.pending_round_outcomes``;本方法在
        **下一次决策入口**(备战/商店/pick 任意入口,经
        :meth:`_consume_prep_direction_frame`/:meth:`_consume_shop_direction_frame`
        统一先 drain)逐行执行策略器内部加工,处理即清槽——每行只加工一次,
        天然幂等,无需键守卫。

        逐行 = 旧 on_round_end(flow 历史版:156-192)原样搬运:
        掉血三臂喂入(BloodAlarmTracker)+ node_type 空值回落 + 谷底回滚登记
        + ``v3_prev_hp`` 更新。**零行为差依据**(ADR-0583 §2.5 归属表读端
        核查):``v3_alarm``/``v3_pending_rollback``/``v3_prev_hp`` 在 src 内
        零行为读端(掉血判据数据积累期;``VALLEY_ROLLBACK_LOSS`` 已裁定退役,
        本批只搬运不删除,删码归既定退役批)。

        state 基准申报:原 on_round_end 收到的 state = battle_wait 传入的空
        ``GameState()``(plane/round 回落与 t 计算实际取其缺省值);本方法无
        state 参,基准 = ``session.last_state``(缺省回落空态)。该差异落在
        上述零读端域内,无行为面;``t`` 数值因此更贴近真实节点序(原形态受
        调用面空态钉在 (plane-1)*9+1)。

        best-effort 语义与原调用面守卫一致(方向/结算加工失败不阻塞决策):
        单行异常留证后续行留槽下个入口重试(已处理行已出槽,不重复计数)。
        """
        pending = getattr(session, 'pending_round_outcomes', None)
        if not pending:
            return
        while pending:
            obs = pending.pop(0)
            try:
                self._process_settlement_strategy_half(session, obs)
            except Exception as e:   # noqa: BLE001  策略半加工失败不阻塞决策
                log.warning('[cw!][strategy] 结算加工异常(下个入口重试余量): %s', e)
                break

    def _process_settlement_strategy_half(self, session: StrategySession,
                                          obs: RoundOutcome) -> None:
        """单行结算策略半加工(:meth:`_drain_pending_round_outcomes` 的逐行体;
        独立成方法便于异常边界落在单行粒度)。"""
        from sr_od.application.currency_war.strategies.impl.mandate_v1.mandate_state import (
            state_of,
        )
        _ms = state_of(session)
        tracker = _ms.v3_alarm
        if tracker is None:
            tracker = _ms.v3_alarm = BloodAlarmTracker()
        hp_after = getattr(obs, 'hp_after', None)
        node_type = getattr(obs, 'node_type', None) or ''
        # N2 同源:obs.plane 权威(结算时位面可能已推进);state 基准申报见 drain docstring
        state = getattr(session, 'last_state', None) or GameState()
        plane = getattr(obs, 'plane', None) or state.plane
        if not node_type:
            # supply 失活治本(supply失活升级线 第6/7次复现):空 node_type 轮
            # 被 BloodAlarmTracker 战斗节点门整轮丢弃 → 掉血数据缺失、生死窗
            # 判读缺页。修法 = node_type 空值回落**对局档案装配轮行序**——
            # 档案(match_archive)按局归并轮次、轮行自带序,但其装配是局后
            # assemble_pending 产物,结算加工时点不可得 → 同一轮行序的
            # 局内单一源 = 位面节点台账(PlaneNodeLedger:按位面归并、轮行
            # 自带序;位面详情采集/投资环境重读两写点,15 号稿 §1 行 10
            # 「权威表」),按 (plane, round_num) 查同轮 node_type;查不到 =
            # 照旧空串(不猜)+ 分键留证。
            node_type = self._alarm_node_type_fallback(
                session, plane, getattr(obs, 'round_num', None)
                or state.round_num)
        t = (plane - 1) * NODES_PER_PLANE + state.round_num
        hp_before = _ms.v3_prev_hp
        if hp_before is not None and hp_after:
            tracker.record(node_type, hp_before, hp_after, t, plane=plane)
            # 点6 谷底回滚:转型中(上次替换名单非空)单场掉血 >15
            # → 回滚一件最弱替换位后放缓(显式动作下轮发)
            mem = _ms.v3_evolution
            if mem is not None and getattr(mem, 'last_deployed', None) \
                    and hp_before - hp_after > VALLEY_ROLLBACK_LOSS \
                    and _ms.v3_pending_rollback is None:
                act = rollback_weakest(state, mem)
                if act is not None:
                    _ms.v3_pending_rollback = act
                    log.info('[cw][d2] 谷底回滚登记(单场 -%d > %d)',
                             hp_before - hp_after, VALLEY_ROLLBACK_LOSS)
        _ms.v3_prev_hp = hp_after if hp_after else hp_before

    def _alarm_node_type_fallback(self, session, plane, round_num) -> str:
        """掉血报警 node_type 空值回落(→ 生产词汇表 token | 空串)。

        命中 = 台账该位次有非空类型 → 映射回生产词表喂
        BloodAlarmTracker(掉血数据恢复);未命中(表缺/越界/该位次 None)
        = 照旧空串不猜 + ``blood_alarm_node_type_fallback`` 分键留证
        (单一源 = kernel.cw_telemetry_exit 常量)。best-effort 不抛。"""
        token: str | None = None
        try:
            from sr_od.application.currency_war.kernel.cw_state import (
                ledger_node_type,
            )
            token = ledger_node_type(session, plane, round_num)
        except Exception:   # noqa: BLE001  台账缺失不阻塞结算喂入
            token = None
        # 词表单一源 = kernel.cw_state.NODE_TOKEN_TO_WORD(落地审 C1:自维护
        # 删减副本漏 elite 致精英轮掉血恢复失效,从源头消掉)。
        try:
            from sr_od.application.currency_war.kernel.cw_state import (
                NODE_TOKEN_TO_WORD,
            )
            nt = NODE_TOKEN_TO_WORD.get(str(token), '') if token else ''
        except Exception:   # noqa: BLE001
            nt = ''
        try:
            from sr_od.application.currency_war.kernel.cw_telemetry_exit import (
                DEFECT_KIND_BLOOD_ALARM_NODE_FALLBACK,
                record_defect,
            )
            record_defect(
                'blood_alarm', DEFECT_KIND_BLOOD_ALARM_NODE_FALLBACK,
                expected=f'node_type 非空(台账={token if token else "缺"})',
                observed=f'回落={nt if nt else "空串(照旧)"}',
                plane=int(plane or 0), round_num=int(round_num or 0),
                gap_large=False, auto_resolved=bool(nt),
                verdict=('台账命中-掉血数据恢复' if nt
                         else '台账未命中-照旧空串(不猜)+分键留证'),
                reader_source='on_round_end_node_type_fallback',
                note='supply 失活治本:空 node_type 轮掉血数据不丢')
        except Exception:   # noqa: BLE001  遥测 best-effort
            pass
        if nt:
            log.info('[cw][d2] node_type 空值回落:台账 %s(%s-%s)→「%s」'
                     '(掉血数据恢复)', token, plane, round_num, nt)
        return nt

    def create_state(self, config: CurrencyWarConfig) -> object:
        """策略器状态对象工厂(session.md §3.1/§5.1;ADR-0563 决策-2)。

        每局冷建 MandateState(本核即 mandate_v1 流程核,create_session
        唯一冷建口接线;sim 初始相位注入经 ensure_strategy_state 构造入口,
        不经本工厂)。**live 初值 v3_phase='FORM' 归 create_session**
        (ADR-0583:原 on_match_start 的唯一非零缺省随生命周期收编迁入
        冷建口;工厂本体保持缺省 '',直调工厂的 sim 注入桩面语义不变)。
        **config 契约:可忽略、可为 None**——sim 侧
        ``ensure_strategy_state`` 注入桩面调 ``factory(None)``,工厂实现
        禁依赖 config 取值;MandateState 无 config 依赖,恒冷建即安全。
        """
        from sr_od.application.currency_war.strategies.impl.mandate_v1.mandate_state import (
            MandateState,
        )
        return MandateState()

    def create_session(self, config) -> StrategySession:
        """空白 session(rng 留默认,由 run loop 按 ``config.strategy_seed`` 覆盖)。

        新局起点顺带复位布局未知态计数(落地审 C4:跨局残留会让新局开局
        ——level 未 observed/CV 高发不可判期——提前吃冻结)。
        **唯一冷建口(ADR-0583)**:策略器状态工厂接线 + live 初值
        ``v3_phase='FORM'`` 一并在此落位(旧 on_match_start 冷建与初值
        双写点收编;manager/sim/replay/direct 直调点全走本方法)。"""
        try:
            from sr_od.application.currency_war.kernel.cw_state import (
                reset_layout_unknown_state,
            )
            reset_layout_unknown_state()
        except Exception:   # noqa: BLE001  复位 best-effort,不阻 session 创建
            pass
        sess = StrategySession()
        # 策略器状态工厂接线(session.md §3.1/§5.1):create_session 即冷建
        # 当局 MandateState——状态生命周期与 session 同源(§3.4-1 统一构建口)。
        sess.strategy_state = self.create_state(config)
        # live 相位观测初值(ADR-0583:原 on_match_start 的唯一非零缺省;
        # 工厂产物保持缺省 ''——sim 直构 session 的旧读数保真,见 §2.3 拆分表)。
        from sr_od.application.currency_war.strategies.impl.mandate_v1.mandate_state import (
            MandateState,
        )
        _ms = sess.strategy_state
        if isinstance(_ms, MandateState):
            _ms.v3_phase = 'FORM'
        return sess

    # ===== 镜像族观察写者(mandate_v1 单臂)=====

    def write_shop_mirrors(self, state: GameState,
                           session: StrategySession) -> None:
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
        board 口径」,与发射门「轮入口全量 state 口径」存在帧差,判读
        时以 sim 账本(全量 state)为准。
        """
        from sr_od.application.currency_war.kernel.cw_deploy_logic import (
            board_target_line_weight,
        )
        from sr_od.application.currency_war.kernel.cw_launch_admission import (
            readiness_form_ok,
        )
        deployed = [d for d in
                    (getattr(state, 'deployed', None) or [])
                    if d is not None]
        if not deployed:
            # 实机落位补缺(g_20260906_021859/034515 两局全帧 0.0 实证):
            # 商店观察帧(state=shop_state_frame)只播种 bench
            # (cw_op_buy_cards 入口 tracked_bench_chars 播种段),
            # ``deployed`` 列表恒空 → B_t 恒 0。回退源 =
            # exec_state_of(session).tracked_deployed(执行记录槽位表,单元素带 char_id,
            # 与 assembly/cw_observation 同一消费源),空 = 板面真空的
            # 事实态,照写 0 不虚构。
            # exec_state_of(session).tracked_deployed(执行记录槽位表,单元素带 char_id,
            # 与 assembly/cw_observation 同一消费源),空 = 板面真空的
            # 事实态,照写 0 不虚构。(执行侧载体读点:kernel.cw_exec_state
            # 访问口——session.md §5.5)
            from sr_od.application.currency_war.kernel.cw_exec_state import (
                exec_state_of,
            )
            deployed = [d for d in
                        (getattr(exec_state_of(session), 'tracked_deployed',
                                 None) or [])
                        if d is not None]
        # 件级计数:名字列表保留重复件(同名多件各计 1,禁 frozenset 去重)
        dep_names = [(getattr(d, 'char_id', '') or '') for d in deployed]
        from sr_od.application.currency_war.strategies.impl.mandate_v1.mandate_state import (
            state_of,
        )
        _ms = state_of(session)
        _ms.v3_b_t = board_target_line_weight(dep_names)
        # form_ok 镜像现读写端(死镜像处置,见 docstring;判据单一源 =
        # readiness_form_ok,与发射 armed 同式)
        _ms.v3_form_ok = readiness_form_ok(
            state, getattr(state_of(session), 'target_comp', None))
        _ms.v3_mirror_key = (getattr(state, 'plane', 1) or 1,
                             getattr(state, 'round_num', 0) or 0)

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
                           session: StrategySession) -> None:
        """方向重估全程(full 类帧入口;ADR-0583 §3.1)。

        键守卫贵段:``update_intention`` 状态机驱动 + 候选线评分遥测供数,
        每 game-round 恰一次(幂等键 = ``(plane, round_num)``,持有者 =
        ``MandateState.v3_intention_key``,与 kernel ``drive_intention`` 纵深
        防御守卫同键面);便宜段 = 派生视图刷新,每次 full 帧入口一次。
        逐字平移自原 ``update_target``(行为锚:段级重入只刷新派生视图,
        不重复驱动锁线/撤销计数)。"""
        _ms = state_of(session)
        ist = self._ensure_intention(_ms)
        # 段级重入守卫:sim 决策循环每轮最多 8 段重入刷新,
        # 意向状态机的 miss 计数分母=轮——同轮重入只刷新派生视图
        # (hoard/target_comp),不重复驱动锁线/撤销计数。
        key = (state.plane, state.round_num)
        if _ms.v3_intention_key != key:
            _ms.v3_intention_key = key
            # ADR-0366:session 透传(plane_remaining_nodes 读本位面轮数真值);
            # registry 透传(C4 存活轮数门在 v2 换线通道的判据注入,A/B 臂
            # 经构造参替换 registry 即可达;cw_intention 缺省 None=缺省表)
            update_intention(state, ist, session, registry=self.registry)
            # 遥测供数(ADR-0579):候选线评分表落盘——选线时点的判断依据
            # (轮入口快照,非店开时刻值;_telemetry_ 前缀 = 披露面自带隔离,
            # 禁决策消费,守卫 = 全仓命中点计数锁)。纯遥测增量:唯一读点
            # 只进 record_decision(深度复盘候选评分可见性,诊断.md §6)。
            # (ADR-0583 §5.5-戊:本段与状态机同键面、同吃帧 state 的 hp——
            # 候选评分遥测列随驱动输入门同步移门,误读轮的分值差属申报面
            # 判读差异,非漂移。)
            _vis = _visible_chars(state)
            _ms._telemetry_last_candidate_scores = {
                c.name: round(line_completion_feasibility(
                    state, c, session, self.registry, _vis), 4)
                for c in _v2_comps()
                if c.name not in ist.evicted
                and state.plane not in (c.weak_planes or ())
            }
            _ms._telemetry_last_candidate_scores_round = state.round_num
            # (P1→P2 接口机制·①锁线 v2 后处理已随五开关定谳清理删除,
            # ADR-0487:W793 A/B 触发面全开火仍主判据双败。[23] 锚经
            # update_intention 信号驱动锁线,不受影响。)
        self._refresh_direction_views(state, session)

    def _refresh_direction_views(self, state: GameState,
                                 session: StrategySession) -> None:
        """派生视图刷新(便宜段;view 类帧入口只走本段,不触状态机——
        ADR-0583 §3.2)。原 ``update_target`` 无守卫段逐字平移:get_comp
        解析 + P1 配方对物化 + ``target_comp``/``v3_core_names`` 写入 +
        意向事件日志。"""
        _ms = state_of(session)
        ist = self._ensure_intention(_ms)
        comp = get_comp(ist.locked_comp) if ist.locked_comp else None
        # `w578_target_comp_wire/`:P1 配方锁帧物化——ADR-0357 后 locked_comp 在配方锁局恒空,
        # state_of(session).target_comp 恒 None → 部署选人/评分管线/投资装备钩子等
        # 既有 target 消费者全盲(实机断链:引擎件躺 bench、散脸占板)。
        # 把已锁配方对物化为伪 comp(单一口径=cw_intention.pair_target_comp
        # docstring);①锁局 locked_comp 优先,本分支不辖;P2+/空对不物化
        # (不越 ADR-0357 辖域)。
        if comp is None and state.plane == 1:
            # P1 目标不空窗(经济冻结批):配方对退场帧(支持度掉出锁门槛/
            # 断供驱逐重派生为空)不落 None——按 p1_early_pair 无门槛 top-2
            # 方向物化(单一源=cw_intention.p1_early_pair,ADR-0372 买入门
            # 同款读法:空窗期同样有方向,不该因为不够锁而没方向)。旧形态
            # None → 消费者(部署/评分/准备域引擎)全盲,0 买 0 刷经济冻结
            # (实机局 g_20260904_042657 p1r7-r9)。P1 外不辖(维持旧辖域:
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

    # ===== 决策入口统一内务:结算惰性 drain + 帧代次消费(ADR-0583 §3.2/§3.4)=====

    def _consume_prep_direction_frame(self, session: StrategySession) -> None:
        """备战黑板帧代次消费(备战入口与 pick 族入口共用;ADR-0583 §3.2 触发面)。

        帧 = full → :meth:`_refresh_direction` 全程(键新则状态机 + 评分遥测);
        帧 = view(破墙派生帧/finalize 买后暂存帧)→ 只刷派生视图;帧 = none
        → 只 drain 结算槽即返回。读后即复位 'none'(消费即清,防同帧重复刷新;
        复位 = 读协议半部,非新鲜度宣告——帧类写点收敛归流程观察段,§3.4/D6)。
        刷新失败不阻塞决策(沿用原 ops 侧守卫语义,日志哨兵 [cw!] 保持)。"""
        self._drain_pending_round_outcomes(session)
        cls = getattr(session, 'prep_frame_class', 'none')
        if cls not in ('full', 'view'):
            return
        session.prep_frame_class = 'none'
        frame = session.prep_obs_frame
        state = getattr(frame, 'state', None) if frame is not None else None
        try:
            if cls == 'full':
                self._refresh_direction(state or GameState(), session)
            else:
                self._refresh_direction_views(state or GameState(), session)
        except Exception as e:   # noqa: BLE001  方向刷新失败不阻塞决策(沿用旧向)
            log.warning('[cw!][strategy] 方向刷新异常(沿用旧方向): %s', e)

    def _consume_shop_direction_frame(self, session: StrategySession) -> None:
        """商店黑板帧代次消费(decide_shop_action 入口;ADR-0583 §3.3-②)。

        visit 首段 full 帧 → 刷新(键同只刷视图,视图源 = 商店入口帧 state);
        续段 none 帧 → 保持首段值(= 旧 ``_target_seeded``「仅首段重估」语义)。
        不捕获异常:与原 ops 侧 ``cw_op_buy_cards`` 首段直调的失败面一致
        (无守卫)。"""
        self._drain_pending_round_outcomes(session)
        cls = getattr(session, 'shop_frame_class', 'none')
        if cls not in ('full', 'view'):
            return
        session.shop_frame_class = 'none'
        state = session.shop_state_frame
        if cls == 'full':
            self._refresh_direction(state, session)
        else:
            self._refresh_direction_views(state, session)

    # ===== pick 族(事件/选卡决策;判据单源 = kernel cw_events/cw_comps)=====

    def decide_invest(self, kind: Literal["strategy", "env"], options: list[str],
                      state: GameState, session: StrategySession, config) -> PickEvent:
        """投资策略/投资环境 3 选 1。P1 两 kind 同一实现(委托 ``decide_event``);分表现 P2+ 议题。
        ``state.board`` 由调用方传空 stub(overlay 叠备战时 board 不可读,§11.7)。
        ADR-0134:strategy kind 传 state_of(session).target_comp(星徽套组/专属强化对齐 target = 成型加速,
        comp 匹配分压倒品质先验)。ADR-0144 修订:env kind 也传 —— 开局环境屏 comp 未定(None,
        行为同旧,阵营定向走 select_comp env_fit);**局中环境屏**(如 联席决策 2-6 节点)comp 已定,
        概念股/邀请/契约阵营匹配定序门(ENV_FACTION_MATCH_FLOOR,ADR-0524 定形:
        三档值=category 定序档位,禁读基数)生效。
        ADR-0209(接线 1/6):选卡结果喂 CommitSignals(策略 2.0/环境 1.0 权重;
        affinity 表把所选卡映射到 comp 分贡献)。"""
        # 入口内务(ADR-0583 §3.2:pick 入口入触发面;消费最近一次备战黑板帧)
        self._consume_prep_direction_frame(session)
        from sr_od.application.currency_war.strategies.impl.mandate_v1.mandate_state import (
            state_of,
        )
        _tgt = state_of(session).target_comp
        pick = cw_events.decide_event(options, config, state, target_comp=_tgt)
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
                _cs = state_of(session).commit_signals
                if _cs is None:
                    _cs = state_of(session).commit_signals = CommitSignals()
                _cs.add(src, scores)
        except Exception:   # noqa: BLE001  信号喂入 best-effort
            pass
        return pick

    def decide_supply(self, options: list[SupplyOption], state: GameState,
                      session: StrategySession, config, refresh_used: bool = False) -> SupplyPick:
        """补给选装备/出钻。⚠️ OCR 未就绪(P1 契约成员 + 默认委托,handler 不 rewire,随阶段5)。"""
        self._consume_prep_direction_frame(session)   # ADR-0583 入口内务
        return cw_events.decide_supply(options, state, state_of(session).target_comp, config, refresh_used)

    def decide_encounter(self, options: list[EncounterOption], state: GameState,
                         session: StrategySession, config, refresh_used: bool = False) -> EncounterPick:
        """遭遇难度/词缀避开。⚠️ 后 dormant(遭遇=普通战斗无选项 UI);纯逻辑+测试暂留。"""
        self._consume_prep_direction_frame(session)   # ADR-0583 入口内务
        return cw_events.decide_encounter(options, state, state_of(session).target_comp, config, refresh_used)

    def decide_megastar(self, options: list[MegastarOption], state: GameState,
                        session: StrategySession, config) -> MegastarPick:
        """巨星选候选:委托 ``cw_comps.select_megastar`` 拿角色名 → 名在 options 命中该 idx;否则 idx=0。
        ⚠️ OCR 未就绪(char_id 全空 → 匹配恒失败 → idx=0 = 今天盲点左候选,随阶段5)。
        (强化角色维度已随 megastar_enhance_enabled 开关族删除——旧方案
        清退批,清查报告 OLD_MIX_AUDIT §1.3;MegastarPick.enhance_char_id
        字段保留恒 None,兼容既有遥测/执行面读取。)"""
        self._consume_prep_direction_frame(session)   # ADR-0583 入口内务
        available = [o.char_id for o in options if o.char_id]
        chosen_name = cw_comps.select_megastar(state, state_of(session).target_comp, available)
        if chosen_name:
            for o in options:
                if o.char_id == chosen_name:
                    return MegastarPick(
                        idx=o.idx,
                        reason=f"select_megastar 命中 {chosen_name}")
        return MegastarPick(idx=0, reason="fallback 左候选(OCR 未就绪,char_id 空)")

    def decide_partner(self, options: list[PartnerOption], state: GameState,
                       session: StrategySession, config) -> PartnerPick:
        """选择伙伴:优先 ``config.character_build_around`` / ``target.core_chars`` 命中;否则 idx=0。
        ⚠️ OCR 未就绪(char_id 全空 → 命中恒失败 → idx=0 = 今天盲点 stage 立绘,随阶段5)。"""
        self._consume_prep_direction_frame(session)   # ADR-0583 入口内务
        wants: list[str] = list(getattr(config, 'character_build_around', []) or [])
        if state_of(session).target_comp is not None:
            wants += list(state_of(session).target_comp.core_chars)
        for o in options:
            if o.char_id and o.char_id in wants:
                return PartnerPick(idx=o.idx, reason=f"命中偏好/核心 {o.char_id}")
        return PartnerPick(idx=0, reason="fallback(OCR 未就绪,char_id 空)")

    def decide_planner(self, options: list[PlannerOption], state: GameState,
                       session: StrategySession, config) -> PlannerPick:
        """银狼策划事件(r104 用户定调:接入策略模块由它定;委托 cw_events.decide_planner)。

        升费卡打分含银狼线/在场判定(state.bench+deployed 的 char_id),
        state_of(session).target_comp 决定银狼线加成。"""
        self._consume_prep_direction_frame(session)   # ADR-0583 入口内务
        return cw_events.decide_planner(options, state, state_of(session).target_comp)

    def decide_star_tome(self, options: list[str], state: GameState,
                         session: StrategySession, config) -> int:
        """星徽秘典四选一(r104 接入策略模块;原 loop 内联 board 匹配迁此)。

        打分:①target_comp.all_factions 命中(终局线需要的阵营星徽 = +40);
        ②board 已有该阵营(板上已有=边际价值高,board 计数 ×8);
        ③当前配方框架阵营命中(双轨期过渡配方需要,+15)。无命中 fallback idx=0。
        返回 options 索引。"""
        self._consume_prep_direction_frame(session)   # ADR-0583 入口内务
        if not options:
            return 0
        fw = getattr(state_of(session), 'transition_framework', '')
        _fw_facs: set[str] = set()
        if fw:
            from sr_od.application.currency_war.kernel.cw_transition import (
                FRAMEWORK_FACTIONS,
            )
            _fw_facs = set(FRAMEWORK_FACTIONS.get(fw, ()) or ())
        _tgt_facs: set[str] = set()
        if state_of(session).target_comp is not None:
            _tgt_facs = set(state_of(session).target_comp.all_factions or [])
        best_i, best_s = 0, -1.0
        for i, name in enumerate(options):
            s = 0.0
            from one_dragon.utils import str_utils
            if name in _tgt_facs:
                s += PICK_BIAS.tome_target_faction
            hit = next((b for b, n in (state.board or {}).items()
                        if n > 0 and str_utils.find_by_lcs(b, name, percent=0.8)), None)
            if hit is not None:
                s += PICK_BIAS.tome_board_hit * (state.board or {})[hit]
            if name in _fw_facs:
                s += PICK_BIAS.tome_framework_faction
            if s > best_s:
                best_i, best_s = i, s
        return best_i

    def decide_wish_trial(self, options: list[str], state: GameState,
                          session: StrategySession, config) -> int:
        """祈愿试炼选卡(r104 接入策略模块;原固定第1张)。

        options = 各卡 objective 文字(OCR)。打分:①金币类(直接经济,阵容无关
        稳妥)+25;②target/框架阵营相关词命中 +20;③「刷新/购买」类操作向
        (与 DP 攒息协同)+10;无信息 fallback idx=0。返回索引。"""
        self._consume_prep_direction_frame(session)   # ADR-0583 入口内务
        if not options:
            return 0
        _tgt_facs: set[str] = set()
        if state_of(session).target_comp is not None:
            _tgt_facs = set(state_of(session).target_comp.all_factions or [])
        fw = getattr(state_of(session), 'transition_framework', '')
        _fw_facs: set[str] = set()
        if fw:
            from sr_od.application.currency_war.kernel.cw_transition import (
                FRAMEWORK_FACTIONS,
            )
            _fw_facs = set(FRAMEWORK_FACTIONS.get(fw, ()) or ())
        best_i, best_s = 0, -1.0
        for i, obj in enumerate(options):
            s = effect_pick_bias(session, obj)
            if '金币' in obj:
                s += PICK_BIAS.wish_gold
            if any(f in obj for f in (_tgt_facs | _fw_facs)):
                s += PICK_BIAS.wish_faction
            if '刷新' in obj or '购买' in obj:
                s += PICK_BIAS.wish_operation
            if s > best_s:
                best_i, best_s = i, s
        return best_i

    def decide_box_card(self, names: list[str], state: GameState,
                        session: StrategySession, config) -> int:
        """武装箱/节点弹窗 4 选 1 装备卡(r104 接入策略模块;原 pick_box_card 内联迁此)。

        打分:①target.key_equips 命中 +100(成型加速压倒一切);
        ②合成材料通用性(_material_value 配方数;生命之花 7/轮滑鞋 6/光能电池 6);
        ③target.key_equips 的合成材料(两跳:该材料能合出 key_equip)命中 +30。
        无信息 fallback idx=0。返回索引(调用方点卡)。"""
        self._consume_prep_direction_frame(session)   # ADR-0583 入口内务
        if not names:
            return 0
        from sr_od.application.currency_war.kernel.cw_prep_expect import (
            material_value as _material_value,
        )
        _key: set[str] = set()
        if state_of(session).target_comp is not None:
            _key = set(state_of(session).target_comp.key_equips or [])
        # key_equip 的合成材料(两跳)
        _key_mats: set[str] = set()
        if _key:
            try:
                # r130 修正:注册表字段是 **recipes**(cw_equipment_data._eq
                # recipes=(('量产型装甲','幸运星'),))——旧代码读 .materials
                # (不存在的属性)→ exception 被 swallow → 材料分静默失效,
                # 幸运星/量产型装甲从拿不到 key_equip 材料加分(局33b 箱仅开
                # 2 次的获取侧根因之一)。recipes 是「配方元组的元组」
                # (每条=(材料a,材料b)),逐条展开。
                from sr_od.application.currency_war.data.cw_equipment_data import (
                    EQUIPMENTS,
                )
                for ke in _key:
                    eq = EQUIPMENTS.get(ke)
                    for recipe in getattr(eq, 'recipes', ()) or ():
                        for m in recipe:
                            if m:
                                _key_mats.add(m)
            except Exception:   # noqa: BLE001  材料表缺失不加分
                pass
        best_i, best_s = 0, -1.0
        for i, n in enumerate(names):
            s = effect_pick_bias(session, n)
            if n in _key:
                s += PICK_BIAS.box_key_equip
            if n in _key_mats:
                s += PICK_BIAS.box_key_material
            s += float(_material_value(n))
            if s > best_s:
                best_i, best_s = i, s
        return best_i

    def decide_shop_action(self, session: StrategySession,
                           config: CurrencyWarConfig) -> Action:
        """商店单动作决策接口(ADR-0517 决策 1/2/5;ADR-0583 升格入契约面)。

        输入 = ``session.shop_state_frame``(黑板:入口观察/单动作投影/
        sim 引擎写);输出 = **恰一个动作**,全函数永不 None——「无动作
        可做」由 ``CloseShop`` 恒可用终结表达(决策 5/6)。决策本体 =
        ``mandate_v1/shop.decide_shop_action``(选择序 = 既有波批优先级
        逐帧取首项)。执行侧单动作循环逐帧调用本接口;sim/兼容路径走
        :meth:`decide_shop_screen` 驱动器(同核循环化)。观察帧缺失 =
        观察层失约,抛错(禁静默按空态决策)。
        入口内务 = 结算惰性 drain + 帧代次消费(:meth:`_consume_shop_direction_frame`;
        方向刷新在决策读视图之前完成,ADR-0583 内化锚)。
        """
        from sr_od.application.currency_war.strategies.impl.mandate_v1 import (
            shop,
        )
        state = session.shop_state_frame
        if state is None:
            raise ValueError(
                'decide_shop_action: session.shop_state_frame 缺失'
                '(黑板契约:入口观察段是唯一写者;None=观察层失约,'
                '禁静默按空态决策)')
        # 入口刷新先于镜像/决策(方向视图 = 本帧语境;ADR-0583 内化锚)
        self._consume_shop_direction_frame(session)
        # v3_b_t 逐帧镜像写者(纯遥测,零行为面;口径与边界见
        # write_shop_mirrors docstring。旧 v3_form_score 已随口径
        # 替换退役,历史账本只读)。写位 = 决策核入口 = 生产单
        # 动作循环与 sim decide_shop_screen 驱动器共同必经点。
        self.write_shop_mirrors(state, session)
        return shop.decide_shop_action(state, session, config,
                                       registry=self.registry)

    def decide_shop_screen(self, session: StrategySession,
                           config: CurrencyWarConfig) -> list[Action]:
        """商店序列兼容驱动器(缺省实现;ADR-0583 降格出 ABC)。

        sim/回放/既有序列锁消费(生产执行侧走单动作循环):逐帧调
        :meth:`decide_shop_action`(单动作核,帧代次消费在核入口)+ ``cw_state.simulate``
        纯投影推进期望态,终结动作(RefreshShop/CompTransaction)截停、
        ``CloseShop`` 收尾不入序列。本缺省 = 通用循环(不绑 mandate 判据);
        mandate 特有记账(已买件/段序号/续段 token)在
        ``MandateV1Strategy.decide_shop_screen`` 覆写。驱动器投影**不写帧类槽**
        (D6:槽在入口消费复位后保持 'none',投影帧不触发刷新)。观察帧
        缺失 = 观察层失约,抛错。"""
        from sr_od.application.currency_war.kernel import cw_state
        state = session.shop_state_frame
        if state is None:
            raise ValueError(
                'decide_shop_screen 驱动器: session.shop_state_frame '
                '缺失(黑板契约:商店观察段是唯一写者;None=观察层失约,'
                '禁静默按空态决策)')
        out: list[Action] = []
        for _ in range(512):   # 防御上界:决策循环不收敛 = 策略器 bug 响亮暴露
            a = self.decide_shop_action(session, config)
            if isinstance(a, cw_state.CloseShop):
                return out
            out.append(a)
            if isinstance(a, (cw_state.RefreshShop, cw_state.CompTransaction)):
                return out      # 终结 op:序列到止(重观察语境)
            state = cw_state.simulate(state, a)
            session.shop_state_frame = state
        raise RuntimeError(
            'decide_shop_screen 驱动器 512 帧未收敛(策略器 bug:'
            f'末态 gold={state.gold} '
            f'bench={cw_state.bench_occupied(state.bench)})')
