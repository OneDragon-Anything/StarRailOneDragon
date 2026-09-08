"""决策回放 harness(r98 建立;r359 升级支持 v2 态忠实还原;ADR-0336
删除 LineStrategy 后仅支持 decision_v2/default 两栈)。

用途:策略改动后,对**历史局的 GameState 快照**重放商店决策
(decide_shop_screen 黑板接口,W971 sim 适配批起),秒级看到
「这个改动动了哪些决策、方向对不对」——验证成本从实跑 20-40min 压到秒级,
"每刀都实跑验证"从此经济可行(bug 无存活空间的前提)。

数据源:replay/decisions.jsonl 的 state 字段(每备战轮的 GameState 快照)。

用法:
  uv run python -m sr_od.application.currency_war.sim.cw_replay \
      [--run ID] [--rounds N] [--diff] [--strategy decision_v2|default]
  --diff:与当时实跑 actions 对比(改动效果 = 与基线的分歧行)
  --strategy decision_v2(默认,现行生产 v2)/ default(内置 v1 打法)

⚠️ 结论边界(必须自持,防过度解读):
- **分歧 ≠ 变好/变差,只 = 行为漂移**。obs 序列是当时策略产生的,
  新策略分歧后游戏演化路径分叉,后续对比是「旧世界 state vs 新策略
  反应」——这正是回归测试要的(同局面不退化),不是胜率指标。
- 首发分歧 vs 级联分歧:第 k 回合分歧会改变重放 session 的演化,
  后续分歧可能是连锁——报告标首发点,判读从首发点看起。
- 低置信回合(hp_readable=False 等)的对比结论打 ⚠(兜底毒值)。

LIMITS(诚实边界):
- 旧记录(decision_v2 前)无 v3_* 态 → 重放的意向/演进 latch 从
  默认态演化(增量演化式),分支可能与实跑不同——判读聚焦购买/升级
  动作族,分支级分歧看新采集的局。
- target/commit 层不重算(target 用快照当时值);deployed 按快照
  重建(含 star/equips——r358 三维判读所需)。
"""
from __future__ import annotations

import json
import sys

from sr_od.application.currency_war.kernel.cw_observe import DEFAULT_REPLAY_DIR
from sr_od.application.currency_war.kernel.cw_state import (  # ADR-0392 helper 导入
    BenchChar,
    GameState,
    ShopCard,
    bench_from_compact,
    deployed_from_compact,
    iter_occupied_deployed,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.mandate_state import (
    state_of,
)


class _Cfg:
    faction_priority: list[str] = ['仙舟', '列车同行', '持续伤害', '护盾', '治疗']


def _rebuild_state(snap: dict) -> GameState:
    """decisions.jsonl 的 state dict → GameState(字段名一致,dataclass 直灌)。"""
    st = GameState()
    for k in ('gold', 'hp', 'level', 'plane', 'round_num', 'node_type',
              'streak', 'shop_refresh_cost', 'level_up_cost',
              'enemy_difficulty', 'enemy_difficulty_live', 'active_env'):
        v = snap.get(k)
        if v is not None:
            setattr(st, k, v)
    _xp = snap.get('xp_progress')
    st.xp_progress = tuple(_xp) if _xp else None
    st.board = dict(snap.get('board') or {})
    st.shop = [ShopCard(x=c.get('x', 0), faction=c.get('faction') or '?',
                        name=c.get('name') or '', cost=c.get('cost') or 1,
                        star=c.get('star') or 1,
                        merge_preview=c.get('merge_preview') or 0)
               for c in (snap.get('shop') or []) if isinstance(c, dict)]
    def _bc(b: dict, i: int) -> BenchChar:
        return BenchChar(slot=b.get('slot') or i + 1,
                         char_id=b.get('char_id') or '',
                         faction=b.get('faction') or '?',
                         star=b.get('star') or 1,
                         position_pref=b.get('position_pref') or 'back')
    # ADR-0316:历史快照是紧缩序,经 bench_from_compact 转槽位表
    # (slot 带 1-based 槽号时按槽放置,否则顺序放置)
    st.bench = bench_from_compact([
        _bc(b, i) for i, b in enumerate(snap.get('bench') or [])
        if isinstance(b, dict)])
    # r359:deployed 重建(formation 检查点/star/equips 消费;r358 三维)
    # ADR-0392:历史快照是紧缩序,经 deployed_from_compact 转槽位表
    st.deployed = deployed_from_compact(
        [_bc(b, i) for i, b in enumerate(snap.get('deployed') or [])
         if isinstance(b, dict)])
    for c in iter_occupied_deployed(st.deployed):
        c.equips = list(c.equips or [])
    st.dual_track_phase = bool(snap.get('dual_track_phase'))
    return st


def _fmt(actions: list) -> str:
    from sr_od.application.currency_war.kernel.cw_state import LevelUp
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


def _divergence_kind(new_acts: list, old_acts: list) -> str:
    """分歧分桶(三桶+兜底;意图标注靠人,桶先分好)。"""
    from sr_od.application.currency_war.kernel.cw_state import LevelUp

    def _bag(acts, key):
        from collections import Counter
        return Counter(key(a) for a in acts)
    new_buys = {getattr(getattr(a, 'card', None), 'name', '') for a in new_acts
                if type(a).__name__ == 'BuyCard'}
    old_buys = {(a.get('card') or {}).get('name', '') for a in old_acts
                if a.get('__type__') == 'BuyCard'}
    if new_buys != old_buys:
        return '买不同卡'
    if (sum(1 for a in new_acts if type(a).__name__ == 'RefreshShop')
            != sum(1 for a in old_acts if a.get('__type__') == 'RefreshShop')):
        return '刷vs不刷'
    # LevelUpShop(商店屏新词表,is-a LevelUp)与账本 'LevelUp' 同桶
    if (sum(1 for a in new_acts if isinstance(a, LevelUp))
            != sum(1 for a in old_acts if a.get('__type__') == 'LevelUp')):
        return '升级分歧'
    return '其他'


def _restore_session(strat, d: dict, sess):
    """从 trace 行恢复 session 态(两策略共用;缺字段=旧记录,走默认)。

    (session.md §2.5 退役前置动作:原 ``sess.dual_track_phase`` 恢复写行
    已随职责分离切换删除——该字段无消费面,恢复语义消失 = 退役语义的
    一部分,显式声明非静默。)
    """
    _ms = state_of(sess)
    _ms.transition_framework = d.get('sess_framework', '') or ''
    if d.get('sess_drought') is not None:
        _ms.target_drought = int(d['sess_drought'])
    if d.get('sess_active_env'):
        sess.active_env = str(d['sess_active_env'])
    # 持卡注入面回读(ADR-0598):decisions 行 top-level active_strategies
    # → session——息帽 resolved 链的输入源,不回读则持卡局重放恒按 base
    # cap 决策(修复效果在重放中结构性不可见)。空行(旧档案/无持卡局)
    # 不写,session 缺省 [] 零漂移。
    if d.get('active_strategies'):
        sess.active_strategies = list(d['active_strategies'])
    _cs = d.get('sess_commit_scores') or {}
    if _cs:
        from sr_od.application.currency_war.kernel.cw_transition import CommitSignals
        if not isinstance(_ms.commit_signals, CommitSignals):
            _ms.commit_signals = CommitSignals()
        _ms.commit_signals.scores = {k: float(v) for k, v in _cs.items()}


def main() -> None:
    sys.stdout.reconfigure(encoding='utf-8')  # type: ignore[attr-defined]
    args = sys.argv[1:]
    run_id = ''
    rounds = 0
    diff = False
    strategy = 'decision_v2'
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
        elif args[i] == '--strategy':
            strategy = args[i + 1]
            i += 2
        else:
            i += 1

    if strategy in ('mandate_v1', 'decision_v2'):
        # decision_v2 字符串 = 历史档案别名(语料 strategy_id 语义),重放走活核 mandate_v1
        from sr_od.application.currency_war.strategies.impl.mandate_v1.bridge import (
            MandateV1Strategy,
        )
        strat = MandateV1Strategy()
        sess = strat.create_session(_Cfg())
    else:
        # default 栈本体已退役:旧语料(default 栈时代 decisions.jsonl)回放
        # 只走冻结快照 worktree(回退参照=迁移批 3(ADR-0465) tag 的干净 worktree),主仓
        # 不再提供 default 臂——惰性 import 回退已删,防「首次使用才炸」。
        raise SystemExit(
            f"strategy='{strategy}' 不受支持:default 栈已退役。"
            "旧 default 语料回放请用冻结快照 worktree(批 3 tag 干净检出)"
            "执行本脚本;decision_v2 语料回放用 --strategy decision_v2")

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
    print(f'=== 决策回放 {rid} [strategy={strategy}] ===')
    if diff:
        print('⚠ 边界:分歧 ≠ 变好/变差,只 = 行为漂移(回归测试语义,'
              '非胜率裁判);级联分歧看首发点。')

    first_div = True
    div_kinds: dict[str, int] = {}
    for n_done, k in enumerate(sorted(best)):
        if rounds and n_done >= rounds:
            break
        d = best[k]
        snap = d.get('state') or {}
        st = _rebuild_state(snap)
        _restore_session(strat, d, sess)
        low_conf = (d.get('hp_readable') is False
                    or snap.get('gold_readable') is False)
        try:
            # W971 sim 适配批:回放决策同样切黑板新接口(与 sim 引擎/生产
            # 同路);帧 = 重建的快照态。LevelUpShop 渲染归一见 _fmt。
            sess.shop_state_frame = st
            actions = strat.decide_shop_screen(sess, _Cfg())
            new_s = _fmt(actions)
        except Exception as e:
            new_s = f'⚠ plan 异常: {type(e).__name__}: {e}'
        if diff:
            old_s = _fmt_json(d.get('actions') or [])
            mark = '  ' if new_s == old_s else '≠ '
            if mark.strip():
                kind = _divergence_kind(actions or [], d.get('actions') or [])
                div_kinds[kind] = div_kinds.get(kind, 0) + 1
                tag = f'[{kind}]'
                if first_div:
                    tag += ' ←首发分歧'
                    first_div = False
                conf = ' ⚠低置信' if low_conf else ''
                print(f"{mark}p{k[0]}r{k[1]} g={d.get('gold')}{conf} {tag}")
                print(f"     旧: {old_s}")
                print(f"     新: {new_s}")
            elif low_conf:
                print(f"  p{k[0]}r{k[1]} (一致,低置信) g={d.get('gold')}")
        else:
            conf = ' ⚠低置信' if low_conf else ''
            print(f"  p{k[0]}r{k[1]} g={d.get('gold')}"
                  f" tgt={d.get('target_comp')}{conf}: {new_s}")
    if diff and div_kinds:
        print(f'— 分歧分布: {div_kinds}')


if __name__ == '__main__':
    main()
