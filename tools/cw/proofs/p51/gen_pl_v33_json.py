# 生成 cw4 lambda_death 的 PL 键(位面键)v3.3 主表 JSON 工件。
#
# 数据单一源 = P51_V3_REBUILD v3.3 节的运行产物 p51_v33_run.txt
# (位于 .debug/temp/currency_war/redesign/,gitignored——故产物 JSON 需提交进包,
# 本脚本是从运行产物重建该 JSON 的对账器,重跑口径见文末注释)。
# 解析三节:Part 3M 主表(38 非空格 CI)+ Part 8 空格处置 + Part 8 逐格消费标签
# (薄格 Wilson 下限在标签行内,薄格 CI 下限无条件强制取该 Wilson 值)。
# 用法:uv run python tools/cw/proofs/p51/gen_pl_v33_json.py
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

SRC = Path('.debug/temp/currency_war/redesign/p51_v33_run.txt')
DST = Path('src/sr_od/application/currency_war/decision/cw4/statefn/'
           'data/lambda_death_pl_v33.json')

ROW = re.compile(
    r'^\s*(D[01])\((\d+)<(\d+)\)\s+(hp<=15|hp15-40|hp>40)\s+(P1|P2\+)\s+'
    r'(battle|encounter|boss|noncombat):\s*(.*)$')
VAL = re.compile(r'n=(\d+)\s+原始=([\d.]+)\s+单调=([\d.]+)\s+\[([\d.]+),([\d.]+)\]')
WILSON = re.compile(r'Wilson=([\d.]+)')


def _band(d: str, hp: str, pl: str, node: str) -> str:
    return f'{d}|{hp}|{pl}|{node}'


def main() -> None:
    text = SRC.read_text(encoding='utf-8')
    lines = text.splitlines()

    cells: dict[str, dict] = {}
    # —— Part 3M 主表段:从「PL 键 λ3 主表」标题起,到「PL 键(主表)空格数」止 ——
    in_main = False
    for ln in lines:
        if 'PL 键 λ3 主表' in ln:
            in_main = True
            continue
        if not in_main:
            continue
        if '空格数' in ln:
            break
        m = ROW.match(ln)
        if not m:
            continue
        d, lo, hi, hp, pl, node, rest = m.groups()
        if '<空格' in rest:
            cells[_band(d, hp, pl, node)] = {
                'n': 0, 'raw': None, 'mono': None,
                'ci_lo': None, 'ci_hi': None, 'label': '空格',
            }
            continue
        vm = VAL.search(rest)
        assert vm, f'unparsed row: {ln!r}'
        cells[_band(d, hp, pl, node)] = {
            'n': int(vm.group(1)), 'raw': float(vm.group(2)),
            'mono': float(vm.group(3)),
            'ci_lo': float(vm.group(4)), 'ci_hi': float(vm.group(5)),
            'label': None,  # 由 Part 8 标签节回填
        }

    # —— Part 8 标签段(含 Wilson 下限覆盖)+ 空格处置段 ——
    in_label = False
    fallbacks: dict[str, str] = {}
    in_fallback = False
    for ln in lines:
        if '逐格消费标签' in ln:
            in_label = True
            continue
        if in_label and '标签汇总' in ln:
            in_label = False
        if '空格处置(10 格)' in ln:
            in_fallback = True
            continue
        if in_fallback:
            if ln.strip().startswith('计数:'):
                in_fallback = False
                continue
            fm = re.match(
                r'^\s*(D[01])\s+(hp<=15|hp15-40|hp>40)\s+(P1|P2\+)\s+'
                r'(battle|encounter|boss|noncombat):\s*(.*)$', ln)
            if fm:
                d, hp, pl, node, _why = fm.groups()
                fallbacks[_band(d, hp, pl, node)] = ln.split(':', 1)[1].strip()
        if not in_label:
            continue
        m = re.match(
            r'^\s*(D[01])\s+(hp<=15|hp15-40|hp>40)\s+(P1|P2\+)\s+'
            r'(battle|encounter|boss|noncombat):\s*(.*)$', ln)
        if not m:
            continue
        d, hp, pl, node, rest = m.groups()
        key = _band(d, hp, pl, node)
        assert key in cells, f'label row without main row: {key}'
        cell = cells[key]
        if cell['label'] == '空格':
            continue
        if '可消费' in rest:
            cell['label'] = '可消费'
            wm = WILSON.search(rest)
            # 薄格 CI 下限强制取该格原始 n 的 Wilson 下限(不吃池化方差)——
            # 工件 Part 8 末行「强制取」= 无条件覆盖,单一源=标签行的 Wilson 值。
            # 历史注:v3.1 口径继承期本生成器曾写成「Wilson 低于 bootstrap 下限
            # 时才覆盖」的条件式,在唯一 bootstrap_lo(0.463)<Wilson(0.480) 的
            # 格上与工件「强制」字面分裂(IMPL_ADV_R194 症1),R194 修复批改
            # 无条件取,注释留痕不改回。
            if wm:
                cell['ci_lo'] = float(wm.group(1))
        elif '仅方向' in rest:
            cell['label'] = '仅方向'
        else:
            cell['label'] = '禁用'

    assert len(cells) == 48, f'expect 48 cells, got {len(cells)}'
    for key, cell in cells.items():
        if cell['label'] == '空格':
            assert key in fallbacks, f'empty cell without fallback: {key}'
            cell['fallback'] = fallbacks[key]
        else:
            assert cell['label'] in ('可消费', '仅方向', '禁用')
    summary = {'可消费': 0, '仅方向': 0, '禁用': 0, '空格': 0}
    for cell in cells.values():
        summary[cell['label']] += 1
    assert summary == {'可消费': 21, '仅方向': 0, '禁用': 17, '空格': 10}, summary

    out = {
        'meta': {
            'table': 'lambda_death_pl',
            'version': 'v3.3',
            'source': 'P51_V3_REBUILD.md v3.3 节运行产物 p51_v33_run.txt'
                      '(Part 3M 主表 + Part 8 标签/空格处置)',
            'key_dims': ['难度带(D0/D1,界 108)', '血带(hp<=15/hp15-40/hp>40)',
                         '位面(P1/P2+)', '节点(battle/encounter/boss/noncombat)'],
            'horizon': 'λ3 = 3 轮窗累积危险率',
            'notes': [
                '空格=表状态机第四态(空格≠域外≠损坏),fallback=表侧权威回退处置',
                '薄格 CI 下限已强制取该格原始 n 的 Wilson 下限(工件 Part 8 标签行;生成器 gen_pl_v33_json.py)',
                '旧 v3.1/v3.2 板面键表系对照存档,禁再被消费位引用',
            ],
        },
        'cells': cells,
    }
    DST.parent.mkdir(parents=True, exist_ok=True)
    DST.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f'[gen] wrote {len(cells)} cells -> {DST}')
    print(f'[gen] labels: {summary}')


if __name__ == '__main__':
    sys.exit(main())
