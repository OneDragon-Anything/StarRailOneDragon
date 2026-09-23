"""P97 刷新预算上限·计算脚本(math_proofs P97)。

命题:全连胜收入日程(效率折扣 η)− 目标等级升级开销 − 终局阵容购置成本
= 可自由支配刷新预算;除以刷新基价 = 刷新次数。判据 = 阈值刷新环境
(长线利好 30 次付费刷新/二手市场 20 次总刷新)的可达性。

口径(全部注册表/文档直读,出处见 proofs/p97-refresh-budget.md):
- 节点日程:economy.md §10.2(P1/P2 实测;P3=9 节点、r9 boss 为结构先验【拟】)
- 轮首收入 = reward_base_gold(基础奖励,P1 r1=3/r2=4 其余 5)
            + streak_gold(连胜金,6+ 封顶 4)+ interest(息,min(g//10,5))
- η 辖基础+连胜分量(运营收入折扣);利息按金轨迹现算
- 连胜计数控:战斗/遭遇/boss 胜 +1;奖励轮照发不动计数;补给轮零连胜金
- 节点经验(M08):战斗/奖励/遭遇 +2、补给 0、boss +12
- 升级开销 = (目标等级所需 XP − 节点白送 XP)÷4 XP/击 × 4 金/击
- 阵容购置 = core_chars(按 level_plan star_goals 最高星,缺省 1★)
            + shared_chars(1★,与 core 去重)——低估申报:板面弹性位不计
- 未计入收入(结果 = 保守下限,见证明文档「未入账项」节):
  奖励节点额外金/补给角色金等价/遭遇奖励金等价

跑法:PYTHONPATH=src python tools/cw/proofs/p97_refresh_budget_check.py
"""
from __future__ import annotations

import sys

from sr_od.application.currency_war.data.cw_chars import CHARACTERS
from sr_od.application.currency_war.kernel.cw_comps import COMP_LIBRARY
from sr_od.application.currency_war.kernel.cw_economy import (
    DEFAULT_INTEREST_CAP,
    XP_PER_BUY,
    XP_TO_NEXT_LEVEL,
    interest,
    reward_base_gold,
    streak_gold,
)
from sr_od.application.currency_war.kernel.cw_vocab import REFRESH_COST_BASE

# ===== 节点日程(economy.md §10.2;P3 = 结构先验【拟】,单篇申报)=====
NODE_SCHEDULE: list[tuple[int, int, str]] = (
    [(1, r + 1, t) for r, t in enumerate(
        ['reward', 'reward', 'battle', 'battle', 'supply',
         'battle', 'encounter', 'reward', 'boss'])]
    + [(2, r + 1, t) for r, t in enumerate(
        ['battle', 'battle', 'encounter', 'reward',
         'encounter', 'reward', 'boss'])]
    + [(3, r + 1, t) for r, t in enumerate(
        ['battle', 'battle', 'battle', 'battle', 'battle',
         'battle', 'battle', 'battle', 'boss'])]
)

#: 节点经验表(M08,依据 xp-rules.md;sim/cw_sim_backend.py NODE_XP_BY_TYPE 同源)
NODE_XP: dict[str, int] = {
    'battle': 2, 'encounter': 2, 'reward': 2, 'supply': 0, 'boss': 12,
}

#: 效率折扣(用户裁定 2026-09-23:0.8,【拟】,实机可校准)
ETA: float = 0.8

#: 开局态(u07u28 定案:sim/cw_sim_opening OPENING_GOLD/LEVEL 同源)
OPENING_GOLD: int = 3
OPENING_LEVEL: int = 3


def star_copies(star: int) -> int:
    """n 星单位所需 1★ 副本数(合成规则:2★=3、3★=9)。"""
    return {1: 1, 2: 3, 3: 9}[star]


def simulate_income(eta: float) -> tuple[int, int, list[str], list[int]]:
    """全连胜收入日程推演。返回 (总收入, 节点白送 XP 合计, 明细行, 金轨迹)。"""
    gold = OPENING_GOLD
    streak = 0
    xp_total = 0
    income_total = 0
    lines: list[str] = []
    golds: list[int] = []
    for plane, rnd, ntype in NODE_SCHEDULE:
        base = reward_base_gold(plane, rnd)
        if ntype == 'supply':
            streak_pay = 0            # 补给轮:连胜不动、零连胜金
        else:
            streak_pay = streak_gold(streak)
            if ntype != 'reward':     # 奖励轮照发不动计数;战斗/遭遇/boss +1
                streak += 1
        interest_pay = interest(gold, DEFAULT_INTEREST_CAP)
        income = round(eta * (base + streak_pay)) + interest_pay
        gold += income
        income_total += income
        xp_total += NODE_XP[ntype]
        golds.append(gold)
        lines.append(
            f'  P{plane}-r{rnd} {ntype:<9} base={base} streak={streak_pay} '
            f'interest={interest_pay} income={income} gold={gold} xp+={NODE_XP[ntype]}')
    return income_total, xp_total, lines, golds


def level_up_cost(target_level: int, free_xp: int) -> tuple[int, int]:
    """升级到 target_level 的买经验金开销。返回 (金开销, 需购 XP)。"""
    need_xp = sum(xp for lv, xp in XP_TO_NEXT_LEVEL.items()
                  if OPENING_LEVEL <= lv < target_level)
    buy_xp = max(0, need_xp - free_xp)
    clicks = -(-buy_xp // XP_PER_BUY)          # 向上取整
    return clicks * 4, buy_xp                  # 4 金/击(按钮实读缺省口径)


def comp_cost(comp) -> tuple[int, int, dict[str, int]]:
    """阵容购置成本。返回 (总成本, 目标等级, 逐角色明细)。"""
    star_goals: dict[str, int] = {}
    target_level = 0
    for level, goal in (comp.level_plan or {}).items():
        target_level = max(target_level, int(level))
        for char, star in (getattr(goal, 'star_goals', None) or {}).items():
            star_goals[char] = max(star_goals.get(char, 1), int(star))
    total = 0
    detail: dict[str, int] = {}
    seen: set[str] = set()
    for char in list(comp.core_chars) + list(comp.shared_chars):
        if char in seen:
            continue
        seen.add(char)
        ch = CHARACTERS.get(char)
        if ch is None:
            detail[f'{char}(注册表缺)'] = 0
            continue
        star = star_goals.get(char, 1)
        cost = star_copies(star) * ch.cost
        detail[f'{char}@{star}★'] = cost
        total += cost
    return total, max(target_level, OPENING_LEVEL + 1), detail


def main() -> int:
    print(f'节点数 = {len(NODE_SCHEDULE)};开局金 {OPENING_GOLD}/等级 '
          f'{OPENING_LEVEL};息帽 {DEFAULT_INTEREST_CAP};刷新基价 {REFRESH_COST_BASE}')
    print(f'η = {ETA}(用户裁定 2026-09-23;【拟】可实机校准)')

    income_eta1, free_xp, lines_eta1, golds_eta1 = simulate_income(1.0)
    income, free_xp_eta, lines, _ = simulate_income(ETA)
    assert free_xp == free_xp_eta, 'XP 不随 η 变(η 只辖收入分量)'
    print('\n— 收入日程(η=1 上限口径)—')
    print('\n'.join(lines_eta1))
    print(f'\n收入合计:η=1 上限 = {income_eta1};η={ETA} = {income}')
    print(f'节点白送 XP 合计 = {free_xp}')
    # 结构锚:满息达成(η=1 下第 7 轮金 ≥ 50)/η 折扣方向
    assert income_eta1 > income > 0, 'η 折扣方向'
    assert any(g >= 50 for g in golds_eta1[:7]), 'η=1 下前 7 轮内满息'

    print(f'\n— 逐阵容预算(目标等级 = level_plan 顶格;η={ETA})—')
    header = (f'{"阵容":<10}{"强度":<4}{"目标级":<5}{"购置":<6}'
              f'{"升级":<6}{"预算":<6}{"刷新次数":<8}{"≥30":<4}{"≥20"}')
    print(header)
    rows: list[tuple[str, int, int, int, int]] = []
    for comp in COMP_LIBRARY:
        cost, target_level, _detail = comp_cost(comp)
        lvl_cost, buy_xp = level_up_cost(target_level, free_xp)
        budget = income - lvl_cost - cost
        refreshes = budget // REFRESH_COST_BASE
        rows.append((comp.name, target_level, cost, lvl_cost, refreshes))
        print(f'{comp.name:<10}{comp.strength:<4}{target_level:<7}{cost:<8}'
              f'{lvl_cost:<8}{budget:<8}{refreshes:<10}'
              f'{"✓" if refreshes >= 30 else "✗":<4}'
              f'{"✓" if refreshes >= 20 else "✗"}')

    counts = [r[4] for r in rows]
    avg = sum(counts) / len(counts)
    print(f'\n均值 = {avg:.1f} 次;最大 = {max(counts)};最小 = {min(counts)}')
    ge30 = sum(1 for c in counts if c >= 30)
    ge20 = sum(1 for c in counts if c >= 20)
    print(f'达长线利好阈值(≥30 次付费刷新):{ge30}/{len(counts)} 条阵容;'
          f'达二手市场阈值(≥20 次):{ge20}/{len(counts)}')

    # 检验锚:均值非负且停 9 级口径下阈值可达面非零(证明文档数字表锚)
    assert avg > 0, '预算均值为正(未入账收入只增不减,0 = 结构性错)'
    assert ge20 > 0, '二手市场阈值至少在部分阵容可达'
    return 0


if __name__ == '__main__':
    sys.exit(main())
