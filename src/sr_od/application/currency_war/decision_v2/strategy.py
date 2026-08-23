"""决策框架 v2 策略具现(ADR-0290/0291;DecisionV2Strategy)。

``CwStrategy`` 接口实现:继承 ``LineStrategy`` 复用战略层
(update_target 的信号锁线+桥线选择——线库=候选的 line 标签来源)
与全部执行性钩子(prep 步级/遭遇/补给/巨星/伙伴);**只覆盖
decide_prep**——备战计划走四层:

  层1 候选生成(candidates)→ 层2 硬过滤链(filters:
  应急>追赶>模式)→ 层3 板面查表评分(scoring)→ 层4 预算仲裁
  (arbiter:按分执行+约束收口+完备性审计表)。

**不做默认切换**:配置开关留接口(registry 注入可 A/B),默认
策略仍是 LineStrategy(ADR-0290 渐进迁移:并行开关→锁迁移→删通道)。
"""
from __future__ import annotations

from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.cw_state import GameState
from sr_od.application.currency_war.cw_strategy import StrategySession
from sr_od.application.currency_war.decision_v2.arbiter import (
    arbitrate,
)
from sr_od.application.currency_war.decision_v2.candidates import (
    generate_candidates,
)
from sr_od.application.currency_war.decision_v2.filters import (
    filter_candidates,
    is_emergency,
)
from sr_od.application.currency_war.decision_v2.registry import (
    DEFAULT_REGISTRY,
    DecisionV2Registry,
)
from sr_od.application.currency_war.decision_v2.scoring import score_all
from sr_od.application.currency_war.strategies.line_strategy import (
    LineStrategy,
)


class DecisionV2Strategy(LineStrategy):
    """决策框架 v2:候选生成×板面评分×预算仲裁(骨架版,未标定)。

    骨架语义(诚实声明,ADR-0291):评分表初版=P3 档位系数+息律 EV+
    H3 插值,**未经标定 gate**(EARLY_WIN_DELTA 真值化+deploy 时序
    落地),预期 sim 表现低于 LineStrategy——本版交付的是**结构与
    可审计性**(每轮候选×分数 log/约束审计表),不是胜率。
    """

    STRATEGY_ID = 'decision_v2'
    STRATEGY_NAME = '决策框架 v2(候选×评分×仲裁)'
    AUTHOR = 'OneDragon'
    VERSION = '0.1'
    DESCRIPTION = ('ADR-0290 四层骨架:候选生成→硬过滤→板面查表'
                   '评分→预算仲裁(未标定,并行验证用)')

    def __init__(self, registry: DecisionV2Registry | None = None):
        """registry 可注入(A/B:两套注册表各跑一臂);缺省=骨架初版。"""
        super().__init__()
        self.registry = registry or DEFAULT_REGISTRY

    # ===== 备战计划:四层 =====

    def decide_prep(self, state: GameState, session: StrategySession,
                    config) -> list:
        """备战 shop 计划(四层;执行性收尾沿用 r408 同轮互斥维护)。"""
        registry = self.registry
        # r408 同轮已买/已卖集维护(轮变更重置;互斥约束的数据源)
        key = (state.plane, state.round_num)
        if session.v2_round_key != key:
            session.v2_round_key = key
            session.v2_round_bought = set()
            session.v2_round_sold = set()
        self._ensure_state(session)
        # 应急进出事件喂状态机(与 LineStrategy._decide_prep_dispatch
        # 同语义;v2_state[1] 供层2/层4 的覆盖态判定)
        if is_emergency(state, registry) and not session.v2_state[1]:
            self._feed(session, 'E3')
        elif session.v2_state[1] and not is_emergency(state, registry):
            self._feed(session, 'E8_restart',
                       pop_low=self._pop_low(state, session))
        # 息引擎采样(r406:曾达满息;LevelUp 门 [12] 消费)
        if state.gold >= registry.interest_floor:
            session.v2_ever_full_interest = True
        # 四层
        cands = generate_candidates(state, session, registry)          # 层1
        kept, _flog = filter_candidates(cands, state, session, registry)  # 层2
        scored = score_all(kept, state, session, registry)             # 层3
        result = arbitrate(scored, state, session, registry)           # 层4
        # 执行 log → session.last_candidate_scores(遥测判读可直接读;
        # 既有字段复用,r6 遥测补同源)
        session.last_candidate_scores = {
            f"r{state.round_num}:{r['tag']}:{r['desc']}": r['score']
            for r in result.log[:10] if r['accepted']}
        session.last_candidate_scores_round = state.round_num
        # 同轮集回写(互斥约束跨段累积)
        from sr_od.application.currency_war.cw_state import BuyCard, SellBench
        for a in result.actions:
            if isinstance(a, BuyCard) and a.card.name:
                session.v2_round_bought.add(a.card.name)
            elif isinstance(a, SellBench) \
                    and 0 <= a.bench_idx < len(state.bench or []):
                nm = state.bench[a.bench_idx].char_id
                if nm:
                    session.v2_round_sold.add(nm)
        log.info('[cw][d2] r%d %s 地板%d:采纳 %d/%d 候选(%s)',
                 state.round_num, result.coverage, result.floor,
                 len(result.actions), len(cands),
                 '; '.join(r['desc'] for r in result.log
                           if r['accepted']) or '无')
        return result.actions
