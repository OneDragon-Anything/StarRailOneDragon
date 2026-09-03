"""P53 帧级 horizon V̄_net 复算脚本(可重跑证明锚;修 A 批)。

三件事:
1. 链锚核验:生产实现 ``cw4.statefn.vbar.v_bar_net`` 与 calib_vuh_v1
   合成价值链同源——r=5 时逐位等于旧静态注入值 24.7(连续性锚),
   各分量(rung_value[2]/Δp/单战价值/连胜金下界)逐项打印;
2. 反事实开门率重放:对 REFRESH_CFO 批 arm2 决策账本逐被拦帧,用生产
   判据同形口径重算账,按帧级 V̄_net(r) 判开门——复现
   REFRESH_CFO_REPORT §6 表(总开门率/分视界开门率/开门帧 j 分布);
   两口径并列:账 ≤ V̄_net(r)(生产比较项,卡价两侧相消,CALIB §2.2)
   与 账 ≤ V̄_net(r)+卡价(报告 §6 表头口径);
3. 单调性:V̄_net(r) 对 r 严格递增(r≥1)。

运行:$env:PYTHONPATH='src'; uv run python tools/cw/proofs/p53_frame_horizon_vgap_check.py
数据源:.debug/temp/currency_war/ab_run_20260903_r3/arm2/decisions.jsonl
(REFRESH_CFO 批三臂账本;缺失时第 2 项跳过并申报,链锚核验不依赖它)。
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from sr_od.application.currency_war.data import cw_shop_odds as odds
from sr_od.application.currency_war.data.cw_chars import CHARACTERS
from sr_od.application.currency_war.decision.cw4.statefn import vbar
from sr_od.application.currency_war.decision.cw4.statefn.income import net_income
from sr_od.application.currency_war.decision.cw4.statefn.interest import loss_exact
from sr_od.application.currency_war.kernel import cw_intention
from sr_od.application.currency_war.kernel.cw_comps import COMP_LIBRARY
from sr_od.application.currency_war.kernel.cw_registry import DEFAULT_REGISTRY

R3 = Path('.debug/temp/currency_war/ab_run_20260903_r3')
C_EFF = 2


def members_of(dec: dict) -> tuple[str, ...]:
    """成员集重建(与 REFRESH_CFO 复盘脚本同式:locked_comp→core+shared;
    P1 体系对→cw_intention._pair_members;超集近似,偏松向)。"""
    ist = dec.get('v3_intention') or {}
    lc = ist.get('locked_comp') or ''
    if lc:
        comp = next((c for c in COMP_LIBRARY if c.name == lc), None)
        if comp is not None:
            return tuple(dict.fromkeys(
                list(comp.core_chars) + list(comp.shared_chars)))
    pair = tuple(ist.get('p1_pair') or ())
    return tuple(sorted(cw_intention._pair_members(pair))) if pair else ()


def main() -> None:
    reg = DEFAULT_REGISTRY
    # ---- 1. 链锚核验 ----
    dp = reg.h3_win_rate[1] - reg.h3_win_rate[0]
    pb = vbar.per_battle_value(reg)
    print(f'rung_value[2]={reg.rung_value[2]} Δp(e0→e1)={dp:.3f} '
          f'单战价值={pb:.1f} (连胜金下界={vbar.streak_floor_gold()})')
    v5 = vbar.v_bar_net(reg, 5)
    print(f'V̄_net(r=5) = {v5:.2f}(连续性锚:旧静态注入 24.7,|Δ|<0.05 '
          f'{"过" if abs(v5 - 24.7) < 0.05 else "红"})')
    vals = [vbar.v_bar_net(reg, r) for r in range(1, 21)]
    assert all(vals[i] < vals[i + 1] for i in range(len(vals) - 1)), '单调性红'
    print('单调性:r∈[1,20] 严格递增 过')

    # ---- 2. 反事实开门率重放(数据在档时)----
    ledger = R3 / 'arm2' / 'decisions.jsonl'
    if not ledger.exists():
        print(f'[跳过] {ledger} 不在档(链锚核验不受影响)')
        return
    rows = []
    for x in ledger.read_text(encoding='utf-8').splitlines():
        d = json.loads(x)
        gold = int(d.get('gold') or 0)
        if gold < C_EFF:
            continue
        level = int(d['state']['level'] or 1)
        plane, rnd = int(d['plane'] or 1), int(d['round_num'] or 1)
        r = max(9 - rnd + 1, 1) + (9 if plane == 1 else 0)
        ibar = net_income(rnd, 0)
        st = d['state']
        owned: dict[str, list[int]] = {}
        for c in list(st.get('bench') or []) + list(st.get('deployed') or []):
            owned.setdefault(c.get('char_id') or '', []).append(
                c.get('star') or 1)
        best = None
        for m in members_of(d):
            ch = CHARACTERS.get(m)
            if ch is None or not ch.cost or odds.refresh_prob(
                    level, ch.cost) <= 0:
                continue
            stars = owned.get(m, [])
            if any(s >= 2 for s in stars):
                continue
            j = len(stars)
            e = odds.expected_refreshes_for_card(level, ch.cost, 2, j)
            if not math.isfinite(e):
                continue
            acct = C_EFF * e + loss_exact(
                gold, int(math.ceil(C_EFF * e)), r, ibar)
            if best is None or acct < best[0]:
                best = (acct, e, j, ch.cost)
        if best:
            v = vbar.v_bar_net(reg, r)
            rows.append({'acct': best[0], 'v': v, 'card': best[3],
                         'r': r, 'j': best[2]})
    n = len(rows)
    open_prod = [a for a in rows if a['acct'] <= a['v']]
    open_rep = [a for a in rows if a['acct'] <= a['v'] + a['card']]
    print(f'\n被拦帧重放 n={n}(修前静态门 100% 拦,REFRESH_CFO_REPORT §4)')
    print(f'生产口径 账≤V̄_net(r)      开门 {len(open_prod)}/{n} '
          f'= {len(open_prod) / n:.0%}')
    print(f'报告口径 账≤V̄_net(r)+卡价  开门 {len(open_rep)}/{n} '
          f'= {len(open_rep) / n:.0%}(报告 §6 表值 57%)')
    for lo, hi in [(1, 4), (4, 7), (7, 10), (10, 14), (14, 19)]:
        g = [a for a in rows if lo <= a['r'] < hi]
        if g:
            op = sum(1 for a in g if a['acct'] <= a['v'] + a['card'])
            print(f'  r∈[{lo},{hi}): n={len(g)} 开门率(报告口径)='
                  f'{op / len(g):.0%}')
    jd = {j: sum(1 for a in open_rep if a['j'] == j) for j in (0, 1, 2)}
    print(f'开门帧 j 分布(报告口径): {dict(sorted(jd.items()))}')


if __name__ == '__main__':
    main()
