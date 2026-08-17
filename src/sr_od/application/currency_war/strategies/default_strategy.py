# 未验证(货币战争自主推进期代码,需进对应画面按 od-dev-screen-onboarding 等 skill review 重审后才能信)

"""货币战争 内置默认策略(``DefaultCwStrategy``,``STRATEGY_ID="default"``)。

**阶段 1(Phase 1)薄封装委托**:每个钩子直接调既有模块函数(``cw_events/cw_plan 等(原 cw_events,ADR-0145 拆分)``/``cw_comps``),
逻辑不动 → **零行为变化**(``config.strategy_id="default"`` = 今天打法)。参赛者可继承本类只覆盖
关心的几个钩子(模板方法,低门槛、比赛友好)。

阶段 2(Phase 2,后续)会把 ``cw_events``+``cw_comps`` 逻辑迁进本类方法、权重转类常量、删模块
函数;接口在阶段 1 已冻结,阶段 2 是纯内部重构 + 测试须保绿。

设计见 ``docs/develop/currency_war/strategy/11_strategy_plugin.md`` §11.6;决策见 。
"""
from __future__ import annotations

from typing import Literal

from one_dragon.utils.log_utils import log
from sr_od.application.currency_war import cw_comps, cw_events, cw_plan
from sr_od.application.currency_war.cw_events import (
    EncounterOption,
    EncounterPick,
    MegastarOption,
    MegastarPick,
    PartnerOption,
    PartnerPick,
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
        但状态进 ``session.target_comp``,非 class-attr)。"""
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
        # → comp 永远建不成 → HP 掉到 4 死。shop-aware select_comp 重选会挑 shop 供得上的 comp。
        # (shop_supply<1.0 = shop 无 target 阵营卡;=1.0 = 本回合买得到 → drought 归 0;正常 shop 波动不会累积)
        DROUGHT_BAIL: int = 5   # T#97:放宽(3 太激进 —— shop 随机 3 轮无阵营卡是正常波动不该弃 target;5 容忍随机,稳 commit)
        if session.target_comp is not None:
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
                    log.info('[cw-target] %s 连续 %d 轮无阵营卡 但 invested(form_progress=%.2f≥0.3)→ 保,不 bail(避免 pivot 破坏集中)',
                             session.target_comp.name, session.target_drought, _fp)
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
            scored_cands = cw_comps.select_comp_scored(state, score_ctx, config, top_n=3)
            cands = [c for _s, c in scored_cands]
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
            _cool = getattr(session, 'pivot_cooldown_until', 0)
            _in_crisis = state.hp < int(0.75 * cw_comps.effective_hp_threshold(state))
            piv = None
            if _in_crisis or state.round_num > _cool:
                piv = cw_comps.maybe_pivot(state, score_ctx, config, session.target_comp,
                                           tracker=session.performance)
            if piv is not None:
                session.target_comp = piv
                session.pivot_cooldown_until = state.round_num + cw_comps.PIVOT_COOLDOWN_ROUNDS
                log.info('[cw-target] pivot %s → 冷却至 r%s(治过度换线,保命信号豁免)',
                         piv.name, session.pivot_cooldown_until)

    def decide_prep(self, state: GameState, session: StrategySession, config) -> list[Action]:
        """备战 shop 计划:``plan`` 用 ``session.rng``(蒙特卡洛 D 牌,可种子化)+ ``session.target_comp``。
        ⚠️ rng 由现「每调用新建 random.Random()」合并为 ``session.rng``(单一可种子源,§11.4);
        未种子时仍真随机,决策分布不变(行为等价,见 D-NN)。"""
        return cw_plan.plan(state, config, config.faction_priority,
                                 rng=session.rng, target_comp=session.target_comp,
                                 reactive=(session.target_comp is None))

    def decide_invest(self, kind: Literal["strategy", "env"], options: list[str],
                      state: GameState, session: StrategySession, config) -> PickEvent:
        """投资策略/投资环境 3 选 1。P1 两 kind 同一实现(委托 ``decide_event``);分表现 P2+ 议题。
        ``state.board`` 由调用方传空 stub(overlay 叠备战时 board 不可读,§11.7)。
        ADR-0134:strategy kind 传 session.target_comp(星徽套组/专属强化对齐 target = 成型加速,
        comp 匹配分压倒品质先验)。ADR-0144 修订:env kind 也传 —— 开局环境屏 comp 未定(None,
        行为同旧,阵营定向走 select_comp env_fit);**局中环境屏**(如 联席决策 2-6 节点)comp 已定,
        概念股/邀请/契约阵营条件分(ENV_FACTION_MATCH_FLOOR)生效。"""
        _tgt = session.target_comp
        return cw_events.decide_event(options, config, state, target_comp=_tgt)

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
        """腾席链一步(§5.2;优先级是默认策略的选择,非框架强制;继承者可只覆盖本方法)。"""
        st = self._pseudo_state(obs, session)
        target = session.target_comp
        # a. deploy 空位(零成本最优):bench 有过 _should_deploy 的角色 → DeployMove
        if obs.deploy_vacancy > 0:
            for bc in list(obs.bench_chars):
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
        st.hp = session.last_hp if session.last_hp is not None else 100
        return st

    def _fresh_state(self, obs, session: StrategySession) -> GameState:
        """shop 开态 fresh state(obs.state)+ bench tracking seed(gold 可信,腾席链 b 用)。"""
        st = obs.state if obs.state is not None else GameState()
        fresh = st.copy()
        if session.tracked_bench_chars:
            fresh.bench = list(session.tracked_bench_chars)
        return fresh

