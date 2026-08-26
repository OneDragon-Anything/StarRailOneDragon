"""货币战争 bench 装备 tracking 单一源 + 对账断言(契约包 C6 契约 2,冻结决定;W38)。

**裁定背景(W21 #17)**:画面机制上未上阵角色不显示装备 icon(机制盲区,非识别
缺陷)→ **bot tracking 记账(``BenchChar.equips`` / ``GameState.equips`` owned 池)
是 bench 装备的单一源**,不建 bench 槽详情 reader(``read_bench_slot_detail``
仅漂移恢复预留接口,草案级不承诺实现)。

**对账义务(冻结)**:
1. ``assert_equips_consistency``:动作执行前,动作对象的账面 equips 与**画面可读面**
   (deployed 侧 below-avatar icon 可读;bench 侧机制不可读 → 无对拍面,直接信账)
   交叉校验,不一致 raise ``EquipsInconsistencyError``(调用方按哨兵协议留证,
   禁静默用账——卖错装的件 = 替换方案一次敲定的直接错误输入);
2. ``equips_ledger_multiset`` / ``assert_ledger_conserved``:动作前后的装备守恒
   对账(assigned = bench+deployed 各 char 的 equips;pool = ``state.equips``;
   装备只随人走/卖出回收,动作前后多重集必须相等)。挂点 = ``cw_state.simulate``
   的 BuyCard/SellBench/SellDeployed/SwapDeploy/CompTransaction 分支后
   (mismatch 记 action_log,checks/遥测可见,不静默)。

**演进引擎 v1 不消费 bench 装备**(契约包六矛盾 leader 裁决 6):替换决策按
角色身份+羁绊档判断,装备只随人走——本模块只做记账+对账,**不进决策**。
"""
from __future__ import annotations

from collections import Counter

from sr_od.application.currency_war.cw_state import BenchChar, GameState


class EquipsInconsistencyError(RuntimeError):
    """账面 equips 与画面可读面交叉校验不一致(C6 对账;禁静默用账)。"""

    def __init__(self, char_desc: str, ledger: list[str], visible: list[str],
                 source: str):
        self.char_desc = char_desc
        self.ledger = list(ledger)
        self.visible = list(visible)
        self.source = source
        super().__init__(
            f'[{source}] equips 对账不一致: char={char_desc} '
            f'账面={sorted(ledger)} 画面={sorted(visible)}')


#: 对账异常元组(R4-2 §3.2 单点化:消费方 except 本元组,新增对账异常
#: 只改这里)
EQUIPS_CONSISTENCY_ERRORS: tuple[type[BaseException], ...] = (
    EquipsInconsistencyError,)


def wear_synthesis_equivalent(ledger: list[str], visible: list[str]) -> bool:
    """**穿着触发自动合成**的账面↔画面等价判定(W209e 取证实锤,ADR-0387)。

    游戏机制(run 26 现场):角色**穿着的两件基础件若恰为某进阶配方组件**
    (交叉两件不同/自配同件×2)→ 画面自动合成显示该进阶——
    账面 [量产型装甲×2] ↔ 画面 [很硬的甲](SELF_RECIPES);
    账面 [光能电池,生命之花] ↔ 画面 [绝对热量](CROSS/GUANGNENG)。
    我们的 tracking 不建模该行为 → 旧对账把已知形态误报不一致。

    判定:账面多重集经**任意次**配方替换(每次两组件 → 一进阶,件数 −1)
    能否到达画面多重集(闭包搜索;ledger ≤6 件,搜索空间极小)。
    """
    if not ledger or not visible:
        return False
    from sr_od.application.currency_war import cw_synthesis as _syn

    def _reach(cur: Counter) -> bool:
        if cur == Counter(visible):
            return True
        names = list(cur)
        # 自配:同件 ×2 → 进阶
        for n in names:
            if cur[n] >= 2:
                adv = _syn.self_advance(n)
                if adv:
                    nxt = cur - Counter({n: 2})
                    nxt[adv] += 1
                    if _reach(nxt):
                        return True
        # 交叉:两件不同 → 进阶
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                adv = _syn.synthesize_target(names[i], names[j])
                if adv:
                    nxt = cur - Counter({names[i]: 1, names[j]: 1})
                    nxt[adv] += 1
                    if _reach(nxt):
                        return True
        return False

    return _reach(Counter(ledger))


def assert_equips_consistency(char: BenchChar, visible: list[str] | None,
                              source: str) -> None:
    """动作前对账(契约 C6 草案签名 + ``visible`` 可读面参数,草案级细化)。

    - ``visible=None``:该侧画面机制不可读(bench 侧盲区,W21 #17)→ 无对拍面,
      单一源 = tracking 账面,直接通过(C6 裁定的本意);
    - ``visible`` 非 None:deployed 侧 below-avatar icon 真读 → 与账面
      ``char.equips`` 多重集比对,不一致 raise(多重集 = 同名装备可重复持有);
    - **穿着合成等价豁免**(W209e/ADR-0387):多重集不等但
      :func:`wear_synthesis_equivalent`(账面组件经配方替换到达画面)→ 视为
      一致不 raise——调用方的画面真值覆盖逻辑照常把账面纠正为画面形态
      (合成不可逆,画面即最新真值)。
    """
    if visible is None:
        return
    ledger = list(getattr(char, 'equips', None) or [])
    if Counter(ledger) != Counter(visible) \
            and not wear_synthesis_equivalent(ledger, visible):
        raise EquipsInconsistencyError(
            char_desc=f'{getattr(char, "char_id", "") or "?"}'
                      f'@{getattr(char, "position_pref", "?")}',
            ledger=ledger, visible=visible, source=source)


def equips_ledger_multiset(bench: list[BenchChar], deployed: list[BenchChar],
                           pool: list[str]) -> Counter:
    """装备账本全景多重集:assigned(bench+deployed 各 char.equips)+ owned 池。"""
    out: Counter = Counter()
    for c in list(bench or []) + list(deployed or []):
        out.update(getattr(c, 'equips', None) or ())
    out.update(pool or ())
    return out


def state_equips_multiset(state: GameState) -> Counter:
    """GameState 侧账本全景(对账快照入口)。"""
    return equips_ledger_multiset(state.bench, state.deployed, state.equips)


def ledger_mismatch(before: Counter, after: Counter) -> list[str]:
    """两份账本快照的差异清单(空 = 守恒;'装备凭空消失/出现'逐条列出)。"""
    diffs: list[str] = []
    for k in sorted(set(before) | set(after)):
        d = after.get(k, 0) - before.get(k, 0)
        if d > 0:
            diffs.append(f'{k}:+{d}(凭空出现)')
        elif d < 0:
            diffs.append(f'{k}:{d}(凭空消失)')
    return diffs


def assert_ledger_conserved(before: Counter, after: Counter,
                            source: str) -> list[str]:
    """装备守恒断言(动作后对账):不一致 **raise**(测试/离线对账用);
    返回值 = 空清单(守恒)。sim 挂点侧用 ``ledger_mismatch`` 走账本记录不 raise。"""
    diffs = ledger_mismatch(before, after)
    if diffs:
        raise EquipsInconsistencyError(
            char_desc='<ledger>', ledger=[], visible=[],
            source=f'{source}|ledger_drift:{",".join(diffs)}')
    return diffs
