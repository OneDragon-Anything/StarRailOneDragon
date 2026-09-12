"""P2 单节点重放模拟(自 cw_sim 拆出,分包期6)。

P2ReplayEntry 描述一场 P2 节点的实机重放输入;simulate_p2_replay_entry
复用 P1 引擎跑 handoff 后的节点段(战斗校准来自 kernel/cw_battle_calib)。
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from pathlib import Path

from sr_od.application.currency_war.data.cw_battle_tables import (
    P2CombatCalib,
)

# 血预算停手·终止分支账本决策位(设计 迁移审计 w659(git 历史) v2 §5.1 R4;ADR-0469)——
# 账本行 'terminal_release' 键的写入侧单一源 =
# sim/checks/segments.terminal_release_bit(sim 引擎轮入口调用,本模块
# 只消费行键不作记账面)。
from sr_od.application.currency_war.kernel.cw_investments import (
    STRATEGY_EFFECTS,
    EconomyEffect,
    normalize_invest_name,
)
from sr_od.application.currency_war.kernel.cw_exec_state import (
    BENCH_CAPACITY,
    BenchChar,
    deployed_from_compact,
)
from sr_od.application.currency_war.kernel.cw_state import GameState
from sr_od.application.currency_war.strategies.impl.cw_strategy import StrategySession

# 开局 bench 构成(遥测校准:开局 4 张,1 费主导)
START_BENCH_COUNT: int = 4
START_BENCH_COST_WEIGHTS: tuple[tuple[int, float], ...] = ((1, .65), (2, .35))


def _overlay_xp_per_refresh(strategy_names: list[str]) -> int:
    """付费刷新产经验数值(单一源 = ``cw_investments.STRATEGY_EFFECTS`` overlay)。

    - 逐持卡名(先 normalize_invest_name 归一 OCR 分隔符形变)查 overlay 的
      EffectSpec,payload 为 EconomyEffect 时累加 xp_per_refresh;未入 overlay
      的卡不供值 —— overlay 是该查询键的唯一供数面,overlay 值变更 sim 跟随。
    - pending 条目(verdict=None)保守支:其 payload 数值本身即按保守支建模
      (现均无 xp_per_refresh,与旧 STRATEGY_ECONOMY 聚合路径同值);verdict
      定谳若引入新语义(如 经验就是财富 改道),须回本查询点同步。
    """
    total = 0
    for n in strategy_names:
        spec = STRATEGY_EFFECTS.get(normalize_invest_name(n))
        if spec is None or not isinstance(spec.payload, EconomyEffect):
            continue
        total += spec.payload.xp_per_refresh
    return total

# 收入模型(r305 真值接入:sim 与决策共用 cw_economy 单一源;
# ADR-0439 收入口径修正:败轮节点金 + 奖励轮 base/streak 成对查表)
from sr_od.application.currency_war.kernel.cw_economy import (  # noqa: E402,F401
    BASE_INCOME,
    ECONOMY_CALIB_VERSION,
    LOSS_GOLD_BY_NODE,
    REWARD_BASE_GOLD_BY_ROUND,
    streak_gold,
)
from sr_od.application.currency_war.sim.engine_p1 import simulate_p1  # noqa: E402
from sr_od.application.currency_war.sim.pool import SimResult  # noqa: E402


@dataclass
class P2ReplayEntry:
    """案 b 臂真值进场态(`w193_p2sim/`/ADR-0377;``simulate_p2_replay_entry``
    的输入)。

    字段来源 = 生产 replay decisions 的 plane=2 首行 state(锚脚本
    构造);bench/deployed 为 dict 列表(char_id/faction/star/
    position_pref/equips),与生产遥测同构。有限牌池消费态不可观
    (迁移审计 w186(git 历史) 表 #4 K4)→ 满池假设 + 标注。
    """

    hp: int
    gold: int
    level: int
    board: dict[str, int] = field(default_factory=dict)
    bench: list[dict] = field(default_factory=list)
    deployed: list[dict] = field(default_factory=list)
    equips: list[str] = field(default_factory=list)
    xp: int = 0
    xp_progress: tuple[int, int] | None = None
    streak: int = 0
    locked_comp: str = ''

    @staticmethod
    def _unit(u: dict, slot: int) -> BenchChar:
        return BenchChar(
            slot=slot, char_id=u.get('char_id', ''),
            faction=u.get('faction', '?'),
            star=int(u.get('star', 1) or 1),
            position_pref=u.get('position_pref', 'back'),
            equips=list(u.get('equips') or []))

    def build_state(self) -> GameState:
        """进场态 → GameState(plane=2;bench 保 9 槽 pad 语义)。"""
        st = GameState()
        st.plane, st.level, st.gold, st.hp = 2, self.level, self.gold, self.hp
        st.board = dict(self.board)
        for i, u in enumerate(self.bench[:BENCH_CAPACITY]):
            st.bench[i] = self._unit(u, i + 1)
        # ADR-0392:进场态紧缩序 → 槽位表(按 position_pref 路由落槽)
        st.deployed = deployed_from_compact(
            [self._unit(u, i + 1) for i, u in enumerate(self.deployed)])
        st.equips = list(self.equips)
        st.streak = self.streak
        return st



def simulate_p2_replay_entry(entry: P2ReplayEntry, seed: int, *,
                             pool: str | Path = 'snapshot',
                             p2_combat: P2CombatCalib | None = None,
                             use_refresh: bool = True) -> SimResult:
    """案 b 交叉校验臂(`w193_p2sim/`/ADR-0377;迁移审计 w186(git 历史) 设计 §4/§3 锚 R1)。

    从真值 P2 进场态(hp/gold/board/bench/deployed/level/意向)直接
    跑 P2 段——**共享 ``simulate_p1`` 的 P2 段循环体**(经 ``_p2_entry``
    注入跳过 P1 段,单一源零复制)。锚 R1 对拍口径:存活轮分布/战斗
    胜率/逐轮掉血带覆盖/金轨迹符号,统计量落实测带内即过(**带内**
    不是「贴近」——贴脸=过拟合警报,迁移审计 w186(git 历史) §6);真值 run 是旧策略
    病局,sim 跑当前策略,决策层差异 expected,锚只锁结算与经济层。
    """
    # 会话随机流从局 seed 派生(w910_sim_determinism/REPORT,与 engine_p1
    # 构造点同契约):禁裸 StrategySession() 的 OS 熵默认入 sim。
    sess = StrategySession(rng=random.Random(f'sim-p2-entry-{seed}'))
    if entry.locked_comp:
        from sr_od.application.currency_war.kernel.cw_comps import COMP_LIBRARY
        from sr_od.application.currency_war.strategies.impl.mandate_v1.mandate_state import (
            state_of,
        )
        if entry.locked_comp in COMP_LIBRARY:
            # 锁定线经状态对象注入(session.md §3.4:策略状态不在 session,
            # 禁裸 setattr;simulate_p1 侧 ensure_strategy_state 见已有
            # 状态对象不覆写,注入保留)。
            state_of(sess).target_comp = COMP_LIBRARY[entry.locked_comp]
    return simulate_p1(seed, use_refresh=use_refresh, pool=pool,
                       session=sess, p2_combat=p2_combat,
                       _p2_entry=entry)

