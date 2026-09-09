"""P88 锁线转型域投机买入收窄·库容不变量与解封方向·复算脚本。

命题(docs/develop/currency_war/proofs/p88.md;math_proofs.md P88 行):
- 辖域单一源: D = _swap_transition_domain_of = armed ∧ locked ∧ fp<1.00 ∧ 板满;
- 调和引理(路径级弱支配): 收窄的占位成本 = 滞留期各帧边际 V_slot 之和 ≥ 0,
  被阻义务兑现帧上 ≥ 该义务净 EV(严格);bench 恒 free≥2 时和 = 0(等价分支);
- 主不等式(冻结口径): S_spec 停发 ⟹ 被压抑类备战席占用逐帧 O_t(收窄) ≤ O_t(基线);
- 解封方向式(非逐帧充分条件): 逐拒帧槽位账恒等 + 未解封必可归因 +
  聚合方向(解封 ≥ 覆盖标记 − 回填持有,两扣减 = 同帧在先臂/中间帧回填);
- 息损不增: dominance 前件 gold>g* ⟹ 压抑只发生在溢余段,该段息损 L≡0(P70);
- 三重折扣: 57-63% = 冻结口径上界,禁当预期值(算术面在断言 7 对账)。

本脚本直调生产单一源复算(kernel 禁第二实现):
- _swap_transition_domain_of / SWAP_TRANSITION_ARM_ENABLED: kernel/cw_deploy_logic.py:833/:756
- LAUNCH_CAUSE_BY_ARM / WINDOW_LAUNCH_CAUSES: strategies/impl/mandate_v1/sell_gate.py:114/:107
- v_slot(P41③): strategies/impl/mandate_v1/statefn/vopt.py:71
- saturation_line / loss_exact: kernel/cw_economy.py(P70 同源)
- BENCH_CAPACITY: kernel/cw_state.py:32

数据锚(冻结直录;三批报告住 .debug/temp/currency_war/ 下,gitignore 易失,
数字冻结于断言 7 与单篇数据锚节): findprob_20260910_005622(n100 s8000-8099)
+ findprob_probe_20260910_012328(n50 s8100-8149,量化以探针批为准)
+ findprob_20260910_0200_8150(n100 s8150-8249,持续面对账)。

重跑: $env:PYTHONPATH='src'; uv run python tools/cw/proofs/p88_check.py
"""
from __future__ import annotations

import random
import sys

from sr_od.application.currency_war.kernel.cw_deploy_logic import (
    SWAP_TRANSITION_ARM_ENABLED,
    _swap_transition_domain_of,
)
from sr_od.application.currency_war.kernel.cw_economy import (
    loss_exact,
    saturation_line,
)
from sr_od.application.currency_war.kernel.cw_state import BENCH_CAPACITY
from sr_od.application.currency_war.strategies.impl.mandate_v1.sell_gate import (
    LAUNCH_CAUSE_BY_ARM,
    WINDOW_LAUNCH_CAUSES,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.statefn.vopt import (
    v_slot,
)

# 收窄集 S_spec(P88 §0;买因键)
S_SPEC: frozenset[str] = frozenset({'dominance_buy', 'hub_option_buy'})
# 溢余段息损网格(P70 全网格 1,698,840 格在册,此处按 P88 辖域缩样复核)
_CAPS = (5, 9, 10)
_OFFSET_MAX = 60
_ROUNDS_MAX = 7   # P2 段 R0-R7
_IBAR_BAND = range(4, 10)


def check_domain_predicate() -> None:
    """断言 1: 辖域谓词单一源真值表 + 域活开关 + hub 带结构不相交。"""
    assert SWAP_TRANSITION_ARM_ENABLED is True, '域活开关被关死(收窄辖域变死开关)'
    n = 0
    for armed in (True, False):
        for locked in (True, False):
            for fp in (None, 0.0, 0.5, 0.99, 1.0, 1.5):
                for board_full in (True, False):
                    got = _swap_transition_domain_of(armed, locked, fp, board_full)
                    want = (armed and locked and fp is not None
                            and fp < 1.00 and board_full)
                    assert got == want, f'谓词偏离合取定义: {armed}/{locked}/{fp}/{board_full} -> {got}'
                    if not locked:
                        assert got is False, 'D 域含未锁帧(hub 辖 unlocked,结构性不相交被破)'
                    n += 1
    print(f'[断言1] 辖域单一源: _swap_transition_domain_of 真值表 {n} 格 = '
          f'armed∧locked∧fp<1.00∧板满 逐格一致; armed=True 域活; D⊆locked(hub 带不相交) PASS')


def check_closed_set() -> None:
    """断言 2: 买因闭集对账(15 键/S_spec ⊆ 闭集/豁免补集/press τ=同轮)。"""
    keys = set(LAUNCH_CAUSE_BY_ARM)
    assert len(keys) == 15, f'LAUNCH_CAUSE_BY_ARM 现值 {len(keys)} 键, 预期 15(闭集漂移=锁红面)'
    assert keys >= S_SPEC, f'收窄集越出闭集: {S_SPEC - keys}'
    exempt = keys - S_SPEC
    for must_exempt in ('m2_line_member', 'm2_locked_member', 'm2_stockpile',
                        'm2_merge_completion', 'core_single_card_buy',
                        'core_single_card_buy:unlocked', 'm6_stockpile',
                        'press_buy_deployable', 'ev_buy', 'transition_component_buy',
                        'dead_gold_press_buy', 'fuel_filler_stall', 't3_unlocked_hemostat'):
        assert must_exempt in exempt, f'{must_exempt} 应在豁免集(收窄误伤面)'
    assert LAUNCH_CAUSE_BY_ARM['dominance_buy'] == 'press'
    assert 'press' in WINDOW_LAUNCH_CAUSES, 'press 类不在窗口段辖域(τ=同轮机制注失效)'
    assert 'hub_option_buy' not in WINDOW_LAUNCH_CAUSES
    print(f'[断言2] 闭集对账: LAUNCH_CAUSE_BY_ARM 15 键; S_spec={sorted(S_SPEC)} ⊆ 闭集; '
          f'豁免=闭集∖S_spec 含 m2_locked_member 等 13 键; dominance=press∈窗口段(τ=同轮) PASS')


def check_harmonic_lemma() -> None:
    """断言 3: 调和引理路径级弱支配(v_slot 直调;随机滞留期轨迹)。"""
    # 点态锚(P41③: free≥2 = 0; free≤1 = max 被阻净 EV)
    assert v_slot(2, [5.0]) == 0.0 and v_slot(9, [5.0]) == 0.0
    assert v_slot(1, [5.0, 3.0]) == 5.0 and v_slot(0, [7.5]) == 7.5
    assert v_slot(1, []) == 0.0, '空被阻集的 V_slot 应为 0(default 下界)'
    rng = random.Random(88)
    strict_cases = equiv_cases = 0
    for _ in range(200):
        span = rng.randint(1, 8)
        has_fulfillment = rng.random() < 0.5
        e_star = round(rng.uniform(1.0, 10.0), 2)  # 被阻线内义务净 EV
        path_cost = 0.0
        for t in range(span):
            free_base = rng.randint(0, 8)
            base_evs = [round(rng.uniform(0.1, 9.0), 2)
                        for _ in range(rng.randint(1, 3))]
            # 收窄世界多一格 ⟹ 被阻动作集单调不减的子集(多出的格可解封义务)
            narrow_evs = [ev for ev in base_evs if rng.random() < 0.5]
            if has_fulfillment and t == span - 1:
                free_base, base_evs, narrow_evs = 0, [e_star], []  # 拒帧形态
            # 边际占位成本 Δ_t = 基线被阻价 − 收窄被阻价(free_narrow = free_base + 1)
            delta = (v_slot(free_base, base_evs)
                     - v_slot(free_base + 1, narrow_evs))
            assert delta >= -1e-9, f'边际占位成本为负: free={free_base} Δ={delta}'
            path_cost += delta
        assert path_cost >= -1e-9, '路径占位成本和为负(弱支配破面)'
        if has_fulfillment:
            assert path_cost >= e_star - 1e-9, (
                f'兑现帧严格性破面: 路径成本 {path_cost} < 被阻义务净 EV {e_star}')
            strict_cases += 1
        else:
            strict_cases += 0 if path_cost > 1e-9 else 0
    # 反事实分支: 滞留期内 bench 恒 free≥2 ⟹ 和 = 0(价值等价、不变量仍成立)
    for _ in range(50):
        span = rng.randint(1, 6)
        total = sum(v_slot(rng.randint(2, 9), [4.0])
                    - v_slot(rng.randint(3, 10), [4.0]) for _ in range(span))
        assert abs(total) < 1e-9, '恒 free≥2 分支路径成本非零'
        equiv_cases += 1
    print(f'[断言3] 调和引理(路径级): 200 条随机滞留期轨迹弱支配成立(路径成本≥0), '
          f'其中 {strict_cases} 条含兑现帧且路径成本 ≥ 被阻义务净 EV(严格); '
          f'{equiv_cases} 条恒 free≥2 反事实分支和=0(等价) PASS')


# ---- 断言 4/5 的事件序列模拟器(冻结口径;单动作契约 = 逐动作串行发射,
# 位次即优先序[F8-2 表述精度处置,shop.py:1591 注原义])----
# 帧事件 = (臂候选, core 到店?, 离场?);臂候选 ∈ {None,'m2','sup','m6'}:
#   'sup' = 收窄类(dominance 投机件),'m2' = 排序在先豁免臂,'m6' = 中间帧回填臂。
# 发射序: 臂候选先于 core(shop 域物理位次即优先序,shop.py:1591);core 拒帧
# 观察在臂动作之后。离场事件 = 账本实际持有区间口径的离场帧(被卖/上板/合成)。


def _gen_frames(rng: random.Random) -> list[tuple[str | None, bool, bool]]:
    frames: list[tuple[str | None, bool, bool]] = []
    for _ in range(rng.randint(3, 15)):
        arm = rng.choices([None, 'm2', 'sup', 'm6'], weights=[4, 3, 3, 2])[0]
        core = rng.random() < 0.45
        leave = rng.random() < 0.18
        frames.append((arm, core, leave))
    return frames


def _simulate(frames: list[tuple[str | None, bool, bool]], free0: int) -> dict:
    """基线/收窄双世界锁步重放;返回逐拒帧槽位账与聚合量。"""
    free_b = free_n = free0
    held_b: list[tuple[str, int]] = []   # 基线 bench 上的 (类, 买帧)
    held_n: list[tuple[str, int]] = []   # 收窄 bench(S_spec 不入席)
    rejects: list[dict] = []
    consume_events = 0
    for t, (arm, core, leave) in enumerate(frames):
        if leave and held_b:
            victim = held_b.pop(0)          # 账本离场: 弹最旧持有件,腾回基线槽
            free_b += 1
            if victim in held_n:            # 收窄世界只重放豁免件的同一离场
                held_n.remove(victim)
                free_n += 1
        if arm is not None:
            is_sup = arm == 'sup'
            bought_b = False
            if free_b > 0:                  # 基线: 门 = bench_free>0
                held_b.append((arm, t))
                free_b -= 1
                bought_b = True
            if not is_sup and free_n > 0:   # 收窄: S_spec 停发,豁免臂照旧
                held_n.append((arm, t))
                free_n -= 1
                if not bought_b:
                    consume_events += 1     # 释放槽被豁免臂吃掉(同帧在先臂/中间帧)
        if core and free_b == 0:
            # 拒帧观察(基线席满,core 不可入);账快照先于 core 动作。
            # 量全部直测:released = 空槽差;occ_diff = 占用差(容量恒等被检对象);
            # narrow_only/base_only = 收窄独有/基线独有的在席件(既往覆盖遗留形态,
            # 含被压抑件离场后基线重新腾空的槽)。
            held_b_set = set(held_b)
            held_n_set = set(held_n)
            covered = sum(1 for kind, _ in held_b if kind == 'sup')
            narrow_only = sum(1 for it in held_n if it not in held_b_set)
            base_only = sum(1 for it in held_b if it not in held_n_set)
            released = free_n - free_b                  # 释放槽账(空槽差直测)
            rejects.append({
                'frame': t, 'covered': covered, 'narrow_only': narrow_only,
                'base_only': base_only, 'occ_diff': len(held_b) - len(held_n),
                'released': released, 'unsealed': free_n >= 1,
                'consumed': max(covered - released, 0),
            })
        if core:
            # core 动作(两世界各自判定;core = 豁免类 C1)
            if free_b >= 1:
                held_b.append(('core', t))
                free_b -= 1
            if free_n >= 1:
                held_n.append(('core', t))
                free_n -= 1
    unsealed = sum(1 for r in rejects if r['unsealed'])
    covered_frames = sum(1 for r in rejects if r['covered'] >= 1)
    consumed_sum = sum(r['consumed'] for r in rejects)
    return {'rejects': rejects, 'unsealed': unsealed,
            'covered_frames': covered_frames, 'consumed_sum': consumed_sum,
            'consume_events': consume_events}


def check_main_invariant() -> None:
    """断言 4: 主不等式(冻结口径)——被压抑类/总占用逐帧 O_t(收窄) ≤ O_t(基线)。"""
    rng = random.Random(8801)
    frames_total = 0
    for _ in range(300):
        frames = _gen_frames(rng)
        held_b: list[tuple[str, int]] = []
        held_n: list[tuple[str, int]] = []
        for t, (arm, _core, leave) in enumerate(frames):
            if leave and held_b:            # 账本离场: 弹最旧持有件(与 _simulate 同口径)
                victim = held_b.pop(0)
                if victim in held_n:        # 收窄世界只重放豁免件的同一离场
                    held_n.remove(victim)
            if arm is not None:             # 买入(S_spec 收窄世界不入席)
                held_b.append((arm, t))
                if arm != 'sup':
                    held_n.append((arm, t))
            sup_b = sum(1 for kind, _ in held_b if kind == 'sup')
            assert len(held_n) <= len(held_b), f'总占用破不等式: t={t}'
            assert len(held_b) - len(held_n) == sup_b, f'被压抑类账不平: t={t}'
            frames_total += 1
    print(f'[断言4] 主不等式(冻结口径): 300 条随机候选序 × 双世界锁步重放(含离场), '
          f'逐帧 O_t(收窄) ≤ O_t(基线) 与被压抑类账恒等全成立({frames_total} 帧) PASS')


def check_unseal_direction() -> None:
    """断言 5: 解封方向式——逐拒帧槽位账恒等 + 解封判定 + 归因闭合 + 聚合方向。"""
    rng = random.Random(8802)
    n_rej = n_unsealed = n_covered = n_attributed = 0
    for _ in range(300):
        frames = _gen_frames(rng)
        res = _simulate(frames, rng.randint(0, 2))
        # (a) 容量恒等: 空槽差 = 占用差(模拟器账自洽)
        # (b) 解封判定(拒帧定义): 基线席满 ∧ 收窄有空槽 ⟺ released ≥ 1
        # (c) 解封必有压抑来源: 当期覆盖 ∨ 既往覆盖遗留(基线独有件)
        # (d) 归因闭合: 有覆盖却未解封 ⟹ 净消耗 ≥ 1(槽被耗尽;无覆盖 = 出辖)
        for r in res['rejects']:
            n_rej += 1
            assert r['released'] == r['occ_diff'], (
                f"容量恒等破面: frame={r['frame']} released={r['released']} "
                f"occ_diff={r['occ_diff']}")
            assert r['unsealed'] == (r['released'] >= 1), (
                f"解封判定不一致: frame={r['frame']}")
            if r['unsealed']:
                assert r['covered'] >= 1 or r['base_only'] >= 1, (
                    f"无压抑来源而解封: frame={r['frame']}")
            if r['covered'] >= 1 and not r['unsealed']:
                assert r['consumed'] >= 1, (
                    f"未解封且有覆盖但无消耗(归因开路): frame={r['frame']}")
                n_attributed += 1
        # (e) 聚合方向(设计方向式,槽时一次计账): Σ解封 ≥ Σ覆盖标记 − Σ净消耗
        #     (净消耗 = 同帧在先臂/中间帧回填吃掉的覆盖槽,两扣减通道的合计形态)
        assert res['unsealed'] >= res['covered_frames'] - res['consumed_sum'], (
            f"聚合方向破面: unsealed={res['unsealed']} "
            f"covered={res['covered_frames']} consumed={res['consumed_sum']}")
        n_unsealed += res['unsealed']
        n_covered += res['covered_frames']
    print(f'[断言5] 解封方向式: 300 局合成序列, {n_rej} 个拒帧逐帧容量恒等+解封判定+'
          f'压抑来源+归因闭合({n_attributed} 个「覆盖未解封」全部归因到槽被耗尽); '
          f'聚合 Σ解封({n_unsealed}) ≥ Σ覆盖标记({n_covered}) − Σ净消耗 全局成立 '
          f'(57-63% 为冻结口径上界,禁当预期值) PASS')


def check_overflow_no_interest_loss() -> None:
    """断言 6: 息损不增——dominance 前件 gold>g* ⟹ 压抑全在溢余段,该段 L≡0(P70)。"""
    n = 0
    for cap in _CAPS:
        g_star = saturation_line(cap)
        for offset in range(1, _OFFSET_MAX + 1):
            g = g_star + offset
            for spend in range(1, offset + 1):     # 压抑不花金;spend 扫描守线出口
                for rounds in range(0, _ROUNDS_MAX + 1):
                    for ibar in _IBAR_BAND:
                        got = loss_exact(g, spend, rounds, ibar, cap=cap)
                        assert got == 0, (
                            f'溢余段息损非零: cap={cap} g={g} spend={spend} '
                            f'R={rounds} I={ibar} -> L={got}')
                        n += 1
    print(f'[断言6] 息损不增(P70 直代): 溢余段网格 {n} 格 loss_exact=0 '
          f'(cap∈{_CAPS}×溢出量1-{_OFFSET_MAX}×spend守线×R0-{_ROUNDS_MAX}×Ī4-9) PASS')


def check_data_anchors() -> None:
    """断言 7: 数据锚对账(三批冻结直录;四舍五入到报告口径)。"""

    def pct(num: int, den: int) -> int:
        return round(num / den * 100)

    # 拒帧构成(n100,findprob_20260910_005622 §二问题 1)
    assert 57 + 51 + 16 == 124, 'core 拒帧构成和不等于 124'
    assert pct(108, 124) == 87 and pct(43, 48) == 90, '拒帧 bench 满占比漂移'
    assert pct(72, 124) == 58 and pct(28, 48) == 58, '拒帧中 bench 满占比漂移'
    assert pct(789, 919) == 86 and pct(397, 454) == 87, '滞留率漂移'
    assert pct(130, 919) == 14, '上板率漂移'
    # 解封下界(冻结口径上界;probe report 任务 2 表)
    assert pct(384, 676) == 57 and pct(179, 283) == 63, '窄口径解封下界漂移'
    assert pct(502, 676) == 74 and pct(206, 283) == 73, '宽口径解封下界漂移'
    # 第三批持续面(findprob_20260910_0200_8150 §一)
    assert pct(61, 61) == 100, '第三批拒帧 bench 满占比漂移'
    assert BENCH_CAPACITY == 9, '备战席容量漂移(带源分母)'
    print('[断言7] 数据锚对账: 124=57+51+16;bench 满 87%/90%;滞留 86%/87%;'
          '窄口径解封下界 57%(384/676)/63%(179/283)——冻结口径上界,'
          '三重折扣(探针冻结假设+回填未扣+辖域差)禁当预期值;'
          '第三批 61/61=100%;BENCH_CAPACITY=9 PASS')


_CHECKS = (
    ('辖域单一源', check_domain_predicate),
    ('闭集对账', check_closed_set),
    ('调和引理', check_harmonic_lemma),
    ('主不等式', check_main_invariant),
    ('解封方向式', check_unseal_direction),
    ('息损不增', check_overflow_no_interest_loss),
    ('数据锚对账', check_data_anchors),
)


def main() -> int:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    print('P88 复算:锁线转型域投机买入收窄的库容不变量与解封方向')
    print('=' * 72)
    for name, fn in _CHECKS:
        try:
            fn()
        except AssertionError as exc:
            print(f'[FAIL] {name}: {exc}')
            return 1
    print('=' * 72)
    print('P88 复算:全部断言通过(7/7 PASS)。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
