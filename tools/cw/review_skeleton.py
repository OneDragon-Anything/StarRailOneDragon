"""复盘骨架生成器(T-153;match-review 协议节点结构 + 可疑项预填)。

## 用途

逐局复盘的**骨架与可疑项预填面**:对本局决策数据跑检测器集
(检测器集以 ``sim.checks.suspects._SUSPECT_DETECTORS`` 注册表实数
为准),生成按单局复盘协议
(``sr-od-currency-war-dev`` skill ``references/match-review.md`` §阶段 2)
组织骨架 markdown——逐节点(P×R×)小节、入口观察/决策循环占位、
**可疑项预填块插在对应节点小节的判定三槽之前**(复盘者做三槽判定
前必须先过本节点可疑项;用户裁定:检测结果禁汇成脱离节点语境的
独立附录,禁改变逐节点结论结构)。

与 ``replay_to_md.py`` 的分工:op 粒度完整渲染(两遍式 op 重建)归
该工具;本工具只辖骨架 + 检测器预填(节点级,op 行为占位),不重做
op 边界重建——同一协议两个消费面,判据单一源在协议文档本身。

## 用法

    uv run python tools/cw/review_skeleton.py --decisions <decisions.jsonl> \
        [--run-id <rid>] [--out <骨架.md>]

输入形状自适应:行带 ``sim`` 键 = sim 批次账本行(直用);否则 = 生产
决策帧(经本文件 ``merge_round_rows`` 合并成账本同构形状,
 的生产数据入口)。输出缺省 stdout,``--out``
落盘。
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from sr_od.application.currency_war.sim.checks.suspects import (
    MODE_NAMES,
    detector_ids,
    run_suspect_checks,
)

#: 花费类动作白名单(合并行动作并集的入集判据)。
# T-153:SellBench 并入合并行动作并集——D1(同轮买卖分键
# 复核)/D5(种子回卖辖域自算)检测器的生产覆盖面需要卖出动作行。
# 段级既有消费面核对:_seg_spent/__type__ 白名单(BuyCard/LevelUp/
# RefreshShop)与 check_overflow_gold_zero_buy_streak 花费判定均不含
# SellBench,并入零影响;生产 SellBench 动作行缺 name/sell_reason 键
# (slot 载体),检测器按缺键跳过并如实声明——join 通路属后续批。
_SPEND_ACTION_TYPES = ('BuyCard', 'LevelUp', 'RefreshShop',
                       'SellBench')


def merge_round_rows(rows: list[dict]) -> list[dict]:
    """生产决策帧(一帧一行,一轮多帧)→ 轮合并行(ledger 同构形状)。

    出处声明:本函数原居 ``sim/ledger_hooks.py``,随其读侧检查族在
    W3 波(账本 T-266)退役删除——本工具是未同步的残留消费面
    (legacy-hygiene-ops T-19 流程层缺口),按其内联设计以原实现
    逐行等价补齐于此;语义与实现单一源 =  生产数据
    入口(原实现可自 git 历史该模块复活比对)。

    段级检查的输入口径 = 一轮一行(sim 账本);生产 decisions.jsonl
    一轮 5-12 帧(pre-refresh/post-refresh/buy/deploy/equip 各一帧,
    每帧 gold 是决策时点金)。合并口径:
    - gold/hp/gold_readable/hp_readable = 本轮**首帧**(决策时点;
      与段级 ``_seg_gold0``「首波 gold」同口径——末帧 gold 已含本轮
      花销,拿去判「溢余未泄」会系统性偏小);
    - actions = 全帧**花费类**动作并集(BuyCard/LevelUp/RefreshShop
      + SellBench[T-153:D1/D5 检测器生产覆盖面;生产卖出行
      缺 name/sell_reason 键,检测器按缺键跳过];
      生产 StartBattle 等非花费动作(原 RunDeploy 组合壳随批2b 退役),
      不入——段级 ``_seg_spent`` 按 __type__ 白名单判,混入无害但
      并集只留花费类更省);
    - formed_stop = 全帧或;
    - state = 首帧 state 派生:board→board_factions(engines 代理的
      生产同构键;生产 GameState 快照无 board_factions 键)、
      deployed/bench/level/cap 照抄;
    - sim.bench_full_skipped_buys = 任一帧 state.bench_full_flag 置 1
      (bench 满想买买不了的段级豁免面,生产无 sim 计数键,用旗标
      作保守镜像——旗标在 = 该轮存在满栏语境,宁豁免不误报)。
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
    生产帧走 merge_round_rows 合并(检测器与 sim 检查器共用同签名)。
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
    """决策循环占位:动作序列摘要(检测器证据的行内上下文)。"""
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


def render_skeleton(rows: list[dict], entries: list[dict],
                    source: str) -> str:
    """渲染骨架 markdown(协议 §阶段 2 节点结构;预填块在三槽前)。"""
    # 定位索引:节点小节 → 条目(锚条目与交叉引用行分形态渲染);
    # 检测器异常面(_errors)只进头部注记,不落节点(禁独立附录)。
    by_node: dict[tuple[int, int], list[dict]] = {}
    det_errors: dict[str, str] = {}
    for e in entries:
        if e.get('mode') == '_errors':
            det_errors = dict(e.get('errors') or {})
            continue
        by_node.setdefault((e.get('plane') or 1,
                            e.get('round_num') or 0), []).append(e)
    lines: list[str] = []
    lines.append('# 单局复盘骨架(生成器预填)· match-review 协议')
    lines.append('')
    lines.append(f'> 来源: {source};检测器集 = sim/checks/suspects.py '
                 f'({", ".join(detector_ids())})。')
    if det_errors:
        lines.append(f'> ⚠ 检测器异常未计入: {det_errors}')
    lines.append('> 复盘者须知: ①判定尺 = 玩法文档 + 在册用户裁定,'
                 '算法自洽≠合格;②每节点先过「可疑项预填」再填三槽;'
                 '③产出零条「算法缺陷候选」= 复盘未完成。')
    lines.append('')
    lines.append('## 阶段 1 阅读理解(开工前提,按协议清单自检)')
    lines.append('- [ ] 玩法知识全读 / [ ] 注册表通读 / [ ] 在册裁定面取齐')
    lines.append('')
    lines.append('## 阶段 2 逐轮复盘')
    for row in rows:
        pl = row.get('plane') or 1
        rn = row.get('round_num') or 0
        node = (row.get('sim') or {}).get('node') or '未知节点'
        key = (pl, rn)
        lines.append('')
        lines.append(f'### P{pl}·R{rn}（{node}）')
        lines.append('#### op 占位（按 journal op 行对齐——'
                     'match-review §阶段 2 op 边界重建规则）')
        lines.append(f'- 入口观察: 金{row.get("gold")} 血{row.get("hp")}'
                     f' 等级{(row.get("state") or {}).get("level")}'
                     f' 目标={row.get("target_comp") or "(未锁)"}'
                     '（板面/装备/锚等由复盘者补全）')
        lines.append(f'- 决策循环: {_actions_summary(row)}')
        node_entries = by_node.pop(key, [])
        lines.append('- **可疑项预填**（检测器集自动生成,逐条裁决后删除标记）:')
        if node_entries:
            for e in node_entries:
                if e.get('cross_ref'):
                    lines.append(f'  - {e["detail"]}')
                else:
                    lines.append(f'  - {e["detail"]}'
                                 f' [{e.get("mode")}: {e.get("mode_name")}]')
        else:
            lines.append('  - （本节点无检测器命中条目）')
        lines.append('- 判定三槽（决策承载 op 必填）:')
        lines.append('  > 决策正确性: ')
        lines.append('  > 是否符合发展主线: ')
        lines.append('  > 备选与改进: ')
    # 索引里还剩条目 = 其坐标行不在本局行集(理论上只有裁剪局发生);
    # 只在头部注记计数,不渲染独立附录(用户裁定禁附录清单)。
    if by_node:
        lines.append('')
        lines.append(f'> ⚠ {sum(len(v) for v in by_node.values())} 条条目'
                     '坐标不在行集内(行集裁剪局),已丢弃未渲染。')
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
    ap = argparse.ArgumentParser(description='复盘骨架生成器(T-153)')
    ap.add_argument('--decisions', required=True,
                    help='decisions.jsonl 路径(sim 批次目录或生产 telemetry)')
    ap.add_argument('--run-id', default=None,
                    help='局 id(档案含多局时必填)')
    ap.add_argument('--out', default=None, help='输出 markdown 路径(缺省 stdout)')
    args = ap.parse_args(argv)
    rows, source = load_rows(Path(args.decisions), args.run_id)
    entries = run_suspect_checks(rows)
    n_suspects = sum(1 for e in entries if not e.get('cross_ref')
                     and e.get('mode') != '_errors')
    md = render_skeleton(rows, entries, source)
    if args.out:
        Path(args.out).write_text(md, encoding='utf-8')
        print(f'骨架已写 {args.out}'
              f'({n_suspects} 条可疑项 / {len(rows)} 节点;检测器 '
              f'{len(detector_ids())} 个={",".join(MODE_NAMES)})')
    else:
        print(md, end='')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
