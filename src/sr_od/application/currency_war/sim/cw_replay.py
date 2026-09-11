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
  不传 --run:回放对象 = 全档案跨 run 拼接体(打警示头);fake_ 前缀
  run(测试注入数据)恒过滤,防污染 best 基准(T-291 判读卫生)。

⚠️ 结论边界(必须自持,防过度解读):
- **分歧 ≠ 变好/变差,只 = 行为漂移**。obs 序列是当时策略产生的,
  新策略分歧后游戏演化路径分叉,后续对比是「旧世界 state vs 新策略
  反应」——这正是回归测试要的(同局面不退化),不是胜率指标。
- 首发分歧 vs 级联分歧:第 k 回合分歧会改变重放 session 的演化,
  后续分歧可能是连锁——报告标首发点,判读从首发点看起。
- 低置信回合(hp_readable/gold_readable=False)的对比结论打 ⚠:
  读数缺失帧的 state 存的是当时读数而非兜底毒值(历史档案逐行核伪),
  ⚠ 只降该行判读置信,不改决策输入。

LIMITS(诚实边界):
- 意向 latch 回读面:v3_intention dict 在案的行回读恢复锁线/配方对/
  派生方向 target 物化(物化与 flow 方向刷新派生视图同式同源,
  T-290),锁定后帧的分支级决策可比;仅 v3_intention=None 的行
  (旧记录/无意向帧)意向仍从默认态演化——该类行分支级分歧看
  新采集的局。
- target/commit 层不重算(target 用快照当时值);deployed 按快照
  重建(含 star/equips——r358 三维判读所需)。
"""
from __future__ import annotations

import json
import sys
from typing import TYPE_CHECKING

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

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_intention import IntentionState


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


def _intention_from_trace(v: dict) -> IntentionState:
    """trace 行 ``v3_intention`` dict → IntentionState(回放恢复面反序列化)。

    是 telemetry/knowledge/cw_serialize.serialize_intention 的反向:
    容器形状还原(list→tuple/set、tracks 子 dict→LineTrack、锁时机
    计数 int 化),其余标量直灌。宽容读法:缺字段走 dataclass 缺省、
    当前类不认识的键忽略——档案跨 schema 版本不炸;LineTrack 子键
    同式过滤(旧档案少键/新档案多键均合法)。
    """
    from dataclasses import fields as _dc_fields

    from sr_od.application.currency_war.kernel.cw_intention import (
        IntentionState,
        LineTrack,
    )
    ist = IntentionState()
    _tuple_keys = {'p1_pair', 'transition_pair', 'p1_pair_frozen_obs',
                   'p1_pair_frozen_pair', 'p1_pair_refreeze_hold'}
    _set_keys = {'evicted', 'pair_evicted'}
    _int_keys = {'lock_layer', 'lock_plane', 'lock_round'}
    _track_keys = {f.name for f in _dc_fields(LineTrack)}
    for name, val in v.items():
        if not hasattr(ist, name):
            continue
        if name == 'tracks':
            setattr(ist, name, {
                k: LineTrack(**{kk: vv for kk, vv in t.items()
                                if kk in _track_keys})
                for k, t in (val or {}).items() if isinstance(t, dict)})
        elif name in _set_keys:
            setattr(ist, name, set(val or ()))
        elif name in _tuple_keys:
            setattr(ist, name, tuple(val or ()))
        elif name in _int_keys:
            setattr(ist, name, int(val or 0))
        else:
            setattr(ist, name, val)
    return ist


def _materialize_target_comp(ist: IntentionState,
                             state: GameState | None) -> object:
    """意向态 → target comp 物化(回放侧补实跑「方向刷新派生视图」产物)。

    实跑中 ``flow._refresh_direction_views`` 在 prep 入口把意向物化为
    ``state_of(session).target_comp``;回放只调商店决策核、不跑方向
    刷新,故由本函数补同一拍产物。派生式与彼处逐字同构(get_comp
    locked 优先;P1 无 comp 锁按 p1_pair ∪ p1_early_pair 物化配方伪
    comp)且复用同一派生源函数,禁第二实现。P1 面辖域判定需快照
    plane,state 缺失时整段 P1 面(配方对/early)跳过——只回退
    locked_comp 硬源;调用序上黑板须先于本函数就位。
    """
    from sr_od.application.currency_war.kernel.cw_comps import get_comp
    from sr_od.application.currency_war.kernel.cw_intention import (
        p1_early_pair,
        pair_target_comp,
    )
    comp = get_comp(ist.locked_comp) if ist.locked_comp else None
    if comp is None and state is not None \
            and int(getattr(state, 'plane', 1) or 1) == 1:
        pair = tuple(getattr(ist, 'p1_pair', ()) or ()) \
            or p1_early_pair(state, ist)
        if pair:
            comp = pair_target_comp(pair)
    return comp


def _restore_session(strat, d: dict, sess) -> None:
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
    # v3 意向 latch 回读(T-290):行携 v3_intention dict(serialize_intention
    # 全量序列化,锁定真值在案)→ IntentionState + target 物化。实跑中
    # 意向由方向刷新逐步置位、回放无该输入源——不回读则锁定/聚焦帧的
    # 分支级决策(买什么卡/买不买)与实跑结构性不可比(消歧正本 =
    # .debug/temp/currency_war/T-286-交付报告.md §3)。None 行(旧记录/
    # 无意向帧)不写,维持默认态演化;此时以行携顶层 target 标签
    # (locked_comp 或「过渡配方·A+B」形态)作残源解析,解析失败(旧
    # 命名/注册表缺项)= None 诚实缺省。
    _vi = d.get('v3_intention')
    if isinstance(_vi, dict):
        _ms.v3_intention = _intention_from_trace(_vi)
        _ms.target_comp = _materialize_target_comp(
            _ms.v3_intention, getattr(sess, 'shop_state_frame', None))
    elif d.get('target_comp'):
        from sr_od.application.currency_war.kernel.cw_comps import get_comp
        from sr_od.application.currency_war.kernel.cw_intention import (
            pair_target_comp,
        )
        _lbl = str(d['target_comp'])
        if _lbl.startswith('过渡配方·'):
            _ms.target_comp = pair_target_comp(
                tuple(_lbl.removeprefix('过渡配方·').split('+')))
        else:
            _ms.target_comp = get_comp(_lbl)


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
    # 每个 (plane,round) 取 actions 最多的一条(= plan 真值帧);
    # fake_ 前缀 run = 测试注入数据(T-291 判读卫生,schema 可能异常且
    # 动作非真实局产物),恒过滤防混入 best 基准与拼接体。
    best: dict = {}
    last_run = ''
    real_runs: set[str] = set()
    fake_rows = 0
    with open(rep / 'decisions.jsonl', encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue
            d = json.loads(line)
            row_run = str(d.get('run_id', ''))
            if row_run.startswith('fake_'):
                fake_rows += 1
                continue
            real_runs.add(row_run)
            last_run = row_run
            if run_id and row_run != run_id:
                continue
            k = (d.get('plane'), d.get('round_num'))
            if k not in best or len(d.get('actions') or []) > len(best[k].get('actions') or []):
                best[k] = d
    if not run_id:
        print(f'⚠ 未指定 --run:回放对象 = {len(real_runs)} 个 run 的跨局'
              '拼接体(best 按 (plane,round) 全档案取动作最多行,非单局'
              f'决策序列;已过滤 fake_ 测试行 {fake_rows} 行;'
              '单局判读请加 --run <run_id>)')
    elif not best:
        print(f'⚠ --run {run_id} 在档案中无真实回放行(id 不存在,'
              '或为 fake_ 测试数据已被过滤)')
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
        # 黑板先于意向回读就位:target 物化的 early 面需读快照板面
        #(p1_early_pair 派生输入),调用序不可倒置。
        sess.shop_state_frame = st
        _restore_session(strat, d, sess)
        low_conf = (d.get('hp_readable') is False
                    or snap.get('gold_readable') is False)
        try:
            # W971 sim 适配批:回放决策同样切黑板新接口(与 sim 引擎/生产
            # 同路);帧 = 重建的快照态。LevelUpShop 渲染归一见 _fmt。
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
