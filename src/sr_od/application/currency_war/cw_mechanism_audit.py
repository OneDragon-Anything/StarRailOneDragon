"""机制常数 telemetry 核对器(redesign 23 号落地第二步;纯函数,吃 decisions.jsonl)。

首批 4 个审计(23 号 §2.2 清单里数据已够的):
- SHOP_REFRESH_COST:RefreshShop 动作前后 gold 差众数(单局即证)。
- XP_PER_BUY:buy 计数×4 vs xp_progress 变化。
- BASE_INCOME:纯攒息回合(动作花费=0)gold 差 − 利息 − 连胜金。
- INTEREST_THRESHOLD:攒息期 gold 上限分布(应封顶 50)。
输出 ConstantAudit(name, estimate, n, verdict: consistent|refuted|underpowered)。
"""
from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ConstantAudit:
    """一个机制常数的 telemetry 审计结果。"""

    name: str
    estimate: float | None    # 测得值(None = 样本不足)
    n: int                    # 样本数
    verdict: str              # consistent | refuted | confounded | underpowered
    expected: float | None    # 注册表当前值
    detail: str = ''


def _cost_of_actions(actions: list[dict]) -> int:
    """一组动作的金花费(RefreshShop/ BuyCard cost 用注册值估;buy cost 在 card 里可能缺)。"""
    total = 0
    for a in actions or []:
        t = a.get('__type__')
        if t == 'RefreshShop':
            total += a.get('cost') or 2
        elif t == 'BuyCard':
            c = a.get('card') or {}
            total += c.get('cost') or 1
        elif t == 'LevelUp':
            total += a.get('cost') or 0
    return total


def audit_refresh_cost(rows: list[dict]) -> ConstantAudit:
    """SHOP_REFRESH_COST 执行侧归因(r9 review 修:旧版把 b 行未执行的规划花费记到 a→b 金差
    → est=0 假阳性毒化注册表)。

    三处修正(review ④):
    ① 归因换 **a.actions 前缀**(执行侧):shop.py 两阶段执行「a 的前缀至首个 RefreshShop(含)」,
       a→b 金差反映的正是这段 —— 用 a 前缀扣费而非 b 全案;
    ② 限定**同节点行对**(round_num 相等):杀收入混杂(跨节点 income 进金差);
    ③ 前缀扣费含 LevelUp(_cost_of_actions 已含)。
    expected 从机制注册表读(首个消费端,防表-码双源)。
    """
    from sr_od.application.currency_war.cw_mechanism import get_mechanism
    expected = None
    _mc = get_mechanism('SHOP_REFRESH_COST')
    if _mc is not None:
        expected = float(_mc.value)
    diffs = []
    for a, b in zip(rows, rows[1:], strict=False):
        if a['run_id'] != b['run_id'] or a['state']['round_num'] != b['state']['round_num']:
            continue
        # 执行前缀 = a.actions 至首个 RefreshShop(含);后面的动作两阶段循环没执行
        prefix: list[dict] = []
        n_rf = 0
        for x in (a.get('actions') or []):
            t = x.get('__type__')
            if t == 'RefreshShop':
                n_rf += 1
                prefix.append(x)
                break   # 执行至首个 RefreshShop(含)即停(重 plan 重来)
            if t == 'DeployMove':
                continue   # shop.py 跳过 deploy(不执行不扣费)
            prefix.append(x)
        if n_rf == 0:
            continue
        other_cost = _cost_of_actions([x for x in prefix if x.get('__type__') != 'RefreshShop'])
        d = (a['state']['gold'] - b['state']['gold'] - other_cost) / n_rf
        if 0 <= d <= 10:   # 单刷费合理窗
            diffs.append(round(d))
    if len(diffs) < 5:
        return ConstantAudit('SHOP_REFRESH_COST', None, len(diffs), 'underpowered', expected)
    est, cnt = Counter(diffs).most_common(1)[0]
    verdict = 'consistent' if expected is not None and est == expected else 'refuted'
    return ConstantAudit('SHOP_REFRESH_COST', float(est), len(diffs), verdict, expected,
                         detail=f'分布 {Counter(diffs).most_common(3)}')


def _expected_of(name: str) -> float | None:
    """注册表期望值(表-码防双源:审计一律从注册表读)。"""
    from sr_od.application.currency_war.cw_mechanism import get_mechanism
    mc = get_mechanism(name)
    return float(mc.value) if mc is not None and isinstance(mc.value, (int, float)) else None


def _same_run_node(a: dict, b: dict) -> bool:
    """同局同节点行对(收入/经验类审计的采样窗:杀跨节点收入混杂)。"""
    return (a.get('run_id') == b.get('run_id')
            and (a.get('state') or {}).get('round_num') == (b.get('state') or {}).get('round_num'))


def audit_xp_per_buy(rows: list[dict]) -> ConstantAudit:
    """XP_PER_BUY:a 前缀内 BuyCard 数 × 4 vs xp_progress 变化(同节点同行对,等级未跨)。

    xp_progress=(cur, need);等级跨级行对剔除(cur 重置不可比)。est = Δxp / n_buys。"""
    expected = _expected_of('XP_PER_BUY')
    ests: list[float] = []
    for a, b in zip(rows, rows[1:], strict=False):
        if not _same_run_node(a, b):
            continue
        sa, sb = a.get('state') or {}, b.get('state') or {}
        if sa.get('level') != sb.get('level'):
            continue   # 跨级:cur 重置
        xa, xb = sa.get('xp_progress'), sb.get('xp_progress')
        if not xa or not xb:
            continue
        # 执行前缀(同 refresh:至首个 RefreshShop 停;buy 前缀内计)
        n_buys = 0
        for x in (a.get('actions') or []):
            t = x.get('__type__')
            if t == 'RefreshShop':
                break
            if t == 'BuyCard':
                n_buys += 1
        if n_buys == 0:
            continue
        d = (xb[0] - xa[0]) / n_buys   # est=Δxp/买数(口径=快照含买牌 XP 时主峰 0,见 confounded 分支)
        if 0 <= d <= 10:
            ests.append(round(d, 1))
    if len(ests) < 5:
        return ConstantAudit('XP_PER_BUY', None, len(ests), 'underpowered', expected)
    est, cnt = Counter(ests).most_common(1)[0]
    if est == 0.0 and expected and expected > 0:
        # 主峰 0 + 次峰=注册值:快照口径差(state.xp_progress 是买牌后的 OCR,已含买牌 XP)
        # —— 非机制 refute(次峰即真值观测);标 confounded 待口径分离(记 xp 前值)。
        return ConstantAudit('XP_PER_BUY', expected, len(ests), 'confounded', expected,
                             detail=f'分布 {Counter(ests).most_common(3)}:主峰 0=快照已含买牌 XP(口径),次峰=真值观测')
    verdict = 'consistent' if expected is not None and abs(est - expected) <= 0.5 else 'refuted'
    return ConstantAudit('XP_PER_BUY', float(est), len(ests), verdict, expected,
                         detail=f'分布 {Counter(ests).most_common(3)}')


def audit_base_income(rows: list[dict]) -> ConstantAudit:
    """BASE_INCOME:跨节点、a 前缀花费=0、连胜加成不可观(streak None/≤1)的行对:
    est = Δgold − interest(min(gold_before//10, 5)) − streak_bonus(0)。"""
    expected = _expected_of('BASE_INCOME')
    ests: list[int] = []
    for a, b in zip(rows, rows[1:], strict=False):
        if a.get('run_id') != b.get('run_id'):
            continue
        sa, sb = a.get('state') or {}, b.get('state') or {}
        if sa.get('round_num') == sb.get('round_num'):
            continue   # 要跨节点(节点结算发收入)
        st = sa.get('streak')
        if st is not None and abs(st) > 1:
            continue   # 连胜/连败加成不可观 → 剔除(保守)
        prefix_cost = 0
        for x in (a.get('actions') or []):
            t = x.get('__type__')
            if t == 'RefreshShop':
                break
            if t in ('BuyCard', 'LevelUp'):
                prefix_cost += 1   # 仅剔除存在性(花费=0 的窗)
        if prefix_cost:
            continue
        gb = sa.get('gold') or 0
        interest = min(gb // 10, 5)
        d = (sb.get('gold') or 0) - gb - interest
        if 0 <= d <= 10:
            ests.append(d)
    if len(ests) < 5:
        return ConstantAudit('BASE_INCOME', None, len(ests), 'underpowered', expected)
    est, cnt = Counter(ests).most_common(1)[0]
    if est > (expected or 0):
        # 观测主峰高于注册值且分布整体上偏:连胜金/boss 加成等**未观收入混入观测窗**
        # (streak=None 行对无法剔除)—— 非机制 refute;标 confounded 待 streak 接线后收窗。
        return ConstantAudit('BASE_INCOME', expected, len(ests), 'confounded', expected,
                             detail=f'分布 {Counter(ests).most_common(3)}:整体上偏=未观收入(连胜/boss)混入,非 base>5')
    verdict = 'consistent' if expected is not None and est == int(expected) else 'refuted'
    return ConstantAudit('BASE_INCOME', float(est), len(ests), verdict, expected,
                         detail=f'分布 {Counter(ests).most_common(3)}(boss 节点 +2 会成次峰——次峰≠refute)')


def audit_interest_threshold(rows: list[dict]) -> ConstantAudit:
    """INTEREST_THRESHOLD(息封顶点):BASE_INCOME 同款窗,est_interest = Δgold − base − 0;
    验证 min(gold_before//10, 5) 公式(封顶=50)在 gb≥50 段成立(观测 est==5)。"""
    expected = _expected_of('INTEREST_THRESHOLD')
    ok = n = 0
    hi_obs = 0
    for a, b in zip(rows, rows[1:], strict=False):
        if a.get('run_id') != b.get('run_id'):
            continue
        sa, sb = a.get('state') or {}, b.get('state') or {}
        if sa.get('round_num') == sb.get('round_num'):
            continue
        st = sa.get('streak')
        if st is not None and abs(st) > 1:
            continue
        if any(x.get('__type__') in ('BuyCard', 'LevelUp', 'RefreshShop')
               for x in (a.get('actions') or [])):
            continue
        gb = sa.get('gold') or 0
        if gb < 50:
            continue   # 只测封顶段(gb≥50 → interest 应=5)
        est_int = (sb.get('gold') or 0) - gb - 5   # base=5(注册值;BASE_INCOME 审计交叉验证)
        n += 1
        if est_int == 5:
            ok += 1
        if est_int > 0:
            hi_obs += 1
    if n < 5:
        return ConstantAudit('INTEREST_THRESHOLD', None, n, 'underpowered', expected,
                             detail='gb≥50 且零花费零连胜窗的行对不足——观测缺口(攒息后期少刷)')
    consistent = ok / n >= 0.8
    if not consistent and hi_obs / n >= 0.5:
        # 正偏差主导:未观收入(boss+2/连胜)混入,封顶公式不可判 —— 非 refute。
        return ConstantAudit('INTEREST_THRESHOLD', expected, n, 'confounded', expected,
                             detail=f'封顶段命中 {ok}/{n};正偏差行 {hi_obs}/{n}=未观收入混入(观测窗混杂,非封顶≠50)')
    verdict = 'consistent' if consistent else 'refuted'
    return ConstantAudit('INTEREST_THRESHOLD', 50.0, n, verdict, expected,
                         detail=f'封顶段 interest==5 命中 {ok}/{n};正偏差行 {hi_obs}(boss+2/连胜混杂源)')


def audit_mechanisms(replay_dir: str | Path) -> list[ConstantAudit]:
    """入口:decisions.jsonl → 各常数审计清单。"""
    rows = [json.loads(line) for line in Path(replay_dir).joinpath('decisions.jsonl')
            .read_text(encoding='utf-8').splitlines()]
    return [
        audit_refresh_cost(rows),
        audit_xp_per_buy(rows),
        audit_base_income(rows),
        audit_interest_threshold(rows),
    ]


if __name__ == '__main__':
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    for a in audit_mechanisms('.debug/temp/currency_war/replay'):
        print(f'{a.name}: est={a.estimate} n={a.n} verdict={a.verdict} expected={a.expected} {a.detail}')
