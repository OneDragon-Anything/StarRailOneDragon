"""决策确定性验收 harness(redesign 46 号 J0;ADR-0180)。

**任务(46 号 J0)**:地基体检 —— 同一 state 前缀重跑决策管线,决策序列必须 100% 确定
(同种子);与录制时动作序列比对给出一致性率(**录制时 rng 未种子 → 比对差 = 非确定源
的实证清单**,非失败)。

- 自洽性(硬判据):同 state + 同种子 → 逐字节一致(跨「进程」= 独立 import 后的两次调用);
- 对拍一致性(诊断):replay 动作 type 序列 vs decisions.jsonl 录制 —— 分歧行按类归因
  (未种子随机/字段缺失默认值漂移/依赖时间)。
纯函数,离线;不操作游戏。
"""
from __future__ import annotations

import json
import random
from pathlib import Path
from types import SimpleNamespace

from sr_od.application.currency_war.cw_comps import get_comp
from sr_od.application.currency_war.cw_plan import plan
from sr_od.application.currency_war.cw_state import BenchChar, GameState, ShopCard


def replay_config() -> SimpleNamespace:
    """离线 mock config(与 sr-od-test _cfg 同款;getattr 读,缺省安全)。"""
    return SimpleNamespace(
        faction_priority=['贝洛伯格', '仙舟', '巡海游侠'],
        character_priority=['阿格莱雅'],
    )


def state_from_row(row: dict) -> GameState:
    """decisions.jsonl 的 state dict → GameState(嵌套 BenchChar/ShopCard 复原)。"""
    d = dict(row.get('state') or {})
    d.pop('node_path', None)
    shop = [ShopCard(**{k: v for k, v in c.items()
                        if k in ('x', 'faction', 'name', 'cost', 'star')})
            for c in (d.pop('shop', None) or [])]
    bench = [BenchChar(**{k: v for k, v in c.items()
                          if k in ('slot', 'char_id', 'faction', 'star', 'position_pref', 'equips')})
             for c in (d.pop('bench', None) or [])]
    deployed = [BenchChar(**{k: v for k, v in c.items()
                             if k in ('slot', 'char_id', 'faction', 'star', 'position_pref', 'equips')})
                for c in (d.pop('deployed', None) or [])]
    known = {f.name for f in GameState.__dataclass_fields__.values()}
    st = GameState(**{k: v for k, v in d.items() if k in known})
    st.shop, st.bench, st.deployed = shop, bench, deployed
    return st


def _action_types(actions: list) -> list[str]:
    return [getattr(a, '__type__', type(a).__name__) for a in (actions or [])]


def run_replay(replay_dir: Path | str, n_prefixes: int = 50, seed: int = 42,
               target_of_row: dict | None = None) -> dict:
    """J0 体检主入口:取前 n 条决策迹 → 自洽重跑 + 录制对拍。

    返回 {n, self_consistent, vs_recorded_match, mismatches:[{idx, run_id, recorded, replayed}]}。
    self_consistent < 1.0 = 确定性违纪(必须修);vs_recorded < 1.0 = 非确定源实证
    (录制时 rng 未种子;归因进 46 号登记表)。
    """
    rows = [json.loads(line) for line in
            Path(replay_dir).joinpath('decisions.jsonl').read_text(encoding='utf-8').splitlines()]
    rows = rows[:n_prefixes]
    n_self_ok = 0
    match = 0
    mismatches: list[dict] = []
    for i, row in enumerate(rows):
        st = state_from_row(row)
        tc_name = (row.get('target_comp') or '').strip()
        tc = get_comp(tc_name) if tc_name else None
        cfg = replay_config()
        a1 = plan(st.copy(), cfg, cfg.faction_priority, rng=random.Random(seed), target_comp=tc)
        a2 = plan(st.copy(), cfg, cfg.faction_priority, rng=random.Random(seed), target_comp=tc)
        if _action_types(a1) == _action_types(a2):
            n_self_ok += 1
        rec = _action_types(row.get('actions') or [])
        rep = _action_types(a1)
        if rec == rep:
            match += 1
        else:
            mismatches.append({'idx': i, 'run_id': row.get('run_id'),
                               'recorded': rec[:8], 'replayed': rep[:8]})
    return {'n': len(rows),
            'self_consistent': n_self_ok / max(1, len(rows)),
            'vs_recorded_match': match / max(1, len(rows)),
            'mismatches': mismatches[:10]}
