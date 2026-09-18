"""复盘骨架生成器(match-review 协议节点结构;T-153 起步,检测器预填面
已随 sim 重做退役)。

## 用途

逐局复盘的**骨架面**:按单局复盘协议
(``sr-od-currency-war-dev`` skill ``references/match-review.md`` §阶段 2)
生成骨架 markdown——逐节点(P×R×)小节、入口观察、决策循环动作摘要、
判定三槽占位,复盘者在骨架上补全板面/装备/锚等观察并逐节点填三槽。

与 ``replay_to_md.py`` 的分工:op 粒度完整渲染(两遍式 op 重建)归
该工具;本工具只辖骨架(节点级,op 行为占位),不重做 op 边界重建
——同一协议两个消费面,判据单一源在协议文档本身。

**可疑项预填面现状(如实申报)**:原版预填 = ``sim/checks/suspects.py``
检测器集对决策行全量检测、条目嵌对应节点判定三槽前;该检测器注册表
随 sim 重做 S10 删除面整体退役(现役 sim 为库形态 ``cw_sim_engine``,
无检查器注册表),本版生成纯骨架,每节点预填位 = 退役注记——可疑项
由复盘者按判定三槽自查;检测器注册表重建后在此恢复预填(用户原裁定
仍适用:检测结果禁汇成脱离节点语境的独立附录,禁改变逐节点结论结构)。

## 用法

    uv run python tools/cw/review_skeleton.py --decisions <decisions.jsonl> \
        [--run-id <rid>] [--out <骨架.md>]

零 src 导入(项目根直接跑)。输入形状自适应:行带 ``sim`` 键 = sim
批次账本行(直用);否则 = 生产决策帧(经本文件 ``merge_round_rows``
合并成账本同构形状的生产数据入口)。输出缺省 stdout,``--out`` 落盘。
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

#: 花费类动作白名单(合并行动作并集的入集判据)。卖出动作行(CwActionSellBenchParam)
#: 入并集供决策循环摘要的买卖对复核语境;生产 CwActionSellBenchParam 动作行缺
#: name/sell_reason 键(早期批)时摘要按缺键跳过,如实显示。
_SPEND_ACTION_TYPES = ('CwActionBuyCardParam', 'CwActionLevelUpParam', 'CwActionRefreshShopParam',
                       'CwActionSellBenchParam')


def merge_round_rows(rows: list[dict]) -> list[dict]:
    """生产决策帧(一帧一行,一轮多帧)→ 轮合并行(ledger 同构形状)。

    本函数原居 ``sim/ledger_hooks.py``,随其读侧检查族退役删除;本工具
    按其内联设计以原实现逐行等价补齐(原实现可自 git 历史该模块复活
    比对)。段级口径语义:

    合并口径:
    - gold/hp/gold_readable/hp_readable = 本轮**首帧**(决策时点;
      末帧 gold 已含本轮花销,拿去判「溢余未泄」会系统性偏小);
    - actions = 全帧**花费类**动作并集(CwActionBuyCardParam/CwActionLevelUpParam/CwActionRefreshShopParam/
      CwActionSellBenchParam;生产 CwActionStartBattleParam 等非花费动作不入);
    - formed_stop = 全帧或;
    - state = 首帧 state 派生:board→board_factions(engines 代理的
      生产同构键;生产 GameState 快照无 board_factions 键)、
      deployed/bench/level/cap 照抄;
    - sim.bench_full_skipped_buys = 任一帧 state.bench_full_flag 置 1
      (bench 满想买买不了的豁免面,生产无 sim 计数键,用旗标作保守
      镜像——旗标在 = 该轮存在满栏语境,宁豁免不误报)。
    排序按 (plane, round, ts);纯读,不改输入行。
    """
    merged: dict[tuple, dict] = {}
    for d in sorted(rows, key=lambda r: ((r.get('plane') or 0),
                                         (r.get('round_num') or 0),
                                         (r.get('ts') or ''))):
        pl = d.get('plane') or 1
        rn = d.get('round_num') or 0
        key = (pl, rn)
        st = d.get('state') or {}
        if key not in merged:
            merged[key] = {
                'plane': pl, 'round_num': rn,
                'gold': d.get('gold'),
                'gold_readable': d.get('gold_readable', True),
                'hp': d.get('hp'),
                'hp_readable': d.get('hp_readable', True),
                'formed_stop': bool(d.get('formed_stop')),
                'actions': [], 'target_comp': d.get('target_comp') or '',
                'state': {
                    'board_factions': dict(st.get('board') or {}),
                    'deployed': st.get('deployed') or [],
                    'bench': st.get('bench') or [],
                    'level': st.get('level'),
                    'cap': st.get('deploy_cap'),
                },
                'sim': {
                    'node': st.get('node_type') or '',
                    'bench_full_skipped_buys':
                        1 if st.get('bench_full_flag') else 0,
                },
            }
        else:
            m = merged[key]
            m['formed_stop'] = m['formed_stop'] or bool(d.get('formed_stop'))
            if d.get('target_comp'):
                m['target_comp'] = d['target_comp']
            if st.get('bench_full_flag'):
                m['sim']['bench_full_skipped_buys'] = 1
        merged[key]['actions'].extend(
            a for a in d.get('actions') or []
            if a.get('__type__') in _SPEND_ACTION_TYPES)
    return [merged[k] for k in sorted(merged)]


def load_rows(path: Path, run_id: str | None) -> tuple[list[dict], str]:
    """读档案行并按形状归一 → (账本行, 来源说明)。

    形状判据 = 行是否带 ``sim`` 键(sim 引擎轮装配写入;生产决策帧无)。
    生产帧走 merge_round_rows 合并。
    """
    rows_all = [json.loads(ln) for ln in
                path.read_text(encoding='utf-8').splitlines() if ln.strip()]
    if run_id:
        rows_all = [r for r in rows_all if r.get('run_id') == run_id]
    if not rows_all:
        raise SystemExit(f'档案无匹配行: {path} (run_id={run_id})')
    if 'sim' in rows_all[0]:
        rows = sorted(rows_all, key=lambda r: ((r.get('plane') or 1),
                                               (r.get('round_num') or 0)))
        return rows, f'sim 账本行 {len(rows)} 轮'
    # 生产决策帧:同 run 多帧一轮,合并成账本同构(生产入口)
    rids = {str(r.get('run_id')) for r in rows_all}
    if len(rids) > 1 and run_id is None:
        raise SystemExit(f'档案含 {len(rids)} 个 run,须 --run-id 点名: '
                         f'{sorted(rids)[:5]}')
    merged = merge_round_rows(rows_all)
    return merged, f'生产决策帧合并行 {len(merged)} 轮({next(iter(rids))})'


def _actions_summary(row: dict, cap: int = 12) -> str:
    """决策循环占位:动作序列摘要(归因键随行展示的行内上下文)。"""
    acts = row.get('actions') or []
    if not acts:
        return '(无决策行)'
    parts: list[str] = []
    for i, a in enumerate(acts, 1):
        if i > cap:
            parts.append(f'…共 {len(acts)} 笔')
            break
        bits = [f"#{i} {a.get('__type__')}"]
        card = a.get('card') or {}
        if card.get('name'):
            bits.append(str(card['name']))
        elif a.get('name'):
            bits.append(str(a['name']))
        for k in ('reason', 'sell_reason', 'channel', 'auth'):
            if a.get(k):
                bits.append(f'{k}={a[k]}')
        parts.append('(' + ' '.join(bits) + ')')
    return ' → '.join(parts)


def render_skeleton(rows: list[dict], source: str) -> str:
    """渲染骨架 markdown(协议 §阶段 2 节点结构;判定三槽占位)。"""
    lines: list[str] = []
    lines.append('# 单局复盘骨架(生成器预填)· match-review 协议')
    lines.append('')
    lines.append(f'> 来源: {source};检测器集已随 sim 重做退役,'
                 '本版为纯骨架(无可疑项预填,自查判定三槽)。')
    lines.append('> 复盘者须知: ①判定尺 = 玩法文档 + 在册用户裁定,'
                 '算法自洽≠合格;②产出零条「算法缺陷候选」= 复盘未完成。')
    lines.append('')
    lines.append('## 阶段 1 阅读理解(开工前提,按协议清单自检)')
    lines.append('- [ ] 玩法知识全读 / [ ] 注册表通读 / [ ] 在册裁定面取齐')
    lines.append('')
    lines.append('## 阶段 2 逐轮复盘')
    for row in rows:
        pl = row.get('plane') or 1
        rn = row.get('round_num') or 0
        node = (row.get('sim') or {}).get('node') or '未知节点'
        lines.append('')
        lines.append(f'### P{pl}·R{rn}（{node}）')
        lines.append('#### op 占位（按 journal op 行对齐——'
                     'match-review §阶段 2 op 边界重建规则）')
        lines.append(f'- 入口观察: 金{row.get("gold")} 血{row.get("hp")}'
                     f' 等级{(row.get("state") or {}).get("level")}'
                     f' 目标={row.get("target_comp") or "(未锁)"}'
                     '（板面/装备/锚等由复盘者补全）')
        lines.append(f'- 决策循环: {_actions_summary(row)}')
        lines.append('- **可疑项预填**: （检测器集退役,无预填;'
                     '由复盘者按本节点决策循环自查可疑形态)')
        lines.append('- 判定三槽（决策承载 op 必填）:')
        lines.append('  > 决策正确性: ')
        lines.append('  > 是否符合发展主线: ')
        lines.append('  > 备选与改进: ')
    lines.append('')
    lines.append('## 阶段 3 位面总结(三问收口)')
    lines.append('- 位面 1: 过渡阵容顺利凑出来了吗?')
    lines.append('- 位面 2: 阵容转型成功了吗?')
    lines.append('- 位面 3: 最终阵容顺利凑出来了吗?')
    lines.append('')
    lines.append('## 候选修复项(带证据链;单局归因=候选,跨局/sim 验证才定谳)')
    lines.append('')
    return '\n'.join(lines) + '\n'


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description='复盘骨架生成器(纯骨架;检测器预填面已退役)')
    ap.add_argument('--decisions', required=True,
                    help='decisions.jsonl 路径(sim 批次目录或生产 telemetry)')
    ap.add_argument('--run-id', default=None,
                    help='局 id(档案含多局时必填)')
    ap.add_argument('--out', default=None, help='输出 markdown 路径(缺省 stdout)')
    args = ap.parse_args(argv)
    rows, source = load_rows(Path(args.decisions), args.run_id)
    md = render_skeleton(rows, source)
    if args.out:
        Path(args.out).write_text(md, encoding='utf-8')
        print(f'骨架已写 {args.out}({len(rows)} 节点;'
              f'检测器集退役无预填)')
    else:
        print(md, end='')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
