"""deploy 选人纯逻辑(sim 与 DeployBench op 共用单一源;r389/r390)。

背景(2026-08-23 用户定调「这些问题明明都可以模拟发现」):局53-62
实机暴露的 deploy 侧 bug(r373 桥期 target 真空/r387 cap 富余仍拦
散牌)全是 **DeployBench op 的选人围栏**行为——而 sim 的 deployed
是自动代理(bench 引擎件直进,围栏零覆盖),执行层 bug 天然测不出。

本模块把围栏判定提取为**纯函数**(无 ctx/无画面/无 SIFT):输入
bench/deployed/目标集/围栏集/cap,输出「谁上场」。DeployBench op
与 cw_sim 都调它——同一份逻辑,实机改=sim 改,漂移不可能。

注意:op 侧还有画面依赖部分(SIFT 读身份/槽位坐标/drag 验证),
那些留在 op;这里只收**纯决策**。输入的 bench 用 BenchChar,
身份可判(char_id 空串=未识别,围栏语义「照旧上」保留)。
"""
from __future__ import annotations

from sr_od.application.currency_war.cw_chars import CHARACTERS
from sr_od.application.currency_war.cw_line_defs import (
    ENGINE_FACTIONS,
    RECIPE_BASE,
    RECIPE_FACTIONS,
)
from sr_od.application.currency_war.cw_state import BenchChar


def _bonds_of(bc: BenchChar) -> set[str]:
    """角色全羁绊(factions+flows);未识别/未注册 → 空集。"""
    cid = getattr(bc, 'char_id', '') or ''
    ch = CHARACTERS.get(cid) if cid else None
    if ch is None:
        return set()
    return set(ch.factions) | set(ch.flows)

# 与 op 侧同源(r357:RECIPE ∪ ENGINE 桥派生集)
DEPLOY_FENCE: frozenset[str] = frozenset(RECIPE_FACTIONS | ENGINE_FACTIONS)


def cap_roomy_of(front_empty: int, back_empty: int, must_up: int) -> bool:
    """r387:cap 是否富余(空位 > 必上件数)。富余=散牌填空不稀释。"""
    return (front_empty + back_empty) > must_up


def tier_completes(bonds, deployed_fac: dict[str, int]) -> int:
    """r361 补档键:上阵后任一阵营恰达激活档 → 1,否则 0。"""
    from sr_od.application.currency_war.cw_factions import FACTIONS
    for _f in bonds:
        _now = (deployed_fac.get(_f, 0) or 0) + 1
        if _now in (FACTIONS.get(_f).tiers if FACTIONS.get(_f) else ()):
            return 1
    return 0


def select_deployments(
    bench: list[BenchChar],
    deployed_cids: set[str],
    deployed_fac: dict[str, int],
    board: dict[str, int],
    cap: int,
    front_total: int = 4,
    back_total: int = 6,
    target_factions: frozenset[str] | set[str] = frozenset(),
    target_cores: frozenset[str] | set[str] = frozenset(),
    fw_carry: frozenset[str] | set[str] = frozenset(),
) -> tuple[list[int], list[int]]:
    """围栏判定:返回 (上场 bench 下标序, 留 bench 下标)。

    语义与 DeployBench op 的 deterministic 段逐条对应
    (ADR-0130 散牌围栏/r361 补档序/r251 引擎对优先/r387 cap 富余
    填空/板空保底),唯一省略:SIFT 未识别(char_id 空)照旧上
    ——调用方传空 char_id 即走该分支。
    cap 语义 = 已 deployed 数 + 本轮上场数 ≤ cap(cap=None 不限,
    调用方传大数)。
    """
    vacancy = front_total + back_total - len(deployed_cids)
    vacancy = max(vacancy, 0)

    tgt_idx: list[int] = []
    rest: list[int] = []
    bench_fac: dict[int, str] = {}
    pair_counts: dict[str, int] = dict(board)
    for i, bc in enumerate(bench):
        cid = getattr(bc, 'char_id', '') or ''
        ch = CHARACTERS.get(cid) if cid else None
        bonds: set[str] = set()
        if ch is not None:
            bonds = set(ch.factions) | set(ch.flows)
            if ch.factions:
                bench_fac[i] = ch.factions[0]
                pair_counts[ch.factions[0]] = pair_counts.get(ch.factions[0], 0) + 1
        is_tgt = bool(bonds & set(target_factions)) or cid in target_cores \
            or cid in fw_carry
        (tgt_idx if is_tgt else rest).append(i)
    tgt_idx.sort(key=lambda i: tier_completes(
        _bonds_of(bench[i]), deployed_fac), reverse=True)

    held: list[int] = []
    fill_mode = vacancy > 2
    board_recipe = sum(v for k, v in board.items() if k in RECIPE_FACTIONS)
    recipe_starved = board_recipe < RECIPE_BASE
    must_up = len(tgt_idx) + sum(
        1 for i in rest
        if bench_fac.get(i) is not None
        and pair_counts.get(bench_fac[i], 0) >= 2)
    roomy = cap_roomy_of(vacancy, 0, must_up)
    for i in list(rest):
        cid = getattr(bench[i], 'char_id', '') or ''
        if not cid:
            continue    # 未识别:照旧上(围栏无法判)
        f = bench_fac.get(i)
        if f is not None and f not in DEPLOY_FENCE \
                and recipe_starved and not roomy:
            rest.remove(i)
            held.append(i)
            continue
        if f is not None and pair_counts.get(f, 0) >= 2:
            continue    # 成对:上
        if fill_mode:
            continue    # 人口扩展期:散牌填位
        rest.remove(i)
        held.append(i)
    board_empty = len(deployed_cids) == 0
    if board_empty and not tgt_idx and not rest and held:
        rest.append(held.pop(0))   # 板空保底:上 1 个
    # r251:引擎 pair 优先(cap 竞争时先到先得)
    _ENGINE = {'仙舟', '列车同行', '持续伤害'}
    rest.sort(key=lambda i: 0 if (bench_fac.get(i) in _ENGINE
                                  or _bonds_of(bench[i]) & _ENGINE) else 1)
    order = tgt_idx + rest
    # cap 截断(动态停语义:超 cap 的留 bench)
    up: list[int] = []
    for i in order:
        if len(deployed_cids) + len(up) >= cap:
            held.append(i)
            continue
        cid = getattr(bench[i], 'char_id', '') or ''
        if cid and cid in deployed_cids:
            continue    # 去重(5.1.7)
        up.append(i)
    return up, held
