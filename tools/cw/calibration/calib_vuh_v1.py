"""V̄/V_gap/u/H 首版标定(calibration batch,calibration.py 注入源的数值产出)。

口径(证明单一源 = p40/p41 待标定清单,本脚本只产出数值不改机器):
- 数据源 = replay/matches/ 按局档案(生产对局语料;telemetry match_archive
  装配产物,含 decisions 逐帧 actions/state);
- u_by_cost(使用概率,p41 A5):一张 1★ 买入卡「被使用」= 该角色在**买入
  之后的任一战斗轮出现在 deployed(上场)**——「上过场」口径。边界:垫件
  临时上场也计入(高估 u,偏保守侧=少卖);终局板面口径另列参考列;
- h_horizon(需要时距,p41 A5):used 样本「买入轮 → 首次上场轮」的轮距
  中位数(跨位面按全局轮序计);未使用样本(删失)不计入 → H 是 used 条件
  下界口径(真实 H 含 never 分支,只声明 ≥ 此值);标定批收带 H∈[6,14]
  (p41 自检④稳健带);
- V̄(单卡平均净价值,p40 A5/待标定清单):局级归因折金——回归
  rounds_survived ~ Σ_c(used 张数,按费用档) 得每档边际生存轮 β_c,
  V̄(c) = β_c × Ī(=7,p47 净收入带 [6,8] 中位,calibration.i_bar 同源)。
  折金口径:1 生存轮 ≈ 净收入流 Ī 金(**下界口径**——存活轮的息复利、
  连胜金、位面推进奖励均未计入);样本不足的档(used n < 5)不报点值,
  给保守下界;
- V_gap:非独立常量(随缺口深度 k 缩放),按 p40 待标定清单换算式
  V_gap ≈ Σ V̄_net + Σ卡费 在窗口装配侧现算——本脚本产出 V̄ 表,
  换算式落 calibration.py 注入源注释(单一源,不在此造第二处公式)。

运行(PowerShell):$env:PYTHONPATH='src'; uv run python tools/cw/calibration/calib_vuh_v1.py
输出:stdout 报告 + `.debug/temp/currency_war/calib_vuh_v1_report.json`。
"""
from __future__ import annotations

import json
import random
import statistics
import sys
from collections import defaultdict
from pathlib import Path

# Windows 控制台缺省 GBK,组合变音符(V̄)会炸编码——统一 utf-8 输出
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from sr_od.application.currency_war.kernel.cw_observe import DEFAULT_REPLAY_DIR

I_BAR_GOLD_PER_ROUND = 7          # p47 净收入带 [6,8] 中位(calibration.i_bar 同源)
MIN_SAMPLE_FOR_POINT = 5          # used 样本低于此值的档只给保守下界
H_BAND = (6, 14)                  # p41 自检④ H 稳健带
#: 档间先验序(p41 特异性序:1费垫件 ≪ 2费 < 3费骨架 > 4费 > 5费贯穿;
#: 样本不足档的下界锚 = 左邻档值,禁凭空拍值)
_COST_ORDER_FALLBACK = {1: 2.0, 2: 4.0, 3: 8.0, 4: 6.0, 5: 30.0}


def v_bar_synthetic() -> dict:
    """V̄ 合成价值链(p40 待标定清单口径 b「按注册表折算」;全部锚 =
    registry/cw_registry 已收字段,零新自由参数):

    V̄_net = rung 流 + 胜率边际流
      rung 流(e1 变体)= rung_value[1] × rounds_left_est
      rung 流(e2 变体)= rung_value[2] × rounds_left_est(累计凑档,P3)
      胜率流   = Δp(e0→e1) × 单战价值 × battles_left_est
      Δp(e0→e1) = h3_win_rate[1] − h3_win_rate[0]       (注册表胜率阶梯)
      单战价值  = expected_battle_loss × hp_to_gold + 连胜金下界 2
                  (STREAK_GOLD_TABLE 2-4 连胜档;下界口径,高连胜不计)
    两变体 = 标定带 [16.7, 24.7]:
    - e1 变体(下沿)= 每件贡献 1 个档位跨越的通用口径;
    - e2 变体(上沿/注入值)= **合格集条件语义**:E = 目标线核心件
      (p40 A4),缺口闭合(2★ 达成)按「主羁绊推进到所追档位」计
      (P3 凑档语义,rung 累计值);transition 方法论的凑档命题支持上沿。
    带 = S1 边界括注:16.7 时 S1(P=0.108)恰好关门、24.7 恰好开门——
    A/B 双臂可检验。输出成本无差异(A5:条件于合格集,成本分化由 u 与
    池参数承载;p41 自检④:V̄ 全档平移不改档间序)。声明:两变体均为
    **下界口径**——boss 税规避/连胜复利/连胜金高档未计。
    """
    from sr_od.application.currency_war.kernel.cw_registry import DEFAULT_REGISTRY
    reg = DEFAULT_REGISTRY
    rung1 = reg.rung_value[1] * reg.rounds_left_est
    rung2 = reg.rung_value[2] * reg.rounds_left_est
    dp = reg.h3_win_rate[1] - reg.h3_win_rate[0]
    per_battle = reg.expected_battle_loss * reg.hp_to_gold + 2.0
    win = dp * per_battle * reg.battles_left_est
    return {'rung_stream_e1': rung1, 'rung_stream_e2': rung2,
            'win_stream': win,
            'v_bar_e1': rung1 + win, 'v_bar_e2': rung2 + win,
            'v_bar_net': rung2 + win,     # 注入值 = 带上沿(解锁语义,见上)
            'dp_e01': dp, 'per_battle': per_battle}


def _load_matches(matches_dir: Path) -> list[dict]:
    out = []
    for p in sorted(matches_dir.glob('match_*.json')):
        try:
            out.append(json.loads(p.read_text(encoding='utf-8')))
        except (OSError, json.JSONDecodeError) as e:
            print(f'[skip] {p.name}: {e}')
    return out


def _round_key(r: dict) -> tuple[int, int]:
    return int(r.get('plane') or 1), int(r.get('round') or 0)


def collect_events(match: dict) -> dict:
    """单局 → (按档买入事件, used 轮距样本, used 终局计数, 局级汇总)。

    轮序键 = (plane, round);deployed 角色 = 该轮决策帧 state.deployed
    (战前上场名单,win_features 同源口径);CwActionBuyCardParam 动作的卡名/费档
    来自 actions(决策帧已含买入意图的卡对象)。
    """
    rounds = sorted(match.get('rounds', []), key=_round_key)
    buys: list[dict] = []          # {k:(plane,round), cost, name}
    deployed_names_at: dict[tuple[int, int], set[str]] = {}
    for r in rounds:
        key = _round_key(r)
        names = {d.get('char_id') for d in (r.get('deployed') or [])
                 if d.get('char_id')}
        deployed_names_at[key] = names
        for a in (r.get('actions') or []):
            if a.get('__type__') == 'CwActionBuyCardParam':
                card = a.get('card') or {}
                name = card.get('name')
                cost = card.get('cost')
                if name and isinstance(cost, int):
                    buys.append({'key': key, 'cost': cost, 'name': name})
    # used 判定(两口径):
    # - ever:买入之后任一轮上场(「上过场」参考列——旧策略填满板面,
    #   垫件也上场,系统性高估,不作标定主口径);
    # - final:终局(最后一战斗轮)仍在 deployed(「真被需要」主口径:
    #   成型贡献 = 留到最后的件;卖出/替换 = 判定不被需要)。
    first_use: dict[int, list[float]] = defaultdict(list)   # cost -> 轮距样本
    used_ever: dict[int, int] = defaultdict(int)
    used_final: dict[int, int] = defaultdict(int)
    total_n: dict[int, int] = defaultdict(int)
    key_list = sorted(deployed_names_at)
    final_names = deployed_names_at[key_list[-1]] if key_list else set()
    for b in buys:
        total_n[b['cost']] += 1
        ever = False
        for key in key_list:
            if key > b['key'] and b['name'] in deployed_names_at[key]:
                ever = True
                first_use[b['cost']].append(
                    (key[0] - b['key'][0]) * 9 + (key[1] - b['key'][1]))
                break
        if ever:
            used_ever[b['cost']] += 1
        if b['name'] in final_names:
            used_final[b['cost']] += 1
    endgame = match.get('endgame') or {}
    # 局级归因样本:每档「终局在场的买入张数」(成型贡献口径)
    attrib = {c: used_final.get(c, 0) for c in (1, 2, 3, 4, 5)}
    return {
        'total': dict(total_n), 'used': dict(used_final),
        'used_ever': dict(used_ever),
        'h_samples': dict(first_use),
        'attrib': attrib,
        'rounds_survived': int(endgame.get('rounds_survived') or 0),
        'plane_reached': int(endgame.get('plane_reached') or 0),
        'result': endgame.get('result'),
        'difficulty': endgame.get('difficulty'),
        'game_id': match.get('game_id'),
    }


def _ols(xs: list[list[float]], ys: list[float]) -> list[float]:
    """带截距 OLS(纯 python 正规方程;特征少,不引 numpy)。"""
    n = len(ys)
    k = len(xs[0]) + 1
    X = [[1.0] + row for row in xs]
    xtx = [[sum(X[i][a] * X[i][b] for i in range(n)) for b in range(k)]
           for a in range(k)]
    xty = [sum(X[i][a] * ys[i] for i in range(n)) for a in range(k)]
    # 高斯消元求逆
    aug = [row[:] + [xty[i]] for i, row in enumerate(xtx)]
    for col in range(k):
        piv = max(range(col, k), key=lambda rr: abs(aug[rr][col]))
        if abs(aug[piv][col]) < 1e-10:
            return [0.0] * k
        aug[col], aug[piv] = aug[piv], aug[col]
        pivv = aug[col][col]
        aug[col] = [v / pivv for v in aug[col]]
        for rr in range(k):
            if rr != col and aug[rr][col] != 0:
                f = aug[rr][col]
                aug[rr] = [v - f * w
                           for v, w in zip(aug[rr], aug[col], strict=True)]
    return [aug[i][k] for i in range(k)]


def _bootstrap_ci(xs, ys, iters: int = 500) -> list[tuple[float, float]]:
    """成对 bootstrap 的系数 90% 区间(小样本诚实带)。"""
    n = len(ys)
    coefs = [[] for _ in range(len(xs[0]) + 1)]
    for _ in range(iters):
        idx = [min(n - 1, max(0, random.randrange(n))) for _ in range(n)]
        bxs = [xs[i] for i in idx]
        bys = [ys[i] for i in idx]
        if len(set(bys)) < 2:
            continue
        for j, c in enumerate(_ols(bxs, bys)):
            coefs[j].append(c)
    out = []
    for cs in coefs:
        cs.sort()
        out.append((cs[int(0.05 * len(cs))], cs[int(0.95 * len(cs)) - 1])
                   if cs else (0.0, 0.0))
    return out


def main() -> None:
    matches = _load_matches(Path(DEFAULT_REPLAY_DIR) / 'matches')
    print(f'档案局数 = {len(matches)}')
    events = [collect_events(m) for m in matches]
    # hp 假值局过滤:档案装配期(2026-09-07 起)真值链已达标,保留全量;
    # abandoned 局(中断)剔除出归因(轮数截断非博弈结果)。
    attrib_events = [e for e in events if e['result'] in ('win', 'loss')]
    print(f'归因样本局数(非中断)= {len(attrib_events)}')

    total = defaultdict(int)
    used = defaultdict(int)
    used_ever = defaultdict(int)
    h_all: list[float] = []
    h_by_cost: dict[int, list[float]] = defaultdict(list)
    for e in events:
        for c, n in e['total'].items():
            total[c] += n
        for c, n in e['used'].items():
            used[c] += n
        for c, n in e.get('used_ever', {}).items():
            used_ever[c] += n
        for c, hs in e['h_samples'].items():
            h_by_cost[c].extend(hs)
            h_all.extend(hs)

    print('\n== u(使用概率;主口径=终局在场,参考列=上过场)==')
    u_table: dict[int, float] = {}
    for c in (1, 2, 3, 4, 5):
        n, m = total[c], used[c]
        if n == 0:
            print(f'  {c}费: 无样本')
            continue
        u_table[c] = m / n
        print(f'  {c}费: 终局在场 {m}/{n} = {m / n:.3f}'
              f'(上过场 {used_ever[c]}/{n} = {used_ever[c] / n:.3f})')
    if h_all:
        print(f'\n== H(买入→首次上场轮距;策略「买入即上场」行为污染,'
              f'语料不可识别 p41 语义——仅记录)==  used n={len(h_all)} 中位='
              f'{statistics.median(h_all):.1f}')

    print('\n== V̄ 合成价值链(注册表锚,零新自由参数;带 [e1 下沿, e2 上沿])==')
    syn = v_bar_synthetic()
    print(f"  rung 流 e1/e2 = {syn['rung_stream_e1']:.2f}/{syn['rung_stream_e2']:.2f} 金,"
          f" 胜率流 = {syn['win_stream']:.2f} 金 (Δp={syn['dp_e01']:.3f} × 单战 "
          f"{syn['per_battle']:.1f} 金 × 5 战)"
          f" → V̄_net 注入值(带上沿)= {syn['v_bar_net']:.1f} 金")

    print('\n== V̄ 局级归因(rounds_survived ~ used终局在场张数,OLS)==')
    xs = [[float(e['attrib'][c]) for c in (1, 2, 3, 4, 5)] for e in attrib_events]
    ys = [float(e['rounds_survived']) for e in attrib_events]
    beta = _ols(xs, ys)
    ci = _bootstrap_ci(xs, ys)
    v_bar: dict[int, float] = {}
    for i, c in enumerate((1, 2, 3, 4, 5), start=1):
        b = beta[i]
        n_used = used[c]
        lo, hi = ci[i]
        if n_used >= MIN_SAMPLE_FOR_POINT:
            v_bar[c] = max(0.0, b) * I_BAR_GOLD_PER_ROUND
            print(f'  {c}费: β={b:+.2f} 轮 [90%CI {lo:+.2f},{hi:+.2f}] '
                  f'→ V̄={v_bar[c]:.1f}金 (used n={n_used})')
        else:
            # 样本不足:取「左邻档已标定值 × 0.5」保守下界,禁点值
            fallback = _COST_ORDER_FALLBACK[c]
            print(f'  {c}费: β={b:+.2f} (used n={n_used} < {MIN_SAMPLE_FOR_POINT}'
                  f') → 样本不足,保守下界 {fallback:.1f}金(先验序锚,非点值)')
    # 参考:控制 difficulty 不可行(66 局内 A 档近单值),声明为口径边界。

    report = {
        'n_matches': len(matches),
        'n_attrib': len(attrib_events),
        'u_by_cost': u_table,
        'u_ever_by_cost': {c: (used_ever[c] / total[c]) if total[c] else None
                           for c in (1, 2, 3, 4, 5)},
        'h_not_identifiable': True,
        'h_median_purchase_to_deploy': statistics.median(h_all) if h_all else None,
        'v_bar_synthetic': syn,
        'v_bar_corpus_attribution': v_bar,
        'gold_per_round': I_BAR_GOLD_PER_ROUND,
    }
    out = Path('.debug/temp/currency_war/calib_vuh_v1_report.json')
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=1),
                   encoding='utf-8')
    print(f'\n报告落盘: {out}')


if __name__ == '__main__':
    main()
