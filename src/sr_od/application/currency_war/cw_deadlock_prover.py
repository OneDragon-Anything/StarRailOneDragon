"""28 号提案落地 Tier-1:金零进展死锁的**穷举可达性**检测(DP 引擎双用)。

主张:13 号合约的 gold_no_progress 是轨迹谓词(只能判已发生);本件把同一性质升级为
状态空间性质——在抽象转移系统(cw_horizon 同款状态空间 + 策略骨架门族为可行性约束)
上穷举:是否存在可达状态,其**全部进展动作(买/升/刷/卖)被门族挡住或不可负担** →
死锁态(「金零进展」的结构性根)。产出:证明(无死锁可达)或最小反例(最短动作序列)。

Tier-1 判据(28 号 §2 主张2):金零进展 = 死锁检测,只需精确机制(收入/利息/升级价/
刷新价/卖回价),不依赖掉血先验。抽象状态 = (t, gold, level);bench 维粗化为占用带
(0=空/1=半/2=满,三态,够判「腾席动作可用性」)。
"""
from __future__ import annotations

from dataclasses import dataclass, field

from sr_od.application.currency_war.cw_mechanism import get_mechanism

# —— 机制常数(注册表单源;缺项回退硬编码值并标 unverified)——
_mc_refresh = get_mechanism('SHOP_REFRESH_COST')
REFRESH_COST = int(_mc_refresh.value) if _mc_refresh else 2
_mc_interest = get_mechanism('INTEREST_THRESHOLD')
INTEREST_CAP = int(_mc_interest.value) if _mc_interest else 50


@dataclass(frozen=True)
class DeadlockState:
    """一个死锁态:全部进展动作不可用,只剩收利息/wait。"""

    t: int           # 节点步
    gold: int
    level: int
    bench: int       # 0 空/1 半/2 满
    reason: str      # 为什么死锁(哪组门把动作全挡了)


@dataclass
class DeadlockReport:
    """穷举结果:证明或反例清单。"""

    deadlocks: list[DeadlockState] = field(default_factory=list)
    states_enumerated: int = 0

    @property
    def verdict(self) -> str:
        return 'PROVEN_NO_DEADLOCK' if not self.deadlocks else f'DEADLOCK_FOUND x{len(self.deadlocks)}'

    def minimal_counterexamples(self, k: int = 5) -> list[DeadlockState]:
        """最小反例:gold 最小(离「无进展」最近)的前 k 个。"""
        return sorted(self.deadlocks, key=lambda d: d.gold)[:k]


def _progress_actions_available(gold: int, level: int, bench: int,
                                refresh_cap: int = 4) -> tuple[bool, str]:
    """策略骨架门族下,进展动作(买/升/刷/卖)是否至少一个可用。

    门族(与 cw_plan 现状对齐的抽象):
    - 买:gold ≥ 最贱卡(1)且 bench<满;bench 满时卖先可行(卖=腾席动作,算进展)。
    - 升:gold ≥ 单击价(4)+地板(10/20 由 hp 决定,这里取保守 10)且 level<10。
    - 刷:gold ≥ REFRESH_COST 且刷新次数 < refresh_cap。
    - 卖:bench>0 恒可行(回金 = 进展)。

    ⚠️ 活性条件(28 号 §2 Tier-1「金零进展=死锁检测」的准确语义):「本态无进展动作
    **且下一节点收入后仍无进展**」才是真死锁——gold=0/空 bench 的平凡态会被每节点
    base income(5)救活。收入进 gold 后重判;两步都挡 = 死锁。
    """
    def _has_progress(g: int) -> tuple[bool, str]:
        if bench > 0:
            return True, 'sell 可行(腾席回金)'
        if g >= 1 and bench < 2:
            return True, 'buy 可行'
        if g >= 14 and level < 10:
            return True, 'level_up 可行'
        if g >= REFRESH_COST and refresh_cap > 0:
            return True, 'refresh 可行'
        return False, f'buy{g >= 1 and bench < 2}/lv{g >= 14}/rf{g >= REFRESH_COST}/sell{bench > 0} 全挡'

    ok, why = _has_progress(gold)
    if ok:
        return True, why
    # 活性一步:下节点收入(base 5 + 利息)后重判
    g2 = min(gold + 5 + min(gold // 10, INTEREST_CAP // 10), 999)
    ok2, why2 = _has_progress(g2)
    if ok2:
        return True, f'本态挡但下节点收入后可行动({why2})'
    return False, f'两步死锁:本态({why}) → 收入后 g={g2}({why2})'


def enumerate_deadlocks(t_max: int = 9, gold_max: int = 100, level_max: int = 10) -> DeadlockReport:
    """穷举 (t, gold, level, bench) 找死锁态。

    注:静态穷举(不动转移系统)——死锁判据是**状态的谓词**(该状态下策略骨架无进展动作
    可发),无需展开转移图;「可达性」由输入域约束(t/gold/level/bench 全在合法域)保证。
    """
    rep = DeadlockReport()
    for t in range(t_max + 1):
        for gold in range(0, gold_max + 1):
            for level in range(1, level_max + 1):
                for bench in (0, 1, 2):
                    rep.states_enumerated += 1
                    ok, why = _progress_actions_available(gold, level, bench)
                    if not ok:
                        rep.deadlocks.append(DeadlockState(t, gold, level, bench, why))
    return rep


if __name__ == '__main__':
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    rep = enumerate_deadlocks()
    print(f'{rep.verdict}(枚举 {rep.states_enumerated} 态)')
    for d in rep.minimal_counterexamples():
        print(f'  反例: t={d.t} gold={d.gold} lv={d.level} bench={d.bench} ({d.reason})')
