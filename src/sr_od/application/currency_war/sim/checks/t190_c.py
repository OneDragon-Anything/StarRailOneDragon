"""批 C 检查项(C-A1..A4;只审计,修法按归属路由)。

设计正本 = 批 C 定义结论(同录 ADR-0627)。实现
基线 = 批 B commit 84a484e97(收窄谓词三落点 + ``press_narrowed_
transition_domain`` 族分键)。四项全部为批级检查,消费 full_ledgers
(P1+P2 全行;判据辖 P2 转化链域,P1 段截断口径会把 P2 行别名截掉——
同 ADR-0629 ``second_engine_deadline`` 的 full_ledgers 先例)。

- C-A1 :func:`check_t190_c1_bench_clog_attribution` 腾席链失效形态
  枚举 + 死库存卡容分类账(core 拒帧逐帧归因;验收锚 = 零未归因);
- C-A2 :func:`check_t190_c2_new_buy_swap_coverage` 新购件覆盖复查
  (新购档关键件「买入帧→计划点」swap 计划候选覆盖;验收锚 = 结论
  可裁回账本:强信号缺口归零裁 done,有缺口进修复面);
- C-A3 :func:`check_t190_c3_exemption_fire` 豁免集开火性(m2_*/C1
  解封轮买入率 >0;hub 空开火面独立申报禁并桶;验收锚 = 非零或空面
  申报);
- C-A4 :func:`check_t190_c4_funnel_reconcile` 转化漏斗遥测检查器
  (买因闭集全键对账 × fate 键 × 收窄分键;验收锚 = 与 decisions
  账本逐位配平)。

**P89 一致性边界(批 C 实施纪律)**:P89 换血预算预注册线 0.75 次/轮
已正式判定 FAIL(复测批 s8550 定谳),属申报内现状(设计机制载体本就不含第二套换血机器)——本模块
四项不读、不判、不引该线,不复活已定谳关闭的换血预算线。

**数据面近似声明(四项共通)**:生产资格排除集(sell_gate 统一装配 A:
T3 垫保活跃名 / 锁定采购集全量 / visit 窗口语义细节)含账本不可见面,
本模块的分类是**候选级镜像**而非生产判定复算——凡因近似产生的发现
一律命名「候选/dispute」交判读,不构成对生产行为的定谳;精确门序以
策略侧计数键为准(shop_unbought_reasons 同款「拒因串是判读线索非审
计账」边界)。按名多集记账不辨同名跨渠道副本(FIFO 归属);C-A1 渠
道标签跨位面携带,但 fresh 窗口只在 P2 段内计算(P1/P2 轮号段内重
计,跨面轮序不可辨)。
"""

from __future__ import annotations

from collections import Counter

from sr_od.application.currency_war.kernel.cw_card_identity import (
    transition_release_names,
)
from sr_od.application.currency_war.kernel.cw_comps import get_comp
from sr_od.application.currency_war.strategies.impl.mandate_v1.sell_gate import (
    LAUNCH_CAUSE_BY_ARM,
)

#: 收窄分键三键族(批 B 落码;单一源 = shop.py/mandate.py 发射位字面,
#: 本元组 = 检查器侧镜像,值漂移由 test_cw_press_narrow_transition 锁暴露)。
NARROW_KEYS: tuple[str, ...] = (
    'press_narrowed_transition_domain',
    'press_narrowed_transition_domain_hub',
    'press_narrowed_transition_domain_prep_seen',
)

#: S_spec 收窄集(设计 v2 §3.1 窄口径;批 B PRESS_NARROWED_ARMS 同源镜像)。
S_SPEC_ARMS: frozenset[str] = frozenset({'dominance_buy', 'hub_option_buy'})

#: 义务买入臂(新购档关键件的合法通道;C1/④ 为囤入通道不上板,
#: 不入 C-A2 分母——shop.py C1 注「动作形态默认 = 囤(bench 持有,
#: 不上场)」)。
_OBLIGATION_ARMS = frozenset({'m2_line_member', 'm2_locked_member'})

#: ③④持有件渠道(账本可见的 hold 类买因;ADR-0580 权限模型排除面)。
_HOLD_ARMS = frozenset({'core_single_card_buy', 'core_single_card_buy:unlocked',
                        'transition_component_buy', 'hub_option_buy'})

#: 义务/素材渠道(m2 族:M2 义务买入与合成素材买入,皆非燃料类)。
_OBLIGATION_FAMILY = frozenset({'m2_line_member', 'm2_locked_member',
                                'm2_stockpile', 'm2_merge_completion'})

#: 种子/visit 窗口宽(L1 同轮硬面 + P78-7 种子年龄相邻轮的账本可见
#: 近似 = 买入轮 ∈ {当前轮, 前一轮};visit 窗口 ≈ 备战轮一一对应)。
_FRESH_WINDOW_ROUNDS = 1

_DISPUTE_NOTE = (
    '候选级发现非定谳:生产排除集含账本不可见面(T3 垫保活跃名/锁定'
    '采购集全量),逐帧判读先查垫保登记面再定修法路由'
    '(P78/P41 卖面 → 卖出资格仲裁线;可上性 → 锁线转型域线)')


def _bench_used(state: dict) -> int:
    return sum(1 for b in (state.get('bench') or []) if b)


def _deployed_names(state: dict) -> list[str]:
    return [(d or {}).get('char_id') or '' for d in
            (state.get('deployed') or []) if d is not None]


def _bench_names(state: dict) -> list[str]:
    return [(b or {}).get('char_id') or '' for b in
            (state.get('bench') or []) if b is not None]


# ====================================================================
# --- C-A1 腾席链失效形态枚举 + 死库存卡容分类账 ----------------------
# ====================================================================

#: 占席分类桶闭集(逐件主标签,优先序 = 列表序;账本可见近似面)。
#: sellable_fuel 判据对齐生产燃料物理谓词(mandate.fuel_sell_candidates):
#: 1★ ∧ 非线名单 ∧ 非 ④放行集 carry/partial ∧ 非合成素材 ∧ 非带装备
#: (后台效果资格的注册表维账本不可见,以装备非空为代理,近似申报)。
_C1_BUCKETS: tuple[str, ...] = (
    'roster_line',        # 义务基座:名 ∈ comp core∪shared(线名单)
    'obligation_bought',  # m2 族义务/素材买入且仍持有(P2 段台账)
    'transition_pack',    # ④放行集 carry/partial(设计 §七-4 主发现面)
    'hold_channel',       # ③④持有件:C1/④/hub hold 类买入且仍持有
    'merge_material',     # 合成素材:同名副本在场且同星
    'effect_carrier',     # 带装备件(后台效果资格的代理维)
    'fresh_seed_window',  # 本轮/相邻轮买入(L1 同轮 + 种子年龄近似)
    'star2_plus',         # 2★+:非 1★ 全额退域,物理非燃料
    'sellable_fuel',      # 裸燃料候选(以上皆非 = 生产腾席 victim 形态)
)


def _transition_pack_names() -> frozenset[str]:
    """④放行集名集(单一源 = kernel.transition_release_names,即
    TRANSITION_PACK 档 ∈ {carry, partial},drop 档不放行;与 shop.py
    ④腿同源。桶依赖矩阵禁 sim→knowledge 直连,经 kernel 访问)。"""
    return transition_release_names()


def _c1_classify_bench(state: dict, roster: frozenset[str],
                       pack_names: frozenset[str],
                       held_tags: dict[str, set[str]],
                       buy_round: dict[str, int],
                       round_num: int) -> Counter:
    """逐占席件主标签计数(优先序 = _C1_BUCKETS 列表序)。

    ``held_tags[name]`` = 该名 P2 段在册买因渠道标签集
    (obligation/hold),``buy_round[name]`` = 最近买入轮号;由
    :func:`_c1_held_tags` 从 actions 流维护。
    """
    bench_chars = [b for b in (state.get('bench') or []) if b]
    dep = _deployed_names(state)
    bench = [b.get('char_id') or '' for b in bench_chars]
    copies = Counter(dep) + Counter(bench)
    star_of: dict[str, set[int]] = {}
    for c in bench_chars + [d for d in
                            (state.get('deployed') or []) if d is not None]:
        star_of.setdefault(c.get('char_id') or '', set()).add(
            int(c.get('star') or 1))
    out: Counter = Counter()
    for c in bench_chars:
        name = c.get('char_id') or ''
        tags: set[str] = set()
        if name in roster:
            tags.add('roster_line')
        ht = held_tags.get(name) or set()
        if 'obligation' in ht:
            tags.add('obligation_bought')
        if name in pack_names:
            tags.add('transition_pack')
        if 'hold' in ht:
            tags.add('hold_channel')
        if copies.get(name, 0) >= 2 and len(star_of.get(name) or ()) == 1:
            tags.add('merge_material')
        if (c.get('equips') or []):
            tags.add('effect_carrier')
        br = buy_round.get(name)
        if br is not None and round_num - br <= _FRESH_WINDOW_ROUNDS:
            tags.add('fresh_seed_window')
        if int(c.get('star') or 1) != 1:
            tags.add('star2_plus')
        if not tags:
            tags.add('sellable_fuel')
        out[next(b for b in _C1_BUCKETS if b in tags)] += 1
    return out


def _c1_held_tags(rows: list[dict], row: dict) -> tuple[dict, dict]:
    """(held_tags, buy_round):截至本行的在册买入渠道标签与最近买入轮。

    渠道标签跨位面携带(P1 段买入的 m2/hold 件会随出口板/备战席进
    P2,身份不因位面切换失效);``buy_round`` 只记 P2 段(P1/P2 轮号
    段内重计,跨面轮序不可辨,fresh 窗口只在 P2 段内计算)。按名多集
    记账近似(卖出按名销账,不辨同名多笔归属)。
    """
    held_tags: dict[str, set[str]] = {}
    buy_round: dict[str, int] = {}
    rn = int(row.get('round_num') or 0)
    for r0 in rows:
        if int(r0.get('round_num') or 0) > rn \
                and (r0.get('plane') or 0) >= 2:
            continue
        plane0 = int(r0.get('plane') or 0)
        for a in (r0.get('actions') or []):
            t = a.get('__type__')
            if t == 'BuyCard':
                n = (a.get('card') or {}).get('name') or ''
                rsn = a.get('reason') or ''
                if not n:
                    continue
                if rsn in _OBLIGATION_FAMILY:
                    held_tags.setdefault(n, set()).add('obligation')
                elif rsn in _HOLD_ARMS:
                    held_tags.setdefault(n, set()).add('hold')
                if (rsn in _OBLIGATION_FAMILY or rsn in _HOLD_ARMS) \
                        and plane0 >= 2:
                    buy_round[n] = int(r0.get('round_num') or 0)
            elif t in ('SellBench', 'SellDeployed'):
                n = a.get('name') or a.get('expect') or ''
                held_tags.pop(n, None)
                buy_round.pop(n, None)
    return held_tags, buy_round


def check_t190_c1_bench_clog_attribution(
        full_ledgers: list[list[dict]]) -> dict:
    """C-A1 腾席链失效形态枚举 + 死库存卡容分类账(批级;设计 v2 §3.2-2)。

    分母 = P2 行内 core 拒因事件(波级 ``sim.shop_waves[].rejects`` 且
    名 ∈ comp.core_chars;波级 = 完整分母,帧级 ``shop_rejects`` 只记
    末波,另披露供与设计基线 124 帧级口径对读)。对含 bench 满拒因的
    行做腾席失效形态归因:

    - ``no_fuel_honest``:占席全部落保护类(零 sellable_fuel)= 诚实
      停摆形态——复测批预数据(no_fuel 963 占出口事件 87.9%,``core_
      ruling_seat_buckets`` 披露)预期主形态;
    - ``chain_act``:有 sellable_fuel 且本轮出口键零 no_fuel 申报
      (腾席支已行权/席空直买)= 链正常;
    - ``honest_stall_dispute``:有 sellable_fuel 且本轮出口键含
      ``*_no_fuel`` 申报 = **申报-数据矛盾候选**(生产称无合法 victim
      而账本存在候选形态占席)——红语义 = 须逐帧判读的发现,非对生
      产行为的定谳(近似豁免面 = T3 垫保活跃名/锁定采购集账本不可见,
      见模块头);violations = 存在该候选的局数。

    非 bench 满拒因(owned/missing_unaffordable/stockpile_*/merge_*)
    原因值直接入桶;``missing_no_path`` 单列(生产语义 = 金席俱足未发
    射异常态,拒因串自申报「判读线索非审计账」,故只披露不判红)。

    验收锚(设计 §六批 C)= **零未归因**:每事件恰落一桶,
    ``unattributed`` 由 else 桶构造恒 0,``attributed_events`` ≡
    ``total_events`` 即覆盖证明。占席主标签分布 = 死库存卡容分类账
    (bench 满归因行的逐桶席位计数;``transition_pack`` 桶 = 设计
    §七-4「④放行集锁线态长期占容」预期主发现面)。
    """
    pack_names = _transition_pack_names()
    total_events = 0
    reason_hist: Counter = Counter()
    frame_level_reason: Counter = Counter()
    benchfull_rows = 0
    shape_rows: Counter = Counter()
    occupancy: Counter = Counter()
    dispute_games: list[int] = []
    pack_occupancy_frames = 0
    no_path_rows = 0
    for gi, rows in enumerate(full_ledgers):
        game_dispute = False
        for row in rows:
            if (row.get('plane') or 0) < 2:
                continue
            comp = get_comp(row.get('target_comp') or '')
            cores = set(comp.core_chars) if comp else set()
            if not cores:
                continue
            roster = frozenset(set(comp.core_chars)
                               | set(comp.shared_chars or ()))
            waves = (row.get('sim') or {}).get('shop_waves') or []
            wave_events = [(n, str(rsn)) for w in waves
                           for n, rsn in (w.get('rejects') or {}).items()
                           if n in cores]
            for n, rsn in (row.get('shop_rejects') or {}).items():
                if n in cores:
                    frame_level_reason[rsn] += 1
            if not wave_events:
                continue
            total_events += len(wave_events)
            for _n, rsn in wave_events:
                reason_hist[rsn] += 1
                if rsn == 'missing_no_path':
                    no_path_rows += 1
            if not any('bench_full' in rsn for _n, rsn in wave_events):
                continue
            benchfull_rows += 1
            rn = int(row.get('round_num') or 0)
            occ = _c1_classify_bench(row.get('state') or {}, roster,
                                     pack_names,
                                     *_c1_held_tags(rows, row), rn)
            for k, v in occ.items():
                occupancy[k] += v
            if occ.get('transition_pack'):
                pack_occupancy_frames += 1
            ct = (row.get('obs') or {}).get('cw4_counters') or {}
            no_fuel_claimed = sum(
                int(ct.get(k, 0) or 0) for k in
                ('core_unlocked_no_fuel', 'core_locked_no_fuel',
                 'transition_no_fuel'))
            if occ.get('sellable_fuel'):
                if no_fuel_claimed > 0:
                    shape_rows['honest_stall_dispute'] += 1
                    game_dispute = True
                else:
                    shape_rows['chain_act'] += 1
            else:
                shape_rows['no_fuel_honest'] += 1
        if game_dispute:
            dispute_games.append(gi)
    return {
        'violations': len(dispute_games),
        'games': dispute_games[:5],
        'total_events': total_events,
        'attributed_events': total_events,
        'unattributed': 0,
        'benchfull_rows': benchfull_rows,
        'shape_rows': dict(shape_rows),
        'occupancy_buckets': dict(occupancy),
        'transition_pack_occupancy_frames': pack_occupancy_frames,
        'reason_hist_wave': dict(reason_hist.most_common()),
        'reason_hist_frame': dict(frame_level_reason.most_common()),
        'missing_no_path_events': no_path_rows,
        'dispute_note': _DISPUTE_NOTE,
    }


# ====================================================================
# --- C-A2 新购件覆盖复查(新购档关键件 → swap 计划候选) ---------------
# ====================================================================

def _c2_plan_point(rows: list[dict], i: int) -> tuple[dict | None, str, str]:
    """计划点定位:同行 m1p 优先(引擎 ``_m1p_plan_and_record`` 吃买后
    黑板 = 买入同轮部署计划),同行缺退下一有 m1p 行;(None, '', skip)
    = 无载体(局终/发射短路帧无 M1″ 决策帧——后者 R3-a 起由独立行内键
    ``m1p_obs_skipped`` 显影,ADR-0647)。第三返回值 = 扫描路径上命中的
    盲窗显影键('launch_short_circuit' = 发射帧短路无帧;'' = 无显影键,
    旧档案/局终),供桶内分键判读,不影响定位语义。"""
    skip = str(rows[i].get('m1p_obs_skipped') or '')
    if isinstance(rows[i].get('m1p'), dict):
        return rows[i], 'same_row', ''
    for r2 in rows[i + 1:]:
        if isinstance(r2.get('m1p'), dict):
            return r2, 'next_row', ''
        if not skip:
            skip = str(r2.get('m1p_obs_skipped') or '')
    return None, '', skip


def check_t190_c2_new_buy_swap_coverage(
        full_ledgers: list[list[dict]]) -> dict:
    """C-A2 新购件覆盖复查(批级收纳)。

    病灶 = 「部署计划未纳入本轮新购件」(复盘 195720 C)。断言:
    每笔新购档关键件(义务买入臂 m2_line_member/m2_locked_member;
    C1/④ 为囤入通道不上板,不入分母)从买入行到**计划点**应被 swap
    计划覆盖。覆盖形态闭集:deployed(已上板)/ left_bench(已离席:
    卖/合成)/ recorded(计划逐件拒因显影,``m1p.reasons``)/ abstain
    (计划整帧弃权)。缺口(face = 计划记录对关键件零处置)按计划
    活性细分:

    - ``gap_plan_active``:计划非空(有 victim 被卖/有件上板)而本件
      零记录 = 强信号(他件被处置、本件不可见——病灶候选);
    - ``gap_plan_idle``:计划空(板满无合格 victim)——本件等待属
      形态内,弱信号;
    - ``gap_board_open``:板未满——本件应走常规部署而非 swap 计划,
      滞席属部署欠载面(既有 ``deploy_lag_units`` 遥测辖),弱信号;
    - ``no_plan_carrier``:无计划载体(申报桶非缺口);R3-a 起桶内
      分键 ``no_plan_carrier_launch_short_circuit`` = 行内盲窗显影键
      ``m1p_obs_skipped`` 在场(发射帧短路无帧,ADR-0647),成因可辨
      非混桶。

    ``m1p.reasons`` 粒度申报:计划只对「被拒 victim」与「卖后留置 bench」
    两类记逐件拒因,胜出 victim 截断后的未处置 bench 件无记录——
    ``gap_plan_active`` 是该粒度下的可见性缺口候选,修复面按「计划
    记录扩面 or 逐帧重放」路由,本检查只显影不预判修法(设计:批 C
    只审计)。

    验收锚 = 结论可裁:``gaps_plan_active == 0`` → 裁
    done(覆盖闭环);>0 → ``gap_samples`` 进修复面。violations =
    有强信号缺口的局数(弱信号只披露)。
    """
    shape: Counter = Counter()
    gap_games: list[int] = []
    gap_samples: list[dict] = []
    buys_tracked = 0
    for gi, rows in enumerate(full_ledgers):
        game_gap = False
        for i, row in enumerate(rows):
            if (row.get('plane') or 0) < 2:
                continue
            for a in (row.get('actions') or []):
                if a.get('__type__') != 'BuyCard' \
                        or (a.get('reason') or '') not in _OBLIGATION_ARMS:
                    continue
                name = (a.get('card') or {}).get('name') or ''
                if not name:
                    continue
                buys_tracked += 1
                pt, tag, _skip = _c2_plan_point(rows, i)
                if pt is None:
                    # R3-a(ADR-0647)桶内分键:盲窗显影键在场 =
                    # 无载体成因 = 发射帧短路(申报桶非缺口语义不变);
                    # 旧档案无键仍归 no_plan_carrier,判读零漂移。
                    shape['no_plan_carrier_launch_short_circuit'
                          if _skip == 'launch_short_circuit'
                          else 'no_plan_carrier'] += 1
                    continue
                m1p = pt.get('m1p') or {}
                st = pt.get('state') or {}
                dep = _deployed_names(st)
                bench = _bench_names(st)
                reasons = m1p.get('reasons') or {}
                if name in dep:
                    shape[f'deployed@{tag}'] += 1
                elif name not in bench:
                    shape[f'left_bench@{tag}'] += 1
                elif name in reasons:
                    shape[f'recorded@{tag}'] += 1
                elif m1p.get('abstain'):
                    shape[f'abstain@{tag}'] += 1
                else:
                    cap = int(st.get('cap') or 0)
                    dep_n = len([d for d in dep if d])
                    if cap > 0 and dep_n < cap:
                        shape[f'gap_board_open@{tag}'] += 1
                    elif m1p.get('nonempty'):
                        shape[f'gap_plan_active@{tag}'] += 1
                        game_gap = True
                        if len(gap_samples) < 20:
                            gap_samples.append({
                                'game': gi, 'plane': row.get('plane'),
                                'round_num': row.get('round_num'),
                                'name': name, 'point': tag})
                    else:
                        shape[f'gap_plan_idle@{tag}'] += 1
        if game_gap:
            gap_games.append(gi)
    active_gaps = sum(v for k, v in shape.items()
                      if k.startswith('gap_plan_active'))
    return {
        'violations': len(gap_games),
        'games': gap_games[:5],
        'buys_tracked': buys_tracked,
        'shapes': dict(shape),
        'gaps_plan_active': active_gaps,
        'gap_samples': gap_samples,
        'verdict': ('coverage_closed:可裁 done' if active_gaps == 0
                    else 'repair_face:强信号缺口在案,进修复面'),
        'note': _DISPUTE_NOTE,
    }


# ====================================================================
# --- C-A3 豁免集开火性 ----------------------------------------------
# ====================================================================

def check_t190_c3_exemption_fire(full_ledgers: list[list[dict]]) -> dict:
    """C-A3 豁免集开火性(批级;设计 v2 §六批 C-A3 + 修订 10)。

    收窄只停 S_spec 两臂(dominance/hub),豁免集 = 买因闭集减 S_spec
    (修订 6 符号单一源)必须在 D 轮(收窄开火轮)照常开火——收窄若
    越界压豁免臂(过度收窄形态),D 轮豁免买入塌零,本检查显影。

    判据(轮级;账本最细粒度 = 轮行,帧级收窄与同轮他帧发射并存属
    合法,不作红——批 B 复测批「停发轮零发射 164/164」是经验事实非
    结构不变量):

    - **红 ①域泄漏**:``press_narrowed_transition_domain`` 开火落 P1
      (声明域 = P2 锁线转型帧);
    - **红 ②哨兵触发**:``..._hub`` 键 >0(hub 辖 unlocked 与 locked
      D 域结构性不相交,批 B 申报恒 0;>0 = P86 辖域变更哨兵命中,
      判读禁并桶进 dominance 位键);
    - **空面申报**:D 轮存在而全批 D 轮豁免臂买入 = 0 →
      ``exemption_zero_fire_in_d_rounds = True`` 申报(非零开火或空面
      申报二选一为验收锚;真零面 = 解封收益未兑现,候判读)。

    ``..._prep_seen`` 键照批 B 语义披露(对称观测,预期恒 0)。
    """
    d_rounds = 0
    dom_fires = 0
    hub_fires = 0
    prep_seen = 0
    leak_planes: Counter = Counter()
    exempt_in_d: Counter = Counter()
    sspec_in_d: Counter = Counter()
    for rows in full_ledgers:
        for row in rows:
            ct = (row.get('obs') or {}).get('cw4_counters') or {}
            dom = int(ct.get(NARROW_KEYS[0], 0) or 0)
            hub_fires += int(ct.get(NARROW_KEYS[1], 0) or 0)
            prep_seen += int(ct.get(NARROW_KEYS[2], 0) or 0)
            if not dom:
                continue
            dom_fires += dom
            d_rounds += 1
            plane = int(row.get('plane') or 0)
            leak_planes[plane] += dom
            for a in (row.get('actions') or []):
                if a.get('__type__') != 'BuyCard':
                    continue
                rsn = a.get('reason') or ''
                if rsn in S_SPEC_ARMS:
                    sspec_in_d[rsn] += 1
                elif rsn in LAUNCH_CAUSE_BY_ARM:
                    exempt_in_d[rsn] += 1
    zero_fire = bool(d_rounds) and not sum(exempt_in_d.values())
    red_planes = sorted(p for p in leak_planes if p != 2)
    return {
        'violations': (1 if red_planes or hub_fires else 0),
        'domain_leak_planes': red_planes,
        'hub_sentinel_fires': hub_fires,
        'd_rounds': d_rounds,
        'dominance_narrow_fires': dom_fires,
        'fire_plane_hist': dict(leak_planes),
        'exempt_buys_in_d_rounds': dict(exempt_in_d.most_common()),
        'exempt_buys_in_d_total': sum(exempt_in_d.values()),
        'sspec_buys_in_d_rounds': dict(sspec_in_d),
        'prep_seen_fires': prep_seen,
        'exemption_zero_fire_in_d_rounds': zero_fire,
        'note': ('hub 空开火面 = 结构事实非辖域错(设计修订 10),'
                 '禁并桶进 dominance 位键;轮级粒度申报同 C-A4'),
    }


# ====================================================================
# --- C-A4 转化漏斗遥测检查器(闭集全键对账 × fate × 收窄分键) --------
# ====================================================================

#: fate 终态闭集(C-A4 配平对账;每笔买入恰认一终态)。
#: ``sold`` 桶含无名卖出与合成消耗(账本不可辨,按名多集收缩认账)。
_FATE_TERMINALS = ('reached_board', 'sold', 'stuck_end')


def check_t190_c4_funnel_reconcile(
        full_ledgers: list[list[dict]]) -> dict:
    """C-A4 转化漏斗遥测检查器(批级;设计 v2 §六批 C-A4 + 修订 6)。

    三重对账:

    1. **闭集全键对账**:全批(全位面)每笔 ``BuyCard.reason`` 必须 ∈
       ``LAUNCH_CAUSE_BY_ARM``(修订 6 符号单一源,现值 15 键;闭集外
       键 = 幽灵臂,红——批 B 闭集锁同判据的数据面镜像);漏斗表 =
       闭集**全键**逐键计数(零计键也列,与 decisions 账本逐位对读;
       m2_locked_member 与 ④ transition_component_buy 键因此显式在表)。
    2. **fate 键配平**:逐笔买入按名多集台账(FIFO 归属,模块头近似
       声明)追踪三终态——reached_board(deployed 计数上升)/ sold
       (卖出动作或台账收缩:无名卖出与合成消耗并入)/ stuck_end
       (局终台账残账 = 滞留备战席主病灶面);``fate_accounted ==
       buys_total`` 为逐位配平锚,缺账 = 红。
    3. **收窄分键对账**:dominance 位分键计数与 S_spec 臂在 D 轮的
       买入计数单列披露(轮级粒度,观测非红——C-A3 同款粒度申报)。

    判读边界:sim 未建模装备效果/星级战斗维,fate 分桶只述去向不述
    收益;与设计基线(滞留 86-87%)对读按批声明口径。
    """
    buys_by_arm: Counter = Counter()
    fate_by_arm: dict[str, Counter] = {}
    unknown_keys: Counter = Counter()
    dom_fires = 0
    sspec_in_d = 0
    for rows in full_ledgers:
        pending: dict[str, list[str]] = {}
        last_dep: dict[str, int] = {}
        for row in rows:
            plane = int(row.get('plane') or 0)
            for a in (row.get('actions') or []):
                t = a.get('__type__')
                if t == 'BuyCard':
                    rsn = a.get('reason') or ''
                    n = (a.get('card') or {}).get('name') or ''
                    buys_by_arm[rsn] += 1
                    if rsn not in LAUNCH_CAUSE_BY_ARM:
                        unknown_keys[rsn] += 1
                    if n:
                        pending.setdefault(n, []).append(rsn)
                elif t in ('SellBench', 'SellDeployed'):
                    n = a.get('name') or a.get('expect') or ''
                    lst = pending.get(n) or []
                    if lst:
                        arm = lst.pop(0)
                        fate_by_arm.setdefault(arm, Counter())['sold'] += 1
            st = row.get('state') or {}
            dep = _deployed_names(st)
            bench = _bench_names(st)
            dep_now = Counter(dep)
            for n, c in dep_now.items():
                if not n:
                    continue
                lst = pending.get(n) or []
                prev = int(last_dep.get(n, 0) or 0)
                for _ in range(max(0, c - prev)):
                    if lst:
                        arm = lst.pop(0)
                        fate_by_arm.setdefault(arm, Counter())[
                            'reached_board'] += 1
            # 台账收缩对账:在册副本(板+bench)少于台账 = 无名消耗
            #(卖出行无名/合成消耗,账本不可辨)→ 最老副本认 sold。
            copies_now = dep_now + Counter(bench)
            for n, lst in pending.items():
                while len(lst) > int(copies_now.get(n, 0) or 0):
                    arm = lst.pop(0)
                    fate_by_arm.setdefault(arm, Counter())['sold'] += 1
            last_dep = dict(dep_now)
            ct = (row.get('obs') or {}).get('cw4_counters') or {}
            dom = int(ct.get(NARROW_KEYS[0], 0) or 0)
            if dom and plane >= 2:
                dom_fires += dom
                for a in (row.get('actions') or []):
                    if a.get('__type__') == 'BuyCard' \
                            and (a.get('reason') or '') in S_SPEC_ARMS:
                        sspec_in_d += 1
        # 局终残账:台账仍挂 = 滞留(stuck_end;含 P1 段件,终态按局)。
        for lst in pending.values():
            for arm in lst:
                fate_by_arm.setdefault(arm, Counter())['stuck_end'] += 1
    funnel = {k: {'buys': int(buys_by_arm.get(k, 0)),
                  'fates': dict(fate_by_arm.get(k, {}))}
              for k in sorted(LAUNCH_CAUSE_BY_ARM)}
    buys_total = sum(buys_by_arm.values())
    fate_total = sum(sum(c.values()) for c in fate_by_arm.values())
    return {
        'violations': (1 if unknown_keys or buys_total != fate_total
                       else 0),
        'closed_set_unknown_keys': dict(unknown_keys),
        'buys_total': buys_total,
        'fate_accounted': fate_total,
        'fate_bitwise_match': buys_total == fate_total,
        'funnel_by_arm': funnel,
        'narrow_dom_fires_p2': dom_fires,
        'sspec_buys_in_d_rounds_p2': sspec_in_d,
        'fate_terminals': list(_FATE_TERMINALS),
        'note': ('fate 归属 = 按名多集 FIFO 近似(同名跨臂副本不可辨;'
                 'sold 桶含无名卖出与合成消耗);逐位配平锚辖总量,'
                 '分桶判读按批声明口径'),
    }
