"""货币战争 内置默认策略(``DefaultCwStrategy``,``STRATEGY_ID="default"``)。

**阶段 1(Phase 1)薄封装委托**:每个钩子直接调既有模块函数(``cw_decisions``/``cw_comps``),
逻辑不动 → **零行为变化**(``config.strategy_id="default"`` = 今天打法)。参赛者可继承本类只覆盖
关心的几个钩子(模板方法,低门槛、比赛友好)。

阶段 2(Phase 2,后续)会把 ``cw_decisions``+``cw_comps`` 逻辑迁进本类方法、权重转类常量、删模块
函数;接口在阶段 1 已冻结,阶段 2 是纯内部重构 + 测试须保绿。

设计见 ``docs/game/currency_war/strategy/11_strategy_plugin.md`` §11.6;决策见 D-34。
"""
from __future__ import annotations

from typing import Literal

from sr_od.application.currency_war import cw_comps, cw_decisions
from sr_od.application.currency_war.cw_decisions import (
    EncounterOption,
    EncounterPick,
    MegastarOption,
    MegastarPick,
    PartnerOption,
    PartnerPick,
    SupplyOption,
    SupplyPick,
)
from sr_od.application.currency_war.cw_performance import RoundOutcome
from sr_od.application.currency_war.cw_state import (
    Action,
    GameState,
    MatchOutcome,
    PickEvent,
)
from sr_od.application.currency_war.cw_strategy import CwStrategy, StrategySession


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
        """观测驱动:喂掉血/胜负 → ``session.performance``(默认实现非空,但 P1 无 caller,§11.7)。"""
        session.performance.record(obs)

    def on_match_end(self, session: StrategySession, config, outcome: MatchOutcome) -> None:
        """P1 no-op(outcome 字段全默认,真实结算屏 OCR 属 P1.5)。"""
        pass

    # ===== 决策 =====

    def update_target(self, state: GameState, session: StrategySession, config) -> None:
        """战略层:首轮 ``select_comp``;其后 ``maybe_pivot``,无 pivot 保持(等价现 shop.py 逻辑,
        但状态进 ``session.target_comp``,非 class-attr)。"""
        score_ctx = cw_comps.make_score_context(state)
        if session.target_comp is None:
            cands = cw_comps.select_comp(state, score_ctx, config)
            session.target_comp = cands[0] if cands else None
        else:
            # tracker=session.performance:maybe_pivot 目前不读 tracker(信号3 走 state.hp;tracker 是
            # 声明未用的占位,与其 docstring「待接」一致)→ 传不传都不影响行为;tracker 驱动的保命观测是 P1.5。
            piv = cw_comps.maybe_pivot(state, score_ctx, config, session.target_comp,
                                       tracker=session.performance)
            if piv is not None:
                session.target_comp = piv

    def decide_prep(self, state: GameState, session: StrategySession, config) -> list[Action]:
        """备战 shop 计划:``plan`` 用 ``session.rng``(蒙特卡洛 D 牌,可种子化)+ ``session.target_comp``。
        ⚠️ rng 由现「每调用新建 random.Random()」合并为 ``session.rng``(单一可种子源,§11.4);
        未种子时仍真随机,决策分布不变(行为等价,见 D-NN)。"""
        return cw_decisions.plan(state, config, config.faction_priority,
                                 rng=session.rng, target_comp=session.target_comp)

    def decide_invest(self, kind: Literal["strategy", "env"], options: list[str],
                      state: GameState, session: StrategySession, config) -> PickEvent:
        """投资策略/投资环境 3 选 1。P1 两 kind 同一实现(委托 ``decide_event``);分表现 P2+ 议题。
        ``state.board`` 由调用方传空 stub(overlay 叠备战时 board 不可读,§11.7)。"""
        return cw_decisions.decide_event(options, config, state)

    def decide_supply(self, options: list[SupplyOption], state: GameState,
                      session: StrategySession, config, refresh_used: bool = False) -> SupplyPick:
        """补给选装备/出钻。⚠️ OCR 未就绪(P1 钩子 + 默认委托,handler 不 rewire,随阶段5)。"""
        return cw_decisions.decide_supply(options, state, session.target_comp, config, refresh_used)

    def decide_encounter(self, options: list[EncounterOption], state: GameState,
                         session: StrategySession, config, refresh_used: bool = False) -> EncounterPick:
        """遭遇难度/词缀避开。⚠️ D-35 后 dormant(遭遇=普通战斗无选项 UI);纯逻辑+测试暂留。"""
        return cw_decisions.decide_encounter(options, state, session.target_comp, config, refresh_used)

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

    def decide_boss_priority(self, bosses: list[str], state: GameState,
                             session: StrategySession, config) -> list[str]:
        """boss 克制调整阵营优先级。⚠️ 全代码库零调用(缺 boss OCR + dispatch),随阶段5。"""
        return cw_decisions.decide_boss_priority(bosses, config)
