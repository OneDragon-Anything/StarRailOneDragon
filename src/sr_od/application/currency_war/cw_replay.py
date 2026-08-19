"""决策回放 harness(r98,redesign/102 组件二的最小可用版)。

用途:策略改动后,对**历史局的 GameState 快照**重放 decide_prep,秒级看到
「这个改动动了哪些决策、方向对不对」——验证成本从实跑 20-40min 压到秒级,
"每刀都实跑验证"从此经济可行(bug 无存活空间的前提)。

数据源:replay/decisions.jsonl 的 state 字段(每备战轮的 GameState 快照,
r95 起含 plan_error 标记;session 态由 harness 重建,见 LIMITS)。

用法:
  uv run python -m sr_od.application.currency_war.cw_replay \
      [--run ID] [--rounds N] [--diff]      # 重放最近一局(或指定局)前 N 备战轮
  --diff:与当时实跑 actions 对比(改动效果 = 与基线的分歧行)

LIMITS(诚实边界):
- session 态(CommitSignals/冷却/失败记忆/framework)无法从快照重建 → 重放的
  update_target 分支与实跑可能不同(decide_prep 的 target 用快照当时值,不重算)。
  即:本 harness 验「**给定同一 target/state,plan 出的动作变没变**」,不验
  战略层(那需要 redesign/102 的 session 态快照化,后续)。
"""
from __future__ import annotations

import json
import sys

from sr_od.application.currency_war.cw_state import BenchChar, GameState, ShopCard
from sr_od.application.currency_war.cw_telemetry import DEFAULT_REPLAY_DIR
from sr_od.application.currency_war.strategies.default_strategy import DefaultCwStrategy


class _Cfg:
    faction_priority: list[str] = ['仙舟', '列车同行', '持续伤害', '护盾', '治疗']


def _rebuild_state(snap: dict) -> GameState:
    """decisions.jsonl 的 state dict → GameState(字段名一致,dataclass 直灌)。"""
    st = GameState()
    for k in ('gold', 'hp', 'level', 'plane', 'round_num', 'node_type',
              'streak', 'shop_refresh_cost', 'level_up_cost', 'xp_progress'):
        v = snap.get(k)
        if v is not None:
            setattr(st, k, v)
    st.board = dict(snap.get('board') or {})
    st.shop = [ShopCard(x=c.get('x', 0), faction=c.get('faction') or '?',
                        name=c.get('name') or '', cost=c.get('cost') or 1,
                        star=c.get('star') or 1)
               for c in (snap.get('shop') or []) if isinstance(c, dict)]
    st.bench = [BenchChar(slot=b.get('slot') or i + 1, char_id=b.get('char_id') or '',
                          faction=b.get('faction') or '?', star=b.get('star') or 1,
                          position_pref=b.get('position_pref') or 'back')
                for i, b in enumerate(snap.get('bench') or []) if isinstance(b, dict)]
    st.dual_track_phase = bool(snap.get('dual_track_phase'))
    return st


def _fmt(actions: list) -> str:
    parts = []
    for a in actions:
        t = type(a).__name__
        if t == 'BuyCard':
            parts.append(f"Buy({a.card.name})")
        elif t == 'LevelUp':
            parts.append('LvUp')
        elif t == 'RefreshShop':
            parts.append('D')
        elif t == 'SellBench':
            parts.append(f"Sell({a.bench_idx})")
        else:
            parts.append(t)
    return ' '.join(parts) or '(空)'


def main() -> None:
    sys.stdout.reconfigure(encoding='utf-8')  # type: ignore[attr-defined]
    args = sys.argv[1:]
    run_id = ''
    rounds = 0
    diff = False
    i = 0
    while i < len(args):
        if args[i] == '--run':
            run_id = args[i + 1]
            i += 2
        elif args[i] == '--rounds':
            rounds = int(args[i + 1])
            i += 2
        elif args[i] == '--diff':
            diff = True
            i += 1
        else:
            i += 1

    rep = DEFAULT_REPLAY_DIR
    # 每个 (plane,round) 取 actions 最多的一条(= plan 真值帧)
    best: dict = {}
    last_run = ''
    with open(rep / 'decisions.jsonl', encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue
            d = json.loads(line)
            last_run = d.get('run_id', '')
            if run_id and d.get('run_id') != run_id:
                continue
            k = (d.get('plane'), d.get('round_num'))
            if k not in best or len(d.get('actions') or []) > len(best[k].get('actions') or []):
                best[k] = d
    rid = run_id or last_run
    print(f'=== 决策回放 {rid} ===')

    strat = DefaultCwStrategy()
    sess = strat.create_session(_Cfg())
    for n_done, k in enumerate(sorted(best)):
        if rounds and n_done >= rounds:
            break
        d = best[k]
        snap = d.get('state') or {}
        st = _rebuild_state(snap)
        # target 用当时值(不重算战略层,见 LIMITS)
        from sr_od.application.currency_war.cw_comps import COMP_LIBRARY
        tgt = next((c for c in COMP_LIBRARY if c.name == d.get('target_comp')), None)
        sess.target_comp = tgt
        try:
            actions = strat.decide_prep(st, sess, _Cfg())
            new_s = _fmt(actions)
        except Exception as e:
            new_s = f'⚠ plan 异常: {type(e).__name__}: {e}'
        if diff:
            old_s = _fmt_json(d.get('actions') or [])
            mark = '  ' if new_s == old_s else '≠ '
            print(f"{mark}p{k[0]}r{k[1]} g={d.get('gold')}")
            print(f"     旧: {old_s}")
            if mark.strip():
                print(f"     新: {new_s}")
        else:
            print(f"  p{k[0]}r{k[1]} g={d.get('gold')} tgt={d.get('target_comp')}: {new_s}")


def _fmt_json(acts: list) -> str:
    parts = []
    for a in acts:
        t = a.get('__type__')
        if t == 'BuyCard':
            parts.append(f"Buy({(a.get('card') or {}).get('name')})")
        elif t == 'LevelUp':
            parts.append('LvUp')
        elif t == 'RefreshShop':
            parts.append('D')
        elif t == 'SellBench':
            parts.append(f"Sell({a.get('bench_idx')})")
        else:
            parts.append(t or '?')
    return ' '.join(parts) or '(空)'


if __name__ == '__main__':
    main()
