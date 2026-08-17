"""live plan 对拍器(27 号能力画像语料工具;r11 诊断「r9 升级爆发」用)。

对每局 decisions.jsonl:取 (state 快照, actions) 对,离线重放 plan() 比对
「复现动作分布 vs live 实发动作」——差异点 = 执行偏差语料(state 时序/读数
干扰的量化定位)。黄金档位:RunBuyPhase 内层 plan 的 decisions
(actions 含 BuyCard/LevelUp/RefreshShop 混合的段)。
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

DEFAULT_REPLAY = Path('.debug/temp/currency_war/replay')


def _state_from_snapshot(snap: dict):
    """decision 的 state 快照 → 近似 GameState(bench/board 用快照粗粒度)。"""
    from sr_od.application.currency_war.cw_state import GameState
    st = GameState()
    for k in ('gold', 'level', 'hp', 'plane', 'round_num'):
        v = snap.get(k)
        if v is not None:
            import contextlib
            with contextlib.suppress(Exception):   # 快照字段兼容
                setattr(st, k, v)
    board = snap.get('board')
    if isinstance(board, dict):
        st.board = dict(board)
    return st


def replay_plan_diff(replay_dir: Path | str = DEFAULT_REPLAY,
                     run_id: str | None = None,
                     target_comp_name: str | None = None,
                     max_points: int = 10) -> list[dict]:
    """对拍 live decisions 的 plan 段,返回差异点列表(最多 max_points)。

    差异点 = {t, live_acts 分布, 复现 plan 分布, gold/level/hp}。
    需要 config 可构造(离线默认实例);comp 按名取,取不到跳过该点。
    """
    from sr_od.application.currency_war.currency_war_config import CurrencyWarConfig
    from sr_od.application.currency_war.cw_comps import COMP_LIBRARY
    from sr_od.application.currency_war.cw_plan import plan as plan_fn

    cfg = CurrencyWarConfig(1)
    target = None
    if target_comp_name:
        target = next((c for c in COMP_LIBRARY if c.name == target_comp_name), None)
    p = Path(replay_dir) / 'decisions.jsonl'
    if not p.exists():
        return []
    diffs: list[dict] = []
    for line in p.open(encoding='utf-8'):
        if len(diffs) >= max_points:
            break
        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            continue
        if run_id is not None and d.get('run_id') != run_id:
            continue
        acts = d.get('actions') or []
        # 黄金段:混合 buy/level/refresh 的内层 plan(排除单动作控制流)
        types = {a.get('__type__', '') for a in acts if isinstance(a, dict)}
        if not {'BuyCard', 'LevelUp', 'RefreshShop'} & types:
            continue
        live = Counter(a.get('__type__', '?') for a in acts if isinstance(a, dict))
        st = _state_from_snapshot(d.get('state') or {})
        try:
            repro = Counter(type(a).__name__ for a in
                            plan_fn(st, cfg, cfg.faction_priority, target_comp=target))
        except Exception as e:   # noqa: BLE001  复现失败也记(画像语料)
            repro = Counter({f'<error:{type(e).__name__}>': 1})
        # 差异判据:LevelUp 数量差 >2 或有无之别
        lv_live, lv_rep = live.get('LevelUp', 0), repro.get('LevelUp', 0)
        if abs(lv_live - lv_rep) > 2 or (lv_live == 0) != (lv_rep == 0):
            diffs.append({'t': f"P{d.get('plane')}-r{d.get('round_num')}",
                          'gold': d.get('gold'), 'level': (d.get('state') or {}).get('level'),
                          'hp': d.get('hp'),
                          'live': dict(live), 'repro': dict(repro)})
    return diffs
