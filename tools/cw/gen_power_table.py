"""货币战争 · 战力表生成器(Phase A Day 1;redesign §4.1 数据层)。

数据源:plaza 784 篇 V4.4 高难帖(同 gen_plaza_comps.py 的过滤与 canon 规则;
--cache 用本地 jsonl)。

产出(**勿手编,重跑覆盖**):
  1. ``src/sr_od/application/currency_war/cw_power_table_data.py`` —— 机器消费:
     ``POWER_ENTRIES``:形态键(羁绊组合+人口)× 位面(P1/P2/P3) → 验证篇数。
  2. ``docs/game/currency_war/data/power_table_meta.md`` —— 人读版。

形态键规则(redesign §4.1;r214 回放同口径——键构造与 gate 脚本单源对齐):
  - 羁绊计数 ≥2 的档,按人数降序、同人数名字排序 → ``名+数`` 用 ``+`` 连接;
  - 人口 = 前排+后排(role_stages 段内);
  - 空段(作者未填)跳过。

判断层(``cw_power_table.py``,手维护)消费本表:分层保守系数/
三级回退/位面边界权威判定——数据与判断分离(gen 生成器三件套规范)。

用法(项目根):
  uv run python tools/cw/gen_power_table.py --cache
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]

REPO = Path(__file__).resolve().parents[2]
DATA_PY = REPO / "src/sr_od/application/currency_war/cw_power_table_data.py"
DOC_MD = REPO / "docs/game/currency_war/data/power_table_meta.md"
CACHE = Path(".debug/temp/currency_war/plaza/lineups_HotHard.jsonl")
GEN_CMD = "uv run python tools/cw/gen_power_table.py --cache"


def bonds_key_of_stage(st: dict) -> tuple[str, int] | None:
    """形态键:羁绊组合(≥2档,人数降序+名字序)+人口;空段返 None。"""
    traits = [t for t in (st.get('traits') or [])
              if (t.get('current_role_count') or 0) >= 2]
    front = st.get('front_roles') or []
    back = st.get('back_roles') or []
    if not traits and not front and not back:
        return None
    traits.sort(key=lambda t: (-(t.get('current_role_count') or 0),
                               t.get('trait_name') or ''))
    bonds = '+'.join(f"{t['trait_name']}{t['current_role_count']}"
                     for t in traits)
    return bonds, len(front) + len(back)


def load_posts(cache: bool) -> list[dict]:
    if cache:
        with open(CACHE, encoding='utf-8') as fh:
            return [json.loads(line) for line in fh]
    raise SystemExit('在线模式未接(用 --cache;数据源同 gen_plaza_comps)')


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--cache', action='store_true')
    args = ap.parse_args()

    posts = load_posts(args.cache)
    v44 = [x for x in posts
           if (x.get('tourn_detail') or {}).get('rpg_game_big_version') == '4.4'
           and (x.get('tourn_detail') or {}).get('create_by_env')
           != 'TournLineupEnv_KOLSandbox'
           and not ((x.get('tourn_detail') or {}).get('is_expired')
                    or (x.get('tourn_detail') or {}).get('is_sub_expired'))]

    entries: Counter = Counter()          # (bonds, pop, phase) -> n
    phase_posts: Counter = Counter()
    for it in v44:
        td = it['tourn_detail']
        for st in (td.get('role_stages') or []):
            ph = {'early': 'P1', 'middle': 'P2', 'final': 'P3'}.get(
                str(st.get('stage', '')).lower())
            if not ph:
                continue
            key = bonds_key_of_stage(st)
            if key is None:
                continue
            bonds, pop = key
            if not bonds:
                continue
            entries[(bonds, pop, ph)] += 1
            phase_posts[ph] += 1

    total_posts = len(v44)
    lines = [
        '# 本文件由 tools/cw/gen_power_table.py 生成,勿手编。',
        f'# 重跑: {GEN_CMD}(数据源 plaza 784 篇 V4.4 高难帖)',
        '# 用途: 战力表数据层(形态×位面→验证篇数);判断层在 cw_power_table.py。',
        '# 键口径: 羁绊≥2档按人数降序+名字序连接;人口=前后排合计。',
        '"""战力表数据(生成;勿手编)。"""',
        '',
        'POWER_ENTRIES: dict[tuple[str, int, str], int] = {',
    ]
    for (bonds, pop, ph), n in sorted(entries.items()):
        lines.append(f'    ({bonds!r}, {pop}, {ph!r}): {n},')
    lines.append('}')
    lines.append('')
    DATA_PY.write_text('\n'.join(lines), encoding='utf-8')

    # 人读版
    by_phase: dict[str, list] = {'P1': [], 'P2': [], 'P3': []}
    for (bonds, pop, ph), n in entries.items():
        by_phase[ph].append((n, pop, bonds))
    md = [
        '# 战力表数据(plaza 784 篇提取;生成勿手编)',
        '',
        f'> 生成: {GEN_CMD};形态键=羁绊组合+人口;篇数=「敢用」下限证据',
        f'(幸存者单向)。总帖 {total_posts};段样本 '
        f'{dict(phase_posts)}。',
        '',
    ]
    for ph in ('P1', 'P2', 'P3'):
        rows = sorted(by_phase[ph], reverse=True)
        md.append(f'## {ph} TOP30(共 {len(rows)} 形态)')
        md.append('')
        md.append('| 篇数 | 人口 | 形态 |')
        md.append('|---|---|---|')
        for n, pop, bonds in rows[:30]:
            md.append(f'| {n} | {pop} | {bonds} |')
        md.append('')
    DOC_MD.write_text('\n'.join(md), encoding='utf-8')

    print(f'战力表生成: {len(entries)} 条目 '
          f'(P1 {sum(1 for k in entries if k[2]=="P1")}/'
          f'P2 {sum(1 for k in entries if k[2]=="P2")}/'
          f'P3 {sum(1 for k in entries if k[2]=="P3")});'
          f' 数据 {DATA_PY.name};文档 {DOC_MD.name}')


if __name__ == '__main__':
    main()
