# 未验证(货币战争自主推进期代码,需进对应画面按 od-dev-screen-onboarding 等 skill review 重审后才能信)

"""货币战争 内置默认策略(``DefaultCwStrategy``,``STRATEGY_ID="default"``)。

**阶段 1(Phase 1)薄封装委托**:每个钩子直接调既有模块函数(``cw_events/cw_plan 等(原 cw_events,ADR-0145 拆分)``/``cw_comps``),
逻辑不动 → **零行为变化**(``config.strategy_id="default"`` = 今天打法)。参赛者可继承本类只覆盖
关心的几个钩子(模板方法,低门槛、比赛友好)。

阶段 2(Phase 2,后续)会把 ``cw_events``+``cw_comps`` 逻辑迁进本类方法、权重转类常量、删模块
函数;接口在阶段 1 已冻结,阶段 2 是纯内部重构 + 测试须保绿。

设计见 ``docs/develop/currency_war/strategy/07_plugin.md``;决策见 ADR(D-34/036)。
"""
from __future__ import annotations

from typing import Literal

from one_dragon.utils.log_utils import log
from sr_od.application.currency_war import cw_comps, cw_events, cw_plan, cw_transition
from sr_od.application.currency_war.cw_events import (
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
from sr_od.application.currency_war.cw_performance import (
    HP_CONFIDENCE_THRESHOLD,
    RoundOutcome,
)
from sr_od.application.currency_war.cw_state import (
    Action,
    GameState,
    MatchOutcome,
    PickEvent,
)
from sr_od.application.currency_war.cw_strategy import CwStrategy, StrategySession
from sr_od.application.currency_war.prep_actions import (
    ClickSpheres,
    DeferSpheres,
    DeployMove,
    EnsureShopClosed,
    EnsureShopOpen,
    LevelUp,
    OpenBox,
    OpenTome,
    PickBoxCard,
    RunBuyPhase,
    RunDeploy,
    RunEquip,
    SellBench,
    StartBattle,
)


class DefaultCwStrategy(CwStrategy):
    """内置默认策略 = 今天打法(阶段键控 eval + 硬门贪心 + 蒙特卡洛 D 牌 + 阵容规划)。

    所有钩子委托既有模块函数;``config.strategy_id`` 默认 ``"default"`` → 不配置就是今天打法。
    """

    STRATEGY_ID = "default"
    STRATEGY_NAME = "内置默认策略"
    AUTHOR = "OneDragon"
    VERSION = "0.1"
    DESCRIPTION = "阶段键控 eval + 硬门贪心 + 蒙特卡洛 D 牌 + 阵容规划(见 02/03)"

    # ===== 生命周期 =====

    def create_session(self, config) -> StrategySession:
        """空白 session(rng 留默认,由 run loop 按 ``config.strategy_seed`` 覆盖)。"""
        return StrategySession()

    def on_match_start(self, state: GameState, session: StrategySession, config) -> None:
        """P1 no-op(跨步状态首轮由 ``update_target`` 初始化)。"""
        pass

    def on_round_end(self, state: GameState, session: StrategySession, config,
                     obs: RoundOutcome) -> None:
        """观测驱动:喂掉血/胜负 → ``session.performance``(✅ 已接线:loop 每轮胜结算调用,§11.7)。"""
        session.performance.record(obs)
        # 结算「连胜×N」前缀=方向 → session.last_streak(给下回合 economy C 杠杆:连胜保连胜/连败 fold)。
        session.last_streak = obs.streak
        # 结算屏「小队生命值NN」可靠 → 用它给下回合 prep(HP 结算→下回合 prep 不变)。保血/maybe_pivot 信号地基。
        if obs.hp_confidence >= HP_CONFIDENCE_THRESHOLD:
            session.last_hp = obs.hp_after

    def on_match_end(self, session: StrategySession, config, outcome: MatchOutcome) -> None:
        """P1 no-op(outcome 字段全默认,真实结算屏 OCR 属 P1.5)。"""
        pass

    # ===== 决策 =====

    def update_target(self, state: GameState, session: StrategySession, config) -> None:
        """战略层:首轮 ``select_comp``;其后 ``maybe_pivot``,无 pivot 保持(等价现 shop.py 逻辑,
        但状态进 ``session.target_comp``,非 class-attr)。
        **玩法理解单一源**:docs/game/gameplay/currency_war.md 策略模型 S2(双轨)/S4(定型信号)
        ——本方法是双轨架构的心脏(信号喂入/双轨判定/定型切换/flex 收敛全在此),
        改动前先对表该文档(防实现漂移)。"""
        # ADR-0209:CommitSignals 惰性建(避免 default_factory 环形导入)
        if session.commit_signals is None:
            from sr_od.application.currency_war.cw_transition import CommitSignals
            session.commit_signals = CommitSignals()
        # ADR-0209(接线 2/6):双轨期判定——P1 且最终线未定型(信号未 ready[t 轮门,
        # r56]且未进位面 2)。committed=False 时 get_node_goal 压 DP 升级姿态(P1 攒息过渡)。
        # 定型边界=进 P2(plane>=2,严于文档口径 P2-3;详 cw_transition 注释);
        # 旧 past_commit_deadline 分支被 plane>=2 恒短路,已删(2026-08-18)。
        from sr_od.application.currency_war.cw_transition import t_of
        # r100i(局22 r7 泄漏修复):committed 判定只看 signals.ready,但定型切换可能
        # 被 drought_excluded/供给门拦 → 出现「ready(双轨结束)+ target 还是旧线 +
        # maybe_pivot 信号1 全开」窗口 = 双轨冻结形同虚设(局22:16:18 弃过专家桑博DOT
        # 进排除名单 → r7 信号 ready 但切换被拦 → 信号1 把 target 摇到万敌单C)。
        # 修:**committed = ready 且(切换成功 或 target 已是 leader)**;切换失败
        # (死线/断供)时保持双轨(信号1/2 关),等待 drought/定义型通道。
        _ready = session.commit_signals.ready(t_of(state.plane, state.round_num))
        _lead = session.commit_signals.leader() if _ready else None
        _lead_comp = (next((c for c in cw_comps.COMP_LIBRARY if c.name == _lead[0]), None)
                      if _lead else None)
        _switchable = (_lead_comp is not None
                       and _lead_comp.name not in session.drought_excluded
                       and cw_comps.shop_supply(_lead_comp, state) > 0)
        _committed = (state.plane >= 2
                      or (_ready and (_switchable or (
                          session.target_comp is not None and _lead_comp is not None
                          and session.target_comp.name == _lead_comp.name))))
        state.dual_track_phase = not _committed   # 消费方(plan/prefilter)经 state 读
        # r73 RC3:双源写 session(单一源;shop 循环态/Director 每轮拷回,防 read_game_state
        # 新建对象默认 False 冲掉 —— 断裂指纹:遥测每轮首条 True、循环内全 False)。
        session.dual_track_phase = state.dual_track_phase
        # r70 过渡框架选定(买/上/卖三侧单一源):双轨期每轮按持有刷新;定型后清空
        # (三侧消费见 cw_transition.pick_framework docstring)。
        # r100e portal 偏置:开局环境(概念股/邀请,特型=过渡与终局重叠的成因)
        # 给框架方向 → pick_framework 计数 +3 等效权(可被实际来牌翻越,非锁死)。
        # 环境源 = session.active_env(handle_invest_env 选完写入,已有链路)。
        if state.dual_track_phase:
            from sr_od.application.currency_war.cw_transition import pick_framework
            _portal = (getattr(session, 'active_env', '') or '').strip()
            _mute_until = getattr(session, 'portal_bias_mute', 0)
            # r100g C-2:清框架后的偏置压制窗内不给 portal(防 pick_framework 立即选回)
            if state.round_num <= _mute_until:
                _portal = ''
            # r101 必修②:禁令窗内(=mute 同窗)被清框架不得重新选定;到期解禁。
            _ban = (getattr(session, 'framework_clear_ban', '')
                    if state.round_num <= _mute_until else '')
            # r114(局32 横跳根因):fresh read 的 bench char_id 靠 SIFT,识别时好时坏
            # (shop 开帧/光标/动画)→ owned 计数归零 → 保持滞回失效 → 「未定↔仙舟」
            # 跨轮横跳(局32 实证:藿藿×2+爻光×3 在手仍横跳)。修:pick_framework
            # 的持有输入改 **session tracking**(bot 执行记录,单一真源)优先,
            # fresh read 仅补缺(tracking 空时兜底)——识别失败不再影响框架稳定性。
            _fw_bench = list(getattr(session, 'tracked_bench_chars', None) or [])
            if not _fw_bench:
                _fw_bench = state.bench
            _fw_deployed = list(getattr(session, 'tracked_deployed', None) or [])
            if not _fw_deployed:
                _fw_deployed = state.deployed
            _picked = pick_framework(
                _fw_bench, _fw_deployed, state.shop,
                current=session.transition_framework, portal=_portal)   # r72 滞后
            if _picked and _ban and _picked == _ban:
                # 选回被清框架 → 拒(断供框架不复活);无现任继续未定,板面走散件
                log.info('[cw][target] 清框架禁令窗:拒绝选回断供框架 %s(r%s≤r%s)',
                         _picked, state.round_num, _mute_until)
                _picked = ''
            session.transition_framework = _picked
            if not _ban and _picked:
                session.framework_clear_ban = ''   # 窗外正常选定即清禁令
        else:
            session.transition_framework = ''
            session.framework_clear_ban = ''
        # ADR-0209(接线 3/6):信号领先线 comp 对象 → session(双轨囤牌方向)
        session.stash_comp = None
        if state.dual_track_phase:
            _lead = session.commit_signals.leader()
            if _lead is not None:
                session.stash_comp = next(
                    (c for c in cw_comps.COMP_LIBRARY if c.name == _lead[0]), None)
        # ADR-0209(接线 5/6):flex 收敛白名单——target 的 flex 中,按 bench+board
        # 已铺计数取 top2(玩家「护盾流/减益流二选一」的单局收敛;空=不启用)
        _tc = session.target_comp
        if _tc is not None and _tc.flex_factions:
            from collections import Counter as _Ctr
            _flex_cnt = _Ctr()
            for bc in (*state.bench, *state.deployed):
                if bc.faction in _tc.flex_factions:
                    _flex_cnt[bc.faction] += 1
            _board_flex = {f: c for f, c in state.board.items() if f in _tc.flex_factions}
            for f, c in _board_flex.items():
                _flex_cnt[f] += c
            session.focus_factions = {f for f, _ in _flex_cnt.most_common(2)} if _flex_cnt else set()
            state.focus_factions = session.focus_factions   # evaluate 经 state 读(接线 5/6)
        # 简报词缀注入:read_game_state 不读简报(已过),从 session.briefing_affixes 设 state.enemy_affixes,
        # 经 current_enemy_mechanics → ScoreContext.mechanics → select_comp/maybe_pivot 的 mechanics_fit。
        if session.briefing_affixes:
            state.enemy_affixes = list(session.briefing_affixes)
        # 本局职级(session.selected_difficulty → state → effective_hp_threshold D-32 保血阈值;3.5.1 接线)
        if session.selected_difficulty:
            state.selected_difficulty = session.selected_difficulty
        # 简报首领注入:3 位面 boss 名 → state.bosses → ScoreContext.bosses → comp_score 的 boss_fit。
        # 注:当前 comp.countered_by_bosses 多为空(数据待采,同 competitors.md),boss_fit 暂中性;数据补上即生效。
        if session.briefing_bosses:
            state.plane_bosses = list(session.briefing_bosses)
        # 原 bug:active_env 恒空 → env_fit 全 0.5 → T0 env(如 昼之半神概念股→昼神阿雅)不硬绑。
        if session.active_env:
            state.active_env = session.active_env
        score_ctx = cw_comps.make_score_context(state)
        # ===== ADR-0209 信号喂入(接线 1/6):CommitSignals 累积各源的 comp 分 =====
        # 词缀信号(一次;开局已见过就只喂一次)、商店供给(每回合弱证据)。
        # 投资策略/环境/节点产出的喂点在各自 handler(见 decide_invest/supply 等)。
        if not getattr(session, '_affix_signal_fed', False) and session.briefing_affixes:
            from sr_od.application.currency_war.cw_comps import comp_score as _cs
            session.commit_signals.add('briefing_affix', {
                c.name: _cs(c, state, score_ctx) for c in cw_comps.COMP_LIBRARY})
            session._affix_signal_fed = True
        # 商店供给信号(每回合):各线核心阵营在 shop 的可买性 → 供给分
        if state.shop:
            _supply_scores: dict[str, float] = {}
            for c in cw_comps.COMP_LIBRARY:
                s = cw_comps.shop_supply(c, state)
                if s > 0:
                    _supply_scores[c.name] = s
            if _supply_scores:
                session.commit_signals.add('shop_supply', _supply_scores)
        # → comp 永远建不成 → HP 掉到 4 死。shop-aware select_comp 重选会挑 shop 供得上的 comp。
        # (shop_supply<1.0 = shop 无 target 阵营卡;=1.0 = 本回合买得到 → drought 归 0;正常 shop 波动不会累积)
        DROUGHT_BAIL: int = 5   # T#97:放宽(3 太激进 —— shop 随机 3 轮无阵营卡是正常波动不该弃 target;5 容忍随机,稳 commit)
        # r100(双轨 drought 重定向):双轨期盯**配方框架供给**(板面的实际依赖),
        # 不盯终局线(终局线 P1 冻结,囤件断了只是慢,不弃线)。终局线 drought 判定
        # 只在定型后(非双轨)生效——原逻辑照旧跑在下面,双轨期短路。
        if getattr(state, 'dual_track_phase', False) and session.transition_framework:
            _fw_fac = cw_transition.FRAMEWORK_FACTIONS.get(session.transition_framework, ())
            _fw_supply = (cw_comps.shop_supply(
                type('FW', (), {'factions': list(_fw_fac), 'form_tiers': {}})(), state)
                if _fw_fac else 1.0)
            # 框架断供 → 清框架重选(pick_framework 已有滞后;这里只在「配方框架阵营
            # 断供 ≥5 轮」时清框架重选——比弃终局线便宜得多(共享件保留)。
            # 口径:只判框架阵营(仙舟/列车同行);通用件(千冶·刃等跨框架)无阵营可判,
            # 不在本判定内(断框架阵营但通用件在供 = 配方可维持,不清)。
            session.target_drought = session.target_drought + 1 if _fw_supply < 1.0 else 0
            if session.target_drought >= DROUGHT_BAIL:
                _cleared_fw = session.transition_framework
                log.warning('[cw!][target] 双轨框架 %s 连续 %d 轮断供 → 清框架重选'
                            '(配方重建比终局弃线便宜;终局线不动)',
                            _cleared_fw, session.target_drought)
                session.transition_framework = ''
                session.target_drought = 0
                # r100g 审计必修(C-2):portal 局偏置持久(active_env 每轮 +3)会让
                # 下一轮 pick_framework 立即选回同一框架 → 清框架空转、断供死循环。
                # 清框架时连带压制 portal 偏置 DROUGHT_BAIL 轮(给重选窗口)。
                session.portal_bias_mute = state.round_num + DROUGHT_BAIL
                # r101 审计必修②(5ba9b0a6 C):清标志不够——板面持有的原框架件
                # 计数还在,mute 窗内 pick_framework 仍按持有件选回原框架(空转
                # 周期)。清框架时记禁令名,mute 窗内该框架不得被重新选定(断供
                # 框架不复活;到期自动解禁——板面件还在,持续断供会再次清+续禁)。
                session.framework_clear_ban = _cleared_fw
        elif session.target_comp is not None:
            _supply = cw_comps.shop_supply(session.target_comp, state)
            session.target_drought = session.target_drought + 1 if _supply < 1.0 else 0
            if session.target_drought >= DROUGHT_BAIL:
                # D-16(comp 稳定,2026-08-09):bail 只在**未 invested**(form_progress<0.3)时。
                # 诊断:PIVOT 是集中破坏者(为 comp A 买→bail 切 B→mixed→散)。bail 已 invested 的 comp
                # → 丢投资 + 破坏集中 → 板散 → p2 弱。invested(form_progress≥0.3,已有几单位)则保(ride it out),
                # 避免破坏性 pivot。stable comp → 单方向买 → tier-2 集中 → p2 更强。
                _fp = cw_comps.form_progress(session.target_comp, state)
                if _fp < 0.3:
                    log.info('[cw-target] %s 连续 %d 轮 shop 无阵营卡 + 未 invested(form_progress=%.2f<0.3)→ 弃,重选',
                             session.target_comp.name, session.target_drought, _fp)
                    session.target_comp = None
                    session.target_drought = 0
                else:
                    # r19 live 判读:invested 固执在 P1 后段是慢性死亡——局9「连续 10 轮
                    # 无阵营卡」仍保 → 阵容卡在 0.5-0.75 form → P2 碾压。极端 drought
                    # (≥8 轮零供给)时半成型线也弃(供给断了 = 这条线在当局已死)。
                    if session.target_drought >= 8:
                        # r96(第18局实证):P1 后段(r≥7)弃线必死——弃后转的新线从零建,
                        # 剩余轮次(r7-r9 ≈2-3 战)根本建不成(局18:仙舟 drought 弃→白厄→
                        # 万敌→千冶 三连换,板=三线残骸 14 阵营,r9 boss hp1 惨胜)。
                        # user_playstyle[20]:框架「成型、加深」非推倒。牌运断供在 P1 末段
                        # 的正确响应 = 保持现线靠散件/星级补 + 吃息等 P2 供给恢复
                        # (shop 概率表每轮独立重掷,断 8 轮不代表 P2 还断),
                        # 不是换一条同样建不成的新线。
                        if state.plane == 1 and state.round_num >= 7:
                            log.warning('[cw!][target] %s 连续 %d 轮无阵营卡(P1r%d 后段,'
                                        '弃线无重建轮次→保持;散件/星级补,P2 供给重掷)',
                                        session.target_comp.name, session.target_drought,
                                        state.round_num)
                        else:
                            log.warning('[cw!][target] %s 连续 %d 轮无阵营卡(invested form=%.2f 但供给断绝≥8)→ 极端 drought 弃线重选',
                                        session.target_comp.name, session.target_drought, _fp)
                            if session.target_comp.name not in session.drought_excluded:
                                session.drought_excluded.append(session.target_comp.name)   # r7 review#1:累积名单(单槽被第二条死线覆盖→振荡)
                            session.target_comp = None
                            session.target_drought = 0
                    else:
                        log.info('[cw-target] %s 连续 %d 轮无阵营卡 但 invested(form_progress=%.2f≥0.3)→ 保,不 bail(避免 pivot 破坏集中)',
                                 session.target_comp.name, session.target_drought, _fp)
        # ===== ADR-0209(接线 4/6):定型切换 =====
        # 双轨期信号 ready 或过 deadline → target 锁定为信号领先线(定型;此后
        # dual_track_phase=False,攒的钱拉人口+D 核心,装备/星级全投)。
        # 领先线在 drought_excluded(死线)或断供 → 退 select_comp 最高分。
        # r100i:committed 判定(L125-129)已把 ready+switchable 算出并写 state;
        # 此处**不能**再判 state.dual_track_phase(已被自己写 False,分支永远死)。
        # 复用判定期的 _ready/_switchable:ready 且可切 → 切;被拦 → 保持(双轨已 True)。
        if _ready and _switchable and _lead_comp is not None:
            if session.target_comp is None or session.target_comp.name != _lead_comp.name:
                log.info('[cw-target] ADR-0209 定型:信号 ready(%s,%.2f)→ 切最终线(卖过渡换最终)',
                         _lead[0], _lead[1])
                # 定型边沿:标记 drop 档过渡牌待卖(plan 的集中卖散消费;
                # 场上 drop 牌不卖——战力>卖价,自然被最终线替换)
                session.commit_flip_pending = True
            session.target_comp = _lead_comp
        # count≥2 到 r6-7 才 emergent → 太慢,HP 在 comp 成型前崩。降到 count≥1(starter 任一阵营在场,r1 即触发)
        # (r1 board 有 starters 非空 + select_comp 用 shop_supply 保 acquirable;maybe_pivot 纠偏;drought_bail 兜底)。
        EMERGENT_SIGNAL_COUNT: int = 1
        _counts: dict[str, int] = dict(state.board)
        for _bc in state.bench:
            if _bc.faction and _bc.faction != '?':
                _counts[_bc.faction] = _counts.get(_bc.faction, 0) + 1
        _has_signal = any(_c >= EMERGENT_SIGNAL_COUNT for _c in _counts.values())
        if session.target_comp is None and not _has_signal:
            log.info('[cw-target] emergent:无阵营 count≥2(board+bench)→ target 保持 None(L1+L2 集中化驱动)')
            return
        if session.target_comp is None:
            # r3 review③:用带分版 select_comp_scored——遥测记**实际排序分**
            # (含 steer/acq/board_alignment 乘子的最终分),量纲与决策一致;
            # 且省掉逐个重算 comp_score。
            # r20 补:极端 drought 弃的线排除(否则弃后重选回同一条 = 白弃;供给断绝的线
            # 本局已死,死线不复活)。r7 review#2:bail 后重选加**供给门**(select 不感知
            # shop,ADR-0092 开局选线不动;此路径须候选本回合供得上核心,防共享阵营假换线)。
            # r92 审计 T3:**双轨期 bail 重选优先 CommitSignals leader**(贯穿件锁线,user_playstyle [23])
            # ——分数排序在近空板上是噪声(r88 治 maybe_pivot 的同族;此路径漏网),
            # bail→分数重选→再 bail 可循环。leader 无/断供才落分数排序(非双轨照旧)。
            # 门:drought_excluded 非空 = 本局发生过 bail(只治 bail 循环,不动初始选线语义
            # ——初始选线有 emergent 信号门+供给门,测试锁的行为)。
            if (state.dual_track_phase and session.drought_excluded
                    and session.commit_signals is not None):
                _lead = session.commit_signals.leader()
                _lead_comp = next((c for c in cw_comps.COMP_LIBRARY if c.name == _lead[0]), None) \
                    if _lead else None
                if (_lead_comp is not None
                        and _lead_comp.name not in session.drought_excluded
                        and cw_comps.shop_supply(_lead_comp, state) > 0):
                    session.target_comp = _lead_comp
                    log.info('[cw-target] drought 重选(双轨):CommitSignals leader=%s(分数排序=噪声,防 bail 循环)',
                             _lead_comp.name)
                    session.last_candidate_scores_round = state.round_num
                    session.last_candidate_scores = {_lead_comp.name: round(_lead[1], 4)}
                    return
            scored_cands = cw_comps.select_comp_scored(state, score_ctx, config, top_n=8)
            cands = [c for _s, c in scored_cands
                     if c.name not in session.drought_excluded
                     and cw_comps.shop_supply(c, state) >= 1.0]
            if not cands:   # 供给门全滤光(整波断供)→ 退未排除名单最高分(比 None 好)
                cands = [c for _s, c in scored_cands if c.name not in session.drought_excluded]
            session.target_comp = cands[0] if cands else None
            # 遥测补(2026-08-17 r6):candidate_scores 曾全空(shop.py 落盘 {})——
            # 14 号 close_call 筛选零语料。select_comp top-3 存 session,shop 侧带出
            # (r3 review②:带轮次戳,非本轮回合 shop 侧判陈旧清空)。
            session.last_candidate_scores_round = state.round_num
            session.last_candidate_scores = {c.name: round(s, 4) for s, c in scored_cands}
        else:
            # tracker=session.performance:maybe_pivot **读** tracker —— is_losing_streak 解锁 commit 锁做
            # 保命转型(cw_comps:791)+ losing 时 pivot 阈值 ×0.7(cw_comps:807)。live-verified(2026-08-12):
            # on_round_end 喂 hp_after conf=1.0,trend 真实(HP 82→…→1),is_losing_streak 实触发。
            # (原「maybe_pivot 目前不读 tracker 占位」判断过期已撤回 —— 实接 cw_comps:791/807。)
            # r7 pivot 冷却(治过度换线,两局败因:4/3 线漂移):转线后 N 轮内不再转。
            # r3 review①修正:冷却只封信号 1/2,**保命信号豁免**——hp 危机时必须
            # 永远允许转(否则冷却窗内 hp 崩掉 = 我亲手封死救命通道)。危机判据复用
            # maybe_pivot 同款门(0.75×effective_hp_threshold)。
            # r70 **boss 窗冻结**(治 r9 三连 pivot,run_20260818_191418 实证):r9=固定
            # boss 节点(9 节点/位面),boss 前换线 = 丢弃已成形板面战力去追 0-progress
            # 新线 = 自杀(本局 r9 一个备战窗内 列车→专家桑博→列车 三连 pivot,boss 打完
            # hp 33→1)。boss 窗(node_type 读到 boss,或 round_num>=9 先验)内一切 pivot
            # 冻结 —— 危机响应改由 buy 侧 boss_spend(cw_plan 花光提质量)承担,那才是
            # boss 前正确动作。read_node_type 对 boss 实机核实过(cw_observation:160)。
            # r73 RC1 扩:冻结域含**位面切换后首战**(plane>=2 且 round_num==1)—— P2r1
            # round 重置 1 → 旧定义恰好在此解锁;断崖点(敌强度跳升+过渡板)换线 = 撕掉
            # 已囤投资(RC1 实证:万敌→千冶→专家桑博 两连撕)。P2 首战与 boss 同级:靠
            # 花光买牌成型,不靠换线。
            _cool = getattr(session, 'pivot_cooldown_until', 0)
            _in_crisis = state.hp < int(0.75 * cw_comps.effective_hp_threshold(state))
            _boss_window = (state.node_type == 'boss'
                            or (state.round_num >= 9 and state.node_type != 'supply')
                            or (state.plane >= 2 and state.round_num == 1))
            piv = None
            # r91:冷却**守卫**单一源在 maybe_pivot 函数顶(不变量:两次 pivot 至少隔
            # 冷却轮,无例外);本处 `or _in_crisis` 只是「冷却内仍进函数看危机」的
            # 通道(maybe_pivot 顶部统一拦),不再是守卫本身——同轮两翻(r90c)即旧结构
            # 把守卫放在调用侧 + 危机豁免旁路的病。
            # r100(终局线 P1 冻结):双轨期 target_comp 是**囤牌方向**不是作战方向
            # (作战方向=过渡配方,decision_target 已换),换终局线 = 撕囤件方向,
            # P1 内无重建轮次(局18 三连换实证);危机响应在双轨期=保配方+花光补强非换线。
            # r100g 审计必修(D):双轨期**仍调 maybe_pivot 但只接受定义型结果**——
            # 旧写法直接不调用 = 黑塔纪元类(模式C,per_comp_transition 总纲)在 P1
            # 全程被拦,与设计矛盾;_defining_new(affinity≥0.9)在函数内部,调用侧
            # 冻结就到不了。信号1/2 由 maybe_pivot 内部双轨门关(r88),不受影响。
            if (getattr(state, 'dual_track_phase', False)
                    and not _boss_window and (_in_crisis or state.round_num > _cool)):
                _piv_all = cw_comps.maybe_pivot(state, score_ctx, config, session.target_comp,
                                                tracker=session.performance)
                if _piv_all is not None and _piv_all is not session.target_comp:
                    _defining = any(
                        cw_comps.AUGMENT_COMP_AFFINITY.get(a, {}).get(_piv_all.name, 0.0) >= 0.9
                        for a in score_ctx.held_strategies)
                    if _defining:
                        piv = _piv_all
                        log.info('[cw-target] 双轨期定义型解锁例外:%s(模式C,绕过冻结)',
                                 _piv_all.name)
                    else:
                        log.info('[cw-target] 双轨期冻结终局 pivot(tgt=%s→候选%s 拒;作战=配方%s)',
                                 session.target_comp.name if session.target_comp else 'None',
                                 _piv_all.name,
                                 getattr(session, 'transition_framework', '') or '未定')
                else:
                    log.info('[cw-target] 双轨期冻结终局 pivot(无候选;作战=配方%s,危机交买侧)',
                             getattr(session, 'transition_framework', '') or '未定')
            elif not _boss_window and (_in_crisis or state.round_num > _cool):
                # r100i 定型边沿保护:commit_flip_pending(本轮刚定型切换)期间信号1/2
                # 冻结——新线 form=0 必被旧线分反超,「切完即摇回」= 定型形同虚设
                # (测试实证:切万敌单C 同轮被信号1摇回专家桑博DOT)。
                if getattr(session, 'commit_flip_pending', False):
                    log.info('[cw-target] 定型边沿保护:本轮刚切换(%s),信号1/2 冻结一轮',
                             session.target_comp.name if session.target_comp else 'None')
                else:
                    piv = cw_comps.maybe_pivot(state, score_ctx, config, session.target_comp,
                                               tracker=session.performance)
            elif _boss_window and (_in_crisis or state.round_num > _cool):
                log.info('[cw-target] boss/位面切换 窗(p%sr%s node=%s)冻结 pivot(危机响应交花光成型)',
                         state.plane, state.round_num, state.node_type)
            if piv is not None:
                session.target_comp = piv
                # r87 H2:保命 pivot 用短冷却(1 轮,防连续翻转自激);信号1/2 维持 3 轮。
                _survival = state.hp < int(0.75 * cw_comps.effective_hp_threshold(state))
                _cd_rounds = (cw_comps.PIVOT_SURVIVAL_COOLDOWN_ROUNDS if _survival
                              else cw_comps.PIVOT_COOLDOWN_ROUNDS)
                session.pivot_cooldown_until = state.round_num + _cd_rounds
                log.info('[cw-target] pivot %s → 冷却至 r%s(%s轮,%s)',
                         piv.name, session.pivot_cooldown_until, _cd_rounds,
                         '保命防自激' if _survival else '治过度换线')

    def decide_prep(self, state: GameState, session: StrategySession, config) -> list[Action]:
        """备战 shop 计划:``plan`` 用 ``session.rng``(蒙特卡洛 D 牌,可种子化)+ 决策 target。
        ⚠️ rng 由现「每调用新建 random.Random()」合并为 ``session.rng``(单一可种子源,§11.4);
        未种子时仍真随机,决策分布不变(行为等价,见 D-NN)。
        ADR-0209(接线 3/6):stash_comp=信号领先线(双轨囤牌方向)传入;
        接线 4/6:定型边沿(commit_flip_pending)→ 卖散上限放宽(drop 档加急清)。
        r100(过渡一等公民):双轨期 plan 的 target = **配方伪 comp**(cw_recipe.decision_target
        单一入口;不变量:P1 板面只由过渡配方驱动,终局件囤 bench 不上场)——买牌评分/
        form_progress/skeleton 门自动转向「配方缺口」;stash_comp 照旧囤终局件。
        r128(换血空窗修复,局36 r4 实证):定型边沿 cap 2→6 一次清光旧板但买入
        无对应加急(白厄不在店)→ 卖 6 买 1 → 板面清空靠散牌填,羁绊 6 档→0,
        空窗期 -15~-20 血/轮。修:**1:1 置换语义**——cap 放宽仍生效,但卖量
        由「bench 已有的新线件数」约束(新线件到位一张卖一张;旧板虽 off-target
        但羁绊档战力 > 空板)。deploy_bench D-10 同语义(max_sell=_bench_tgt_n)。
        """
        _flipping = bool(getattr(session, 'commit_flip_pending', False))
        _cap = 6 if _flipping else 2
        if _flipping:
            session.commit_flip_pending = False   # 一次性(本回合清)
            # 1:1 置换:bench 新线件(target/stash core)数 = 可卖上限
            _tgt_names = set(getattr(getattr(session, 'target_comp', None),
                                     'core_chars', ()) or ())
            _stash = getattr(session, 'stash_comp', None)
            if _stash is not None:
                _tgt_names |= set(getattr(_stash, 'core_chars', ()) or ())
            _new_line_n = sum(1 for bc in (state.bench or [])
                              if getattr(bc, 'char_id', '') in _tgt_names)
            _cap = max(2, min(_cap, _new_line_n + 2))   # 基线2+新线件数(渐进清,不一次光)
            log.info('[cw][target] 定型边沿 1:1 置换:bench 新线件 %d → 卖散 cap %d '
                     '(旧板羁绊档保留至新线件到位;r128)', _new_line_n, _cap)
        from sr_od.application.currency_war.cw_recipe import decision_target
        _dt = decision_target(session, state)
        return cw_plan.plan(state, config, config.faction_priority,
                            rng=session.rng, target_comp=_dt,
                            reactive=(_dt is None),
                            stash_comp=getattr(session, 'stash_comp', None),
                            focus_sell_cap=_cap,
                            framework=getattr(session, 'transition_framework', ''))

    def decide_invest(self, kind: Literal["strategy", "env"], options: list[str],
                      state: GameState, session: StrategySession, config) -> PickEvent:
        """投资策略/投资环境 3 选 1。P1 两 kind 同一实现(委托 ``decide_event``);分表现 P2+ 议题。
        ``state.board`` 由调用方传空 stub(overlay 叠备战时 board 不可读,§11.7)。
        ADR-0134:strategy kind 传 session.target_comp(星徽套组/专属强化对齐 target = 成型加速,
        comp 匹配分压倒品质先验)。ADR-0144 修订:env kind 也传 —— 开局环境屏 comp 未定(None,
        行为同旧,阵营定向走 select_comp env_fit);**局中环境屏**(如 联席决策 2-6 节点)comp 已定,
        概念股/邀请/契约阵营条件分(ENV_FACTION_MATCH_FLOOR)生效。
        ADR-0209(接线 1/6):选卡结果喂 CommitSignals(策略 2.0/环境 1.0 权重;
        affinity 表把所选卡映射到 comp 分贡献)。"""
        _tgt = session.target_comp
        pick = cw_events.decide_event(options, config, state, target_comp=_tgt)
        # 信号喂入:所选卡对各线的 affinity → comp 分贡献
        try:
            from sr_od.application.currency_war.cw_comps import AUGMENT_COMP_AFFINITY
            src = 'invest_strategy' if kind == 'strategy' else 'invest_env'
            scores: dict[str, float] = {}
            for opt in options:
                aff = AUGMENT_COMP_AFFINITY.get(opt, {})
                for comp_name, v in aff.items():
                    scores[comp_name] = max(scores.get(comp_name, 0.0), v)
            if scores:
                session.commit_signals.add(src, scores)
        except Exception:   # noqa: BLE001  信号喂入 best-effort
            pass
        return pick

    def decide_supply(self, options: list[SupplyOption], state: GameState,
                      session: StrategySession, config, refresh_used: bool = False) -> SupplyPick:
        """补给选装备/出钻。⚠️ OCR 未就绪(P1 钩子 + 默认委托,handler 不 rewire,随阶段5)。"""
        return cw_events.decide_supply(options, state, session.target_comp, config, refresh_used)

    def decide_encounter(self, options: list[EncounterOption], state: GameState,
                         session: StrategySession, config, refresh_used: bool = False) -> EncounterPick:
        """遭遇难度/词缀避开。⚠️ 后 dormant(遭遇=普通战斗无选项 UI);纯逻辑+测试暂留。"""
        return cw_events.decide_encounter(options, state, session.target_comp, config, refresh_used)

    def decide_megastar(self, options: list[MegastarOption], state: GameState,
                        session: StrategySession, config) -> MegastarPick:
        """巨星选候选:委托 ``cw_comps.select_megastar`` 拿角色名 → 名在 options 命中该 idx;否则 idx=0。
        ⚠️ OCR 未就绪(char_id 全空 → 匹配恒失败 → idx=0 = 今天盲点左候选,随阶段5)。"""
        available = [o.char_id for o in options if o.char_id]
        chosen_name = cw_comps.select_megastar(state, session.target_comp, available)
        if chosen_name:
            for o in options:
                if o.char_id == chosen_name:
                    return MegastarPick(idx=o.idx, reason=f"select_megastar 命中 {chosen_name}")
        return MegastarPick(idx=0, reason="fallback 左候选(OCR 未就绪,char_id 空)")

    def decide_partner(self, options: list[PartnerOption], state: GameState,
                       session: StrategySession, config) -> PartnerPick:
        """选择伙伴:优先 ``config.character_build_around`` / ``target.core_chars`` 命中;否则 idx=0。
        ⚠️ OCR 未就绪(char_id 全空 → 命中恒失败 → idx=0 = 今天盲点 stage 立绘,随阶段5)。"""
        wants: list[str] = list(getattr(config, 'character_build_around', []) or [])
        if session.target_comp is not None:
            wants += list(session.target_comp.core_chars)
        for o in options:
            if o.char_id and o.char_id in wants:
                return PartnerPick(idx=o.idx, reason=f"命中偏好/核心 {o.char_id}")
        return PartnerPick(idx=0, reason="fallback(OCR 未就绪,char_id 空)")

    def decide_planner(self, options: list[PlannerOption], state: GameState,
                       session: StrategySession, config) -> PlannerPick:
        """银狼策划事件(r104 用户定调:接入策略模块由它定;委托 cw_events.decide_planner)。

        升费卡打分含银狼线/在场判定(state.bench+deployed 的 char_id),
        session.target_comp 决定银狼线加成。"""
        return cw_events.decide_planner(options, state, session.target_comp)

    def decide_star_tome(self, options: list[str], state: GameState,
                         session: StrategySession, config) -> int:
        """星徽秘典四选一(r104 接入策略模块;原 loop 内联 board 匹配迁此)。

        打分:①target_comp.all_factions 命中(终局线需要的阵营星徽 = +40);
        ②board 已有该阵营(板上已有=边际价值高,board 计数 ×8);
        ③当前配方框架阵营命中(双轨期过渡配方需要,+15)。无命中 fallback idx=0。
        返回 options 索引。"""
        if not options:
            return 0
        fw = getattr(session, 'transition_framework', '')
        _fw_facs: set[str] = set()
        if fw:
            from sr_od.application.currency_war.cw_transition import FRAMEWORK_FACTIONS
            _fw_facs = set(FRAMEWORK_FACTIONS.get(fw, ()) or ())
        _tgt_facs: set[str] = set()
        if session.target_comp is not None:
            _tgt_facs = set(session.target_comp.all_factions or [])
        best_i, best_s = 0, -1.0
        for i, name in enumerate(options):
            s = 0.0
            from one_dragon.utils import str_utils
            if name in _tgt_facs:
                s += 40.0
            hit = next((b for b, n in (state.board or {}).items()
                        if n > 0 and str_utils.find_by_lcs(b, name, percent=0.8)), None)
            if hit is not None:
                s += 8.0 * (state.board or {})[hit]
            if name in _fw_facs:
                s += 15.0
            if s > best_s:
                best_i, best_s = i, s
        return best_i

    def decide_wish_trial(self, options: list[str], state: GameState,
                          session: StrategySession, config) -> int:
        """祈愿试炼选卡(r104 接入策略模块;原固定第1张)。

        options = 各卡 objective 文字(OCR)。打分:①金币类(直接经济,阵容无关
        稳妥)+25;②target/框架阵营相关词命中 +20;③「刷新/购买」类操作向
        (与 DP 攒息协同)+10;无信息 fallback idx=0。返回索引。"""
        if not options:
            return 0
        _tgt_facs: set[str] = set()
        if session.target_comp is not None:
            _tgt_facs = set(session.target_comp.all_factions or [])
        fw = getattr(session, 'transition_framework', '')
        _fw_facs: set[str] = set()
        if fw:
            from sr_od.application.currency_war.cw_transition import FRAMEWORK_FACTIONS
            _fw_facs = set(FRAMEWORK_FACTIONS.get(fw, ()) or ())
        best_i, best_s = 0, -1.0
        for i, obj in enumerate(options):
            s = 0.0
            if '金币' in obj:
                s += 25.0
            if any(f in obj for f in (_tgt_facs | _fw_facs)):
                s += 20.0
            if '刷新' in obj or '购买' in obj:
                s += 10.0
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
        if not names:
            return 0
        from sr_od.application.currency_war.operations.handlers.handle_supply_box import (
            _material_value,
        )
        _key: set[str] = set()
        if session.target_comp is not None:
            _key = set(session.target_comp.key_equips or [])
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
                from sr_od.application.currency_war.cw_equipment_data import EQUIPMENTS
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
            s = 0.0
            if n in _key:
                s += 100.0
            if n in _key_mats:
                s += 30.0
            s += float(_material_value(n))
            if s > best_s:
                best_i, best_s = i, s
        return best_i
    # ===== 备战决策环步级决策(doc 15 §5.1-5.3 参考实现;P1)=====

    def decide_prep_action(self, obs, session: StrategySession, config):
        """备战决策环步级决策 = doc 15 §5.1-5.3 参考实现(奖励收取 → 腾席链 → 主流程)。"

        规则序(每步全量重判,先命中先出):
        1. 武装箱 overlay 开 → PickBoxCard(执行器默认选卡,v7 M-3;OpenBox 两步链第二步);
        2. 有箱 → OpenBox(箱白占席,先开=腾席+得装备;两步非一步,F1/L-5);
        3. 有球且有空席 → ClickSpheres(k=min(free, n);掉箱由规则 1/2 下步统筹);
        4. 有球无空席且 defer<2 → 腾席链一步(deploy 空位 > 升级 > 卖最弱 > DeferSpheres);
        5. 球箱皆无 或 defer≥2 → 主流程(买→部署→装备→出战,Run* 组合;P1 过渡)。

        obs P1 恒空字段(overlay_state/overlay_options/shop_cards/owned_equips)不依赖(§13.4);
        gold 仅 shop_open 且 obs.state fresh 时可信(关态读空,§5.2b M2)。
        """
        if obs.box_overlay_open:
            return PickBoxCard(card_idx=None)   # 执行器默认选卡(P1 住执行器;P5 上移策略)
        # r11 review P0:defer 门(对照收球规则 4)——OpenTome 失败反复重试时(执行器连败置
        # defer),无门活锁:M55 P2 全部 365 条决策全是 OpenTome 重试,71→84 金全程闲置、板面
        # 冻结硬吃两仗。典籍疑似误检/开不动 → 放弃走主流程;下轮环入口 defer 清零重判自愈。
        if getattr(obs, 'tomes', None) and session.defer_count < 2:
            return OpenTome()                   # 开典籍即腾席+触发星徽四选一(2026-08-16;选卡 loop 0i)
        if obs.boxes:
            return OpenBox()                     # 开箱即腾席 + 得装备
        if obs.spheres and obs.free_bench_slots > 0:
            # live 2026-08-14(1-2 实锤):商店开态奖励面板 [1257,140,1662,493] 与「刷新概率表」
            # 按钮 [945,360,1415,410] 重叠(x1257-1415∩y360-410)——HoughCircles 把按钮图形误检成
            # 假球,点击即开概率表弹窗(遮挡 → bail → 乒乓)。商店开 → 先关店,清洁面板上再收球。
            if obs.shop_open:
                return EnsureShopClosed()
            # live 2026-08-15(M12 1-9 实锤):owned 装备栏溢出到奖励区 → 道具图标被误检成假球,
            # 点击无效 → 验证失败循环 → bail×3 停机。defer 门扩到收球:反复失败(框架置 defer)后
            # 放弃收球走主流程;下轮环入口 defer 清零重判(真球可再收,自愈)。
            if session.defer_count >= 2:
                log.info('[cw][prep] 球疑假检(owned 溢出,点击反复失败)→ defer 跳过收球,走主流程')
                return self._main_flow_step(obs, session, config)
            return ClickSpheres(max_k=min(obs.free_bench_slots, len(obs.spheres)))
        if obs.spheres and obs.free_bench_slots <= 0 and session.defer_count < 2:
            return self._free_bench_step(obs, session, config)
        return self._main_flow_step(obs, session, config)

    def _free_bench_step(self, obs, session: StrategySession, config):
        """腾席链一步(§5.2;优先级是默认策略的选择,非框架强制;继承者可只覆盖本方法)。

        r100 审计必修①:target 改走 decision_target 单一入口——双轨期腾席链的上/卖
        判据同 plan 路径(配方驱动),消除双路径语义分叉(旧:步级读终局 target →
        r≥8 终局件上场 + 腾席链 c 无框架 keep 集可卖掉配方 carry)。
        """
        st = self._pseudo_state(obs, session)
        from sr_od.application.currency_war.cw_recipe import decision_target
        target = decision_target(session, st)
        # ⚖️ r94:同名在场守卫收口 cw_plan.deploy_legal(全局不变量单一源;5.1.7)。
        # 第14局 r9 实证:藿藿已在场,腾席链a把 bench 藿藿拖向空位 5 次全被游戏拒
        # → director 屏蔽 → 爻光滞留 bench 到局末。_should_deploy 顶部同守卫,
        # 此处显式跳过是为了「失败记忆」计数不污染(被拦的不再进候选循环)。
        _dep_names = cw_plan.deployed_name_set(st)
        # a. deploy 空位(零成本最优):bench 有过 _should_deploy 的角色 → DeployMove
        if obs.deploy_vacancy > 0:
            for bc in list(obs.bench_chars):
                if not cw_plan.deploy_legal(bc, _dep_names):
                    continue   # 同名已在场(游戏拒),留 bench 待 3合1 合并
                # r93 失败记忆:同角色拖拽已被游戏拒过 → 跳过(重试同目标=白烧环步,
                # 藿藿 5 连败实证;下一候选继续)。备战后对账刷新会自然重置状态。
                if session.deploy_fail_counts.get(bc.char_id, 0) >= 1:
                    continue
                if cw_plan._should_deploy(bc, st, target):
                    row, ok = cw_plan._pick_deploy_row(st, bc, target)
                    if not ok:
                        continue
                    occupied = obs.front_occupied if row == 'front' else obs.back_occupied
                    size = obs.front_size if row == 'front' else obs.back_size
                    empty = next((n for n in range(1, size + 1) if n not in occupied), None)
                    if empty is not None:
                        log.info(f'[cw][prep] 腾席链a:deploy空位 → 槽{bc.slot}({bc.char_id})'
                                 f' → {row}{empty}')
                        return DeployMove(from_slot=bc.slot, to_row=row, to_slot=empty)
        # b. 升级扩容(cap+1 → 回 a):gold 需可信(framework F2 state_gold_trusted,MED-1 接线;
        # shop 开态 + fresh state 才信 —— 关态读空/缓存过期都会误判无金 → 链 c 误卖)
        if st.level < 10:
            if getattr(obs, 'state_gold_trusted', False) and obs.state is not None:
                fresh = self._fresh_state(obs, session)
                if cw_plan.level_up_gate(fresh, target):
                    log.info(f'[cw][prep] 腾席链b:升级 lv{fresh.level} gold={fresh.gold}(cap+1 → 回 a)')
                    return LevelUp()
            else:
                log.info('[cw][prep] 腾席链b:需 gold 真值 → EnsureShopOpen(开态重读)')
                return EnsureShopOpen()
        # c. 卖最弱(_weakest_bench_idx 含 3合1 重复件保护;全保护 → None)
        idx = cw_plan._weakest_bench_idx(st, config.character_priority, target)
        if idx is not None and idx < len(st.bench):
            bc = st.bench[idx]
            log.info(f'[cw][prep] 腾席链c:卖最弱 槽{bc.slot}({bc.char_id})')
            return SellBench(slot=bc.slot)
        # d. 全是有用角色 → 留置(DeferSpheres;框架计 defer_count,门=2)
        log.info('[cw][prep] 腾席链d:无可卖/不可升 → DeferSpheres(球留置)')
        return DeferSpheres()

    def _main_flow_step(self, obs, session: StrategySession, config):
        """主流程推进(§5.3;Run* 组合 P1 过渡,阶段位 prep_phase 由 Director 环入口清零)。

        阶段位在**出动作时**前移(策略看不到执行结果;失败由框架 fail/屏蔽/恢复链兜住,
        失败动作不无限重提案)。M-6 门:进 RunBuyPhase 前保证 free>0,否则跳过买牌直奔部署
        (防 shop.py 内 _handle_bench_full 位置式卖,doc 15 §8 P1 残留风险)。
        """
        if session.prep_phase <= 0:
            session.prep_phase = 1
            if obs.free_bench_slots <= 0:
                # M-6 门:free=0 跳过买牌(防 shop.py 内 _handle_bench_full 位置式卖)。
                # M24 卡死修(2026-08-16):满席且**无球**时旧逻辑直奔 RunDeploy → deploy-swap 卖
                # 拖拽失败(bug#1 变体)→ 警告不消 → 死循环;金不够升级时链 b 也不通。修:满席
                # 一律先过腾席链 a/b/c(deploy 空位/升级扩容/卖最弱 —— _weakest_bench_idx 是保护式
                # 卖,非位置式卖,与 M-6 门防的不冲突);链 d(DeferSpheres)不入 —— 无球时 defer 无意义,
                # 落回部署段保持原行为。
                log.info('[cw][prep] M-6 门:free=0 → 腾席链 a/b/c 破满席(买牌跳过)')
                step = self._free_bench_step(obs, session, config)
                if not isinstance(step, DeferSpheres):
                    return step
                return self._main_flow_step(obs, session, config)   # 链全空 → 部署段
            return RunBuyPhase()
        if session.prep_phase == 1:
            session.prep_phase = 2
            return RunDeploy()
        if session.prep_phase == 2:
            session.prep_phase = 3
            return RunEquip()
        # ⚖️ r23(强度表消费,p1-1 掉 25.5 实证):空板/严重缺员出战守卫——54 局 5 次空板出战
        # (lv4,dep=0),p1-1/p1-7 高强度节点掉 24-29 血。deployed 有 tracking(bench/deployed chars)
        # 且板上 0 人 → 不出战,回部署段(RunDeploy 会拖 bench 上场);bench 也空(真无牌)才放行
        # (开局首轮无牌是正常态,游戏会给保底板?不——p1-1 开局必能买到牌,空板=部署失败,重试)。
        _dep_n = len(obs.deployed_chars or [])
        _bench_n = len(obs.bench_chars or [])
        if _dep_n == 0 and _bench_n > 0 and session.prep_phase_retry < 2:
            session.prep_phase_retry += 1
            session.prep_phase = 1   # 回部署段重试(bench 有人没上去)
            log.info('[cw][prep] 空板出战守卫:板上 0 人 bench %d 人 → 回部署段(p1-1 类节点掉 24+ 血)',
                     _bench_n)
            return RunDeploy()
        return StartBattle()

    def _pseudo_state(self, obs, session: StrategySession) -> GameState:
        """从 session tracking 组装决策用 GameState(环内轻量,SIFT 重读只在环入口)。"""
        st = GameState()
        st.board = {}
        for bc in session.tracked_deployed:
            if bc.faction and bc.faction != '?':
                st.board[bc.faction] = st.board.get(bc.faction, 0) + 1
        st.bench = list(session.tracked_bench_chars)
        st.deployed = list(session.tracked_deployed)
        st.level = session.last_level_obs or (
            session.last_state.level if session.last_state is not None else 1)
        if obs is not None and getattr(obs, 'state_gold_trusted', False) and obs.state is not None:
            st.gold = obs.state.gold   # 仅 F2 可信标记时采用(gold 关态读空,MED-1)
            st.plane = obs.state.plane
            st.round_num = obs.state.round_num
        elif session.last_state is not None:
            st.plane = session.last_state.plane
            st.round_num = session.last_state.round_num
        # r69 review:hp 过新鲜度门(陈旧 last_hp 不进 pseudo state;门单源 cw_strategy.gated_hp,
        # 现读基准 = last_state.hp 框架末次读值,None 时 100 默认)。
        from sr_od.application.currency_war.cw_strategy import gated_hp
        _t = (st.plane - 1) * 9 + st.round_num if (st.plane and st.round_num) else None
        _cur_hp = session.last_state.hp if session.last_state is not None else 100
        st.hp = gated_hp(_cur_hp, session, _t)
        # r101 审计必修①(5ba9b0a6 T6 实证):漏拷 dual_track_phase → 腾席链的
        # decision_target 恒走非双轨分支退终局 comp,r100 必修①(步级路径迁移)
        # 空转——r≥8 终局件提前上场+配方 carry 可被卖。单一源在 session
        # (r73 RC3),此处与 shop 循环态同款拷贝。
        st.dual_track_phase = bool(getattr(session, 'dual_track_phase', False))
        return st

    def _fresh_state(self, obs, session: StrategySession) -> GameState:
        """shop 开态 fresh state(obs.state)+ bench tracking seed(gold 可信,腾席链 b 用)。"""
        st = obs.state if obs.state is not None else GameState()
        fresh = st.copy()
        if session.tracked_bench_chars:
            fresh.bench = list(session.tracked_bench_chars)
        return fresh

