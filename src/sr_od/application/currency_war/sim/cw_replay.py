"""决策回放 harness(journal 新账源,ADR-0630 判读走新账)。

用途:策略改动后,对**历史局的容器真值帧**重放商店决策
(decide_shop_screen 黑板接口),秒级看到「这个改动动了哪些决策、
方向对不对」——验证成本从实跑 20-40min 压到秒级。

数据源:state/journal.jsonl(统一 state 状态流水,行行自足)——按
(run, plane, round) 取每轮最后一次写入的行内 state 快照,经
:func:`restore_state_snapshot` 恢复进容器后决策。旧 decisions.jsonl
源与其 CwSimFrame 重建/会话恢复面已随本切源退役(该流写入端已随删除
波 1 停写,读死数据;退役面 = _rebuild_state/_restore_session/--diff
分歧对比/意向 latch 回读/执行态可信位回读,归 git 历史)。

用法:
  uv run python -m sr_od.application.currency_war.sim.cw_replay \
      [--run ID] [--rounds N]
  不传 --run:回放全部 run(按轮键排序跨局遍历,打警示头)。

⚠️ 结论边界(判读语义,切源后如实申报):
- **意向/锁线冷启动**:策略态(意向 latch/锁定配方对/经验期望账本)
  不入状态流水,journal 源回放每轮冷建 session——方向层按容器帧键
  自驱,锁线延续性语义与实跑不可比;分支级(锁线相关)决策对比需
  旧格式语料 + 冻结快照 worktree(历史档案考古走 git 历史)。
- 轮真值 = 该轮最后一次容器写入的快照(备战决策帧语境;战斗/结算
  中间态不构成独立轮)。
"""
from __future__ import annotations

import sys

from sr_od.application.currency_war.kernel.cw_game_state import (
    GameState,
    board_state_of,
    gold_of,
    node_kind_of,
    restore_state_snapshot,
)
from sr_od.application.currency_war.kernel.cw_observe import DEFAULT_REPLAY_DIR
from sr_od.application.currency_war.telemetry.journal_query import (
    read_journal,
    round_state_snapshots,
)


class _Cfg:
    faction_priority: list[str] = ['仙舟', '列车同行', '持续伤害', '护盾', '治疗']


def _fmt(actions: list) -> str:
    from sr_od.application.currency_war.kernel.cw_vocab import LevelUp
    parts = []
    for a in actions:
        t = type(a).__name__
        if t == 'BuyCard':
            parts.append(f"Buy({a.card.name})")
        elif isinstance(a, LevelUp):   # LevelUpShop(商店屏新词表)同渲染为 LvUp
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
    i = 0
    while i < len(args):
        if args[i] == '--run':
            run_id = args[i + 1]
            i += 2
        elif args[i] == '--rounds':
            rounds = int(args[i + 1])
            i += 2
        else:
            i += 1

    # 单一策略臂 = mandate_v1(统一迁移批 A9 裁决:与实机/sim 同源;
    # decision_v2 字符串 = 历史档案别名,接受但同路)。
    from sr_od.application.currency_war.strategies.impl.mandate_v1.bridge import (
        MandateV1Strategy,
    )
    strat = MandateV1Strategy()

    rows = read_journal(DEFAULT_REPLAY_DIR)
    snaps = round_state_snapshots(rows, run_id)
    if not run_id:
        runs = {k[0] for k in snaps}
        print(f'⚠ 未指定 --run:回放对象 = {len(runs)} 个 run 的轮键排序'
              '遍历(跨局非单局连续演化;单局判读请加 --run <run_id>)')
    elif not snaps:
        print(f'⚠ --run {run_id} 在状态流水无轮快照(id 不存在,'
              '或该段已被滚动清理——journal.retirement.jsonl 显影)')
        return
    print(f'=== 决策回放(journal 源){run_id or "(全部 run)"} ===')

    for n_done, key in enumerate(sorted(snaps)):
        if rounds and n_done >= rounds:
            break
        rid, plane, rnd = key
        # 每轮冷建 session(策略态不入流水;判读边界见模块 docstring),
        # 快照恢复进该 session 的容器后走生产同路决策。
        sess = strat.create_session(_Cfg())
        bs: GameState = board_state_of(sess)
        restore_state_snapshot(bs, snaps[key])
        try:
            actions = strat.decide_shop_screen(sess, _Cfg())
            plan = _fmt(actions)
        except Exception as e:
            plan = f'⚠ plan 异常: {type(e).__name__}: {e}'
        hp = bs.hp.value
        kind = node_kind_of(bs) or ''
        print(f'  p{plane}r{rnd} g={gold_of(bs)} hp={hp} node={kind}'
              f' [{rid}]: {plan}')


if __name__ == '__main__':
    main()
