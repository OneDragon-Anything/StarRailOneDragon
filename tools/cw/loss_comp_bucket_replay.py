"""败轮补发口径判别·分桶重放(BoardState 设计 §4.2 口径冲突挂账的仲裁实验)。

问题:战斗败轮的轮首补发基项有两个互斥候选口径——
  H_base(基础奖励口径,玩家裁定 2026-09-09):补发 = 被败节点的基础奖励
    (平面感知键:P1 r1=3 / r2=4 / 其余 5,与奖励轮同款)+ 利息;
  H_type(节点类型表口径,108 局差分的分桶读数):补发 =
    LOSS_GOLD_BY_NODE{battle:2, encounter:4, boss:4} + 利息。
判据:补发金额**随轮次/平面变**(P1r1→3、P1r2→4、其余→5)= H_base 胜;
**按类型恒 2/4** = H_type 胜。

方法(逐笔记账差分):
  败轮 N 的备战帧金 g(N) 与下一可读轮 N+1 的备战帧金 g(N+1) 之间,金流 =
  轮内动作净支出 + 卖金钩子 + 补发 + 利息。轮内动作自带金额字段
  (BuyCard.card.cost / LevelUp.cost / LevelUpShop.cost / RefreshShop.cost),
  卖金走 exogenous.sell_income 钩子(choice.gold_delta,按 plane+round 归轮),
  CompTransaction 的卖也经该钩子入账。于是
      补发估算 = g(N+1) − g(N) + Σ支出 − Σ卖金 − 利息(g_settle),
  g_settle = g(N) − Σ支出 + Σ卖金(结算时点持金)。
  主子集限 0 ≤ g_settle < 10(利息恒 0,且不受息帽卡影响),差值即补发基项。
  未知金额面(ClickSpheres/OpenBox/OpenTome 的内容物、事件即时金;原 PickBoxCard/RunTools 项随 unified-action-factory 批2a/2b 词表删除退役)
  一律整轮剔除;金面效果卡局(狸财经狸息 flat/双手狸代买扣金)整局剔除。
  胜轮同法校验 = 方法自检:差值应 = base + streak_gold(进轮连胜) + 利息。

数据:.debug/currency_war/telemetry/matches/match_*.json(同源语料;
本脚本只读)。用法:
  uv run python tools/cw/loss_comp_bucket_replay.py [--matches GLOB]
"""
from __future__ import annotations

import argparse
import glob
import json
from collections import Counter, defaultdict

#: 动作 → 轮内支出金额提取键(无金额字段=旧 schema,该轮剔除)
SPEND_FIELDS: dict[str, tuple[str, ...]] = {
    'BuyCard': ('card', 'cost'),
    'LevelUp': ('cost',),
    'LevelUpShop': ('cost',),
    'RefreshShop': ('cost',),
}
#: 未知金流动作(内容物可能含金且无金额记录)——出现即整轮剔除
UNKNOWN_GOLD_ACTIONS: frozenset[str] = frozenset({
    'ClickSpheres', 'OpenBox', 'OpenTome',
})

#: 遥测节点类型(中文为主,旧局混英文 token)→ 引擎 token(与 LOSS_GOLD_BY_NODE 键同域)
NODE_TOKEN: dict[str, str] = {
    '普通战斗': 'battle', '遭遇': 'encounter', 'boss': 'boss',
    'battle': 'battle', 'encounter': 'encounter',
    '奖励': 'reward', '补给': 'supply', '首领': 'boss', '精英': 'elite',
}
COMBAT_TOKENS: frozenset[str] = frozenset({'battle', 'encounter', 'boss'})

#: 金面效果卡黑名单(整局剔除:其金流无动作钩子,残差不可归因)
GOLD_EFFECT_CARDS: tuple[str, ...] = ('狸财经狸', '双手狸开键盘')

#: 连胜金真值表(与 kernel cw_economy.STREAK_GOLD_TABLE 同值;此处独立内联,
#: 让判别不依赖被审代码的当前实现——判据源独立纪律)
_STREAK_TABLE: tuple[int, ...] = (1, 1, 2, 2, 2, 3, 4)

#: 缺省息帽档(与 kernel DEFAULT_INTEREST_CAP 同值;次级子集扣息用)
_DEFAULT_CAP: int = 5


def _streak_gold(streak: int) -> int:
    return _STREAK_TABLE[max(0, min(streak, len(_STREAK_TABLE) - 1))]


def h_base(plane: int, round_num: int) -> int:
    """H_base 预测:节点 (plane, round) 的基础奖励(平面感知键)。"""
    if plane == 1 and round_num == 1:
        return 3
    if plane == 1 and round_num == 2:
        return 4
    return 5


def h_type(node_type: str) -> int:
    """H_type 预测:LOSS_GOLD_BY_NODE 类型表(非战斗类无预测)。"""
    return {'battle': 2, 'encounter': 4, 'boss': 4}.get(node_type, 0)


def _action_spend(action: dict) -> int | None:
    """单动作金支出;金额字段缺失(旧 schema)返 None。"""
    t = action.get('__type__')
    if t not in SPEND_FIELDS:
        return 0
    keys = SPEND_FIELDS[t]
    node: object = action
    for k in keys[:-1]:
        if not isinstance(node, dict) or k not in node:
            return None
        node = node[k]
    if not isinstance(node, dict) or keys[-1] not in node:
        return None
    v = node[keys[-1]]
    return int(v) if v is not None else None


def replay(matches_glob: str) -> None:
    files = sorted(glob.glob(matches_glob))
    win_resid: Counter[int] = Counter()          # 胜轮校验:差值−期望 分布
    win_total = win_hit = 0
    loss_primary: dict[tuple, list[int]] = defaultdict(list)
    loss_secondary: dict[tuple, list[int]] = defaultdict(list)
    skipped: Counter[str] = Counter()
    excluded: Counter[str] = Counter()
    used_matches = 0

    for fp in files:
        with open(fp, encoding='utf-8') as f:
            raw = f.read()
        m = json.loads(raw)
        why = next((c for c in GOLD_EFFECT_CARDS if c in raw), None)
        if why:
            excluded[f'金面效果卡:{why}'] += 1
            continue
        used_matches += 1
        rows = m.get('rounds') or []
        losses: dict[tuple[int, int], str] = {}
        for ln in m.get('loss_nodes') or []:
            token = NODE_TOKEN.get(str(ln.get('node_type')), '')
            if token:
                losses[(int(ln['plane']), int(ln['round']))] = token
        streak_after: dict[tuple[int, int], int] = {}
        for o in m.get('slices', {}).get('outcomes.jsonl') or []:
            try:
                streak_after[(int(o['plane']), int(o['round_num']))] = \
                    int(o.get('streak') or 0)
            except (KeyError, TypeError, ValueError):
                continue
        # 卖金钩子:(plane, round) → Σ gold_delta
        sell_gold: dict[tuple[int, int], int] = defaultdict(int)
        event_rounds: set[tuple[int, int]] = set()
        for e in m.get('slices', {}).get('exogenous.jsonl') or []:
            snap = e.get('state_snapshot') or {}
            try:
                pkey = (int(snap.get('plane') or 0), int(e['round_num']))
            except (KeyError, TypeError, ValueError):
                continue
            if e.get('kind') == 'sell_income':
                delta = ((e.get('choice') or {}).get('gold_delta'))
                if delta is not None:
                    sell_gold[pkey] += int(delta)
            elif e.get('kind') == 'event_choice':
                event_rounds.add(pkey)

        for i in range(len(rows) - 1):
            cur, nxt = rows[i], rows[i + 1]
            g0, g1 = cur.get('gold'), nxt.get('gold')
            if g0 is None or g1 is None:
                skipped['端点金缺失'] += 1
                continue
            pkey = (int(cur['plane']), int(cur['round']))
            token = NODE_TOKEN.get(str(cur.get('node_type')), '')
            is_loss = pkey in losses
            actions = cur.get('actions') or []
            spend = 0
            bad = False
            for a in actions:
                t = a.get('__type__')
                if t in UNKNOWN_GOLD_ACTIONS:
                    bad = True
                    break
                s = _action_spend(a)
                if s is None:
                    bad = True   # 旧 schema 无金额字段
                    break
                spend += s
            if bad:
                skipped['未知金流动作/旧schema'] += 1
                continue
            if pkey in event_rounds:
                skipped['事件即时金轮'] += 1
                continue
            sells = sell_gold.get(pkey, 0)
            g_settle = int(g0) - spend + sells
            diff = int(g1) - int(g0)
            if is_loss:
                ltoken = losses[pkey]
                bucket = (ltoken, pkey[0], pkey[1],
                          NODE_TOKEN.get(str(nxt.get('node_type')), '?'))
                if g_settle < 0:
                    skipped['结算持金负值'] += 1
                elif 0 <= g_settle < 10:
                    loss_primary[bucket].append(diff)
                else:
                    loss_secondary[bucket].append(
                        diff - min(g_settle // 10, _DEFAULT_CAP))
            elif token in COMBAT_TOKENS:
                # 胜轮方法自检:进轮连胜 = 上一轮结算后 streak
                sp = streak_after.get(
                    (int(rows[i - 1]['plane']), int(rows[i - 1]['round']))
                ) if i > 0 else None
                if sp is None or sp < 0:
                    skipped['胜轮校验缺进轮连胜'] += 1
                    continue
                expected = (h_base(pkey[0], pkey[1]) + _streak_gold(sp)
                            + min(max(g_settle, 0) // 10, _DEFAULT_CAP))
                win_total += 1
                if diff == expected:
                    win_hit += 1
                win_resid[diff - expected] += 1

    # ---- 输出 ----
    print(f'语料:{len(files)} 局,纳入 {used_matches},'
          f'整局剔除 {dict(excluded)},行级跳过 {dict(skipped)}')
    print()
    print('== 胜轮逐笔记账校验(方法自检:差值−期望;期望=base+streak_gold+息) ==')
    if win_total:
        print(f'   n={win_total} 逐位命中={win_hit} '
              f'({win_hit / win_total * 100:.1f}%)  '
              f'残差分布:{dict(sorted(win_resid.items()))}')
    else:
        print('   n=0(无可用校验样本)')
    print()
    print('== 败轮补发分布(主子集:逐笔记账 ∧ 0<=结算持金<10 → 差值=补发基项) ==')
    print(f'{"桶(token,p,r,下一轮)":<26}{"n":>4}  {"分布":<30}'
          f'{"众数":>4}  H_base命中   H_type命中')
    hb_hit = ht_hit = hb_n = ht_n = 0
    for bucket in sorted(loss_primary, key=str):
        vals = loss_primary[bucket]
        cnt = dict(sorted(Counter(vals).items()))
        mode = Counter(vals).most_common(1)[0][0]
        token, pl, rn = bucket[0], bucket[1], bucket[2]
        hb, ht = h_base(pl, rn), h_type(token)
        line = (f'{str(bucket):<26}{len(vals):>4}  {str(cnt):<30}'
                f'{mode:>4}  ')
        if token in COMBAT_TOKENS:
            mh = sum(1 for v in vals if v == hb)
            mt = sum(1 for v in vals if v == ht)
            hb_hit += mh
            ht_hit += mt
            hb_n += len(vals)
            ht_n += len(vals)
            line += f'{mh}/{len(vals)}'.ljust(12) + f'{mt}/{len(vals)}'
        else:
            line += '(非战斗类,无 H_type 预测)'
        print(line)
    print()
    print('== 次级子集(结算持金>=10,扣缺省息帽利息;息帽卡局有偏,旁证) ==')
    for bucket in sorted(loss_secondary, key=str):
        vals = loss_secondary[bucket]
        cnt = dict(sorted(Counter(vals).items()))
        print(f'{str(bucket):<26}{len(vals):>4}  {cnt}')
    if hb_n:
        print()
        print(f'== 战斗类逐样本命中率(主子集 n={hb_n}) ==')
        print(f'   H_base(基础奖励口径): {hb_hit}/{hb_n} '
              f'= {hb_hit / hb_n * 100:.1f}%')
        print(f'   H_type(类型表口径):   {ht_hit}/{ht_n} '
              f'= {ht_hit / ht_n * 100:.1f}%')
    else:
        print()
        print('== 主子集战斗类样本 n=0:数据不足以定谳(见交付申报) ==')


def main() -> None:
    ap = argparse.ArgumentParser(
        description='败轮补发口径判别·分桶重放(§4.2 挂账仲裁)')
    ap.add_argument('--matches',
                    default='.debug/currency_war/telemetry/matches/match_*.json')
    args = ap.parse_args()
    replay(args.matches)


if __name__ == '__main__':
    main()
