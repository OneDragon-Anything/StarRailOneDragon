"""sim 账本异常断言(②;实机学费的回灌载体)。

设计定谳(两轮对抗审查):
- **纯函数**:吃账本 dict 列表(每局 = 逐轮行列表),不 import
  cw_sim——依赖方向 = 调用方(simulate_p1_batch/CLI)跑完把账本
  传进来(二轮#7,非模块级 import 不构成循环);
- **分布级预警在 batch 内嵌**(默认开,--checks False 关);
  确定性回归走测试仓合成账本双向锁(检查逻辑本身的锁);
- **局49 指纹断言只对构造账本跑**(check_coldstart_seed_
  squander):sim 开局 bench 先填 4 张已知阵营卡 → r368 冷启动
  门在 sim 内不可达(二轮#3),跑 sim 批次 = 空转/随机误报;
  faction='?' 开局模拟模式是单独立项。

每条检查的 docstring 记来源局号/指纹(学费账本;ADR 见对应条目)。
"""
from __future__ import annotations

# 冷启动方向件白名单(r368 门语义:classify_buy label 集)
_COLDSTART_OK = frozenset({'bridge_seed', 'engine'})


def check_ledger_consistency(rows: list[dict]) -> list[str]:
    """账本内部一致性(锁账本本身没写坏;generic,sim 批量内嵌)。

    逐轮守恒:gold == gold_before + income合计 − (buys+levelup+
    refresh) + sell_income。违例 = 账本记录 bug(非策略病)——
    先修账本再谈策略判读。
    """
    out: list[str] = []
    for row in rows:
        s = row.get('sim') or {}
        gb = s.get('gold_before')
        inc = s.get('income') or {}
        sp = s.get('spend') or {}
        if gb is None:
            out.append(f"r{row.get('round_num')}: 缺 gold_before")
            continue
        expect = (gb + sum(inc.values())
                  - sum((sp.get('buys') or {}).values())
                  - sp.get('levelup', 0) - sp.get('refresh', 0)
                  + sp.get('sell_income', 0))
        if row.get('gold') != expect:
            out.append(
                f"r{row.get('round_num')}: 金不守恒 "
                f"{row.get('gold')} != {expect}(gb={gb})")
    return out


def check_coldstart_seed_squander(rows: list[dict]) -> list[str]:
    """局49 指纹(首条回灌断言;ADR-0240;r368 修前形态)。

    指纹:r1 无方向(target_comp 空)时,买入含白名单外标签
    (off/pair/board_focus/emergency/swap/plan/unknown)——冷启动
    首购只放行桥名单∪引擎(r368 门),violation 即旧病形态。
    **只对构造账本跑**:sim 内冷启动门不可达(见模块 docstring)。
    """
    out: list[str] = []
    for row in rows:
        if row.get('round_num') != 1:
            continue
        if row.get('target_comp'):
            continue   # 已有方向,非冷启动形态
        for a in row.get('actions') or []:
            if a.get('__type__') != 'BuyCard':
                continue
            reason = a.get('reason') or 'unknown'
            if reason not in _COLDSTART_OK:
                name = (a.get('card') or {}).get('name') or a.get('name')
                cost = (a.get('card') or {}).get('cost') or a.get('cost')
                out.append(
                    f"r1 冷启动买入非方向件: {name}"
                    f"(reason={reason}, cost={cost})")
        return out   # 只查 r1
    return out


# 批量内嵌的 generic 检查集(分布级;局49 类构造检查不在此列)
_BATCH_CHECKS = {
    'ledger_consistency': check_ledger_consistency,
}


def run_checks_on_ledgers(ledgers: list[list[dict]]) -> dict[str, dict]:
    """批量执行 generic 检查 → {检查名: {violations: n, games: [idx...]}}。

    违规局数与前 5 个局索引(供 seed 重放定位:simulate_p1(
    seed_base+idx) 重放该局)。
    """
    report: dict[str, dict] = {}
    for name, fn in _BATCH_CHECKS.items():
        games: list[int] = []
        for idx, rows in enumerate(ledgers):
            if fn(rows):
                games.append(idx)
        report[name] = {
            'violations': len(games),
            'games': games[:5],
        }
    return report
