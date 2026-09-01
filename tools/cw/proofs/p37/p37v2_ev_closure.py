"""P37v2.1 晚转 XP 机会成本 期望口径闭合自检(实机口径重证版;print 仅 ASCII,不进 src)。

复算证明文档 docs/game/currency_war/research/proofs/p37-late-xp-conversion-cost.md (v2.1):
  (1) 注册表直调锚:利息律常量(INTEREST_THRESHOLD/INTEREST_RATE/回退 cap=THRESHOLD//10)
      与息律投资 interest_cap_override 例外域(开源节流 9/利息上调 10/买断制 0);
  (2) 收益端期望口径 E[I_gain] = q_full x cap,按 resolved cap 域(5/9/10)分列
      —— q_full 主口径=实机 replay 语料 154 局健康带(r4-r7 ∧ hp>25)465 轮满息占比
      125/465=0.269(run 级 cluster bootstrap 95%CI [0.212, 0.328];P1 段 0.261/P2 段 0.375
      分列,2026-09-08 λ 基座攻击批复算,见证明 §2A);
      sim 旧带 0.17-0.25(W959,无 CI)仅作对照保留——实机点估计出带上沿,已击穿;
  (3) 纯金流通道(P51 同源):p<=7 x battle 分层 lambda3=0.065 [0.046,0.086]
      -> 每轮边际危险率 h=1-(1-lambda3)^(1/3) -> h x g(存息帧 g>=50 下界)
      + 败局纯金流差通道(连胜置零底线口径:仅当轮表差,不计断链重爬);
  (4) 金当量显式模型带:L_defer(rho) = rho x L(tau 带 5-8 hp/轮,保守折价假设/关联级);
      rho 敏感性扫描 + 闭合阈值 rho* = E[I_gain]max / L_min;
  (5) 符号裕度表(最劣格= L_min / E[I]max)按 cap 域 x rho 分列;
  (6) 部分息敏感项:翻转所需非满息轮平均附加息量;
  (7) 实机口径翻转对照:rho=0.25 恰闭合格与 cap10 域在实机 q_full 下翻转(不闭合)。

输入为注册表直调锚 + 语料现算 q_full(数据锁,见 q_full_corpus.py),确定性可重跑:
  uv run python tools/cw/proofs/p37/p37v2_ev_closure.py   # q_full CI bootstrap 一并现算
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'src'))

from sr_od.application.currency_war.data.cw_factions import (  # noqa: E402
    INTEREST_RATE,
    INTEREST_THRESHOLD,
)
from sr_od.application.currency_war.kernel.cw_economy import (  # noqa: E402
    LOSS_GOLD_BY_NODE,
    STREAK_GOLD_TABLE,
)
from sr_od.application.currency_war.kernel.cw_investments import (
    STRATEGY_ECONOMY,  # noqa: E402
)

DEFAULT_DOM = 'default(no-interest-invest)'

# ---- q_full 主口径(实机重证,2026-09-08;v3.1 起改【数据锁】)----
# 数据锁:Q_K/Q_N/CI 从 replay 语料现算(单一源=同目录 q_full_corpus.py),语料追加即漂移可见,
# 不再锁文档转录值;语料不可得时回退文档转录基准并显式打标(断言链按回退口径仍可跑)。
# 文档 v2.1 定稿转录基准:125/465=0.269,CI [0.212, 0.328];窗户口径见 q_full_corpus.py 文件头
# (最早 run 2026-08-22,更早 runs 已清理——文档 §2A 旧写「08-16 起」为过期表述)。
_DOC_Q_K, _DOC_Q_N, _DOC_Q_LO, _DOC_Q_HI = 125, 465, 0.212, 0.328
try:
    from q_full_corpus import compute as _q_compute  # 同目录,数据锁单一源
    _q = _q_compute()
    Q_K, Q_N, Q_WIN = _q['k'], _q['n'], _q['window']
    Q_PT = Q_K / Q_N
    Q_LO, Q_HI = _q['ci']
    Q_SOURCE = f'CORPUS(数据锁,{Q_WIN[0]}~{Q_WIN[1]})'
except Exception as _e:  # 语料缺失/损坏:回退文档转录,显式打标
    Q_K, Q_N = _DOC_Q_K, _DOC_Q_N
    Q_PT = Q_K / Q_N
    Q_LO, Q_HI = _DOC_Q_LO, _DOC_Q_HI
    Q_SOURCE = f'DOC-FALLBACK({_e.__class__.__name__})'
Q_SIM_LO, Q_SIM_HI = 0.17, 0.25      # W959 sim 旧带(已被实机点估计击穿,仅对照)
Q_DRIFT_TOL = 0.03                   # 文档检验点 1:点估计漂移 >0.03 需重标裕度行


def fmt(x: float, n: int = 2) -> str:
    return f'{x:.{n}f}'


def hazard_per_round(lam3: float) -> float:
    """3 轮累积危险率 -> 每轮边际危险率(等危险率折算)。"""
    return 1.0 - (1.0 - lam3) ** (1.0 / 3.0)


def main() -> None:
    # ---- (1) 注册表直调锚 ----
    print('== (1) registry anchors (direct import, no transcription) ==')
    base_cap = INTEREST_THRESHOLD // 10  # cw_economy L411 回退式同一口径
    print(f'INTEREST_THRESHOLD={INTEREST_THRESHOLD} INTEREST_RATE={INTEREST_RATE} '
          f'-> full-interest gold/round = {int(INTEREST_THRESHOLD * INTEREST_RATE)}; '
          f'base_cap(fallback)={base_cap}')
    overrides = {k: v.interest_cap_override for k, v in STRATEGY_ECONOMY.items()
                 if v.interest_cap_override is not None}
    print(f'interest_cap_override domain: {overrides}  (resolved-cap law; P47 A1 / P35 errata)')
    caps = {DEFAULT_DOM: 5, 'kaiyuanjieliu(cap9)': 9, 'lixishangdiao(cap10)': 10}

    # ---- (2) 收益端期望口径(实机主口径)----
    print('\n== (2) E[I_gain] = q_full x cap (expected account; REAL-MACHINE q_full primary) ==')
    print(f'  q_full real-machine: {Q_K}/{Q_N} = {fmt(Q_PT, 3)} [{Q_SOURCE}] '
          f'(cluster-bootstrap95 [{fmt(Q_LO, 3)}, {fmt(Q_HI, 3)}] N=2000 seed=37; '
          f'doc-transcribed baseline 125/465=0.269 [0.212, 0.328])')
    print(f'  q_full sim legacy band (W959): [{Q_SIM_LO}, {Q_SIM_HI}] '
          f'-- POINT ESTIMATE EXCEEDS UPPER EDGE (breached, comparison only)')
    e_pt: dict[str, float] = {}
    e_lo: dict[str, float] = {}
    e_hi: dict[str, float] = {}
    for dom, cap in caps.items():
        e_pt[dom] = Q_PT * cap
        e_lo[dom] = Q_LO * cap
        e_hi[dom] = Q_HI * cap
        print(f'  {dom:28s} cap={cap:2d}: E[I_gain] pt={fmt(e_pt[dom])} '
              f'(CI [{fmt(e_lo[dom])}, {fmt(e_hi[dom])}]) gold/round')

    # ---- (3) 纯金流通道 ----
    print('\n== (3) pure-gold-flow channels (axiom-primary cross-check) ==')
    # lambda3: P51 §4-B-2 分层表 p<=7 x battle = 0.065 [0.046, 0.086](3 轮累积危险率,直测)
    lam3_pt, lam3_lo, lam3_hi = 0.065, 0.046, 0.086
    g_floor = 50  # 存息帧定义下界(行末金>=50)
    for lam in (lam3_lo, lam3_pt, lam3_hi):
        print(f'  lambda3={fmt(lam, 3)} -> per-round hazard h={fmt(hazard_per_round(lam), 4)} '
              f'-> h x g(g=50) = {fmt(hazard_per_round(lam) * g_floor)} gold/round')
    lam_band = (hazard_per_round(lam3_lo) * g_floor, hazard_per_round(lam3_hi) * g_floor)
    print(f'  death-clearing exposure band (g=50 floor): [{fmt(lam_band[0])}, {fmt(lam_band[1])}] gold/round')
    print(f'  vs E[I_gain] real-machine point {fmt(e_pt[DEFAULT_DOM])}: '
          f'death channel point {fmt(hazard_per_round(lam3_pt) * g_floor)} is BELOW it '
          f'(same magnitude, no longer covers the point; defeat-flow channel needed)')
    print('  (P51 §5-11 note: magnitude-comparison form only, not a gate; R=dist-to-end is ex-post)')
    # 败局纯金流差(连胜置零底线=仅当轮连胜表差,不计断链重爬 -> 下界)
    diffs = [s + loss for s in STREAK_GOLD_TABLE for loss in LOSS_GOLD_BY_NODE.values()]
    print(f'  per-extra-defeat flow diff (streak-zero floor): '
          f'min={min(diffs)} max={max(diffs)} gold '
          f'(STREAK_GOLD_TABLE={STREAK_GOLD_TABLE}, LOSS_GOLD_BY_NODE={LOSS_GOLD_BY_NODE})')
    # 闭合所需额外败率(实机点估计与 CI 极端)
    for tag, lam, e_ref in (('point', lam3_pt, e_pt[DEFAULT_DOM]),
                            ('CI-extreme(E hi vs lam lo)', lam3_lo, e_hi[DEFAULT_DOM])):
        dp_need = (e_ref - hazard_per_round(lam) * g_floor) / min(diffs)
        print(f'  {tag}: lambda-path closure needs delta_p_extra >= {fmt(max(dp_need, 0.0))} '
              f'(vs E[I_gain] ref {fmt(e_ref)})')

    # ---- (4) 金当量显式模型带 ----
    print('\n== (4) L_defer(rho) = rho x L(tau), rho = declared model param (NOT a gate) ==')
    # L(tau): 首达 lv7 每晚 1 轮 ~ 终局 hp -5 ~ -8(W959 代理;保守折价假设/关联级)
    l_lo, l_hi = 5.0, 8.0
    print('  rho grid: L_defer band / worst-cell margin (L_min / E[I_gain] pt), default cap=5')
    for rho in (0.15, 0.25, 0.269, 0.3, 0.4, 0.5):
        m_lo, m_hi = rho * l_lo, rho * l_hi
        margin = m_lo / e_pt[DEFAULT_DOM]
        print(f'    rho={fmt(rho, 3)}: L_defer=[{fmt(m_lo)}, {fmt(m_hi)}] '
              f'gold/round; worst-cell margin vs default cap = {fmt(margin)}x')
    rho_star = e_pt[DEFAULT_DOM] / l_lo
    rho_star_ci = e_hi[DEFAULT_DOM] / l_lo
    print(f'  closure threshold rho* = E[I_gain]pt / L_min = {fmt(rho_star, 3)} '
          f'(sign closes, margin>=1); CI-upper rho* = {fmt(rho_star_ci, 3)}')
    print(f'  margin>=2x needs rho >= {fmt(2 * rho_star, 3)} (point) / {fmt(2 * rho_star_ci, 3)} (CI hi)')
    print('  v2->v2.1 flip: sim band rho*=0.25 -> real-machine rho*=0.269; '
          'the rho=0.25 "exactly closes" cell NO LONGER closes (0.93x)')

    # ---- (5) 符号裕度表(按 cap 域,实机口径)----
    print('\n== (5) worst-cell margin by resolved-cap domain (rho=0.5 = deprecated-0.5 anchor) ==')
    for dom in caps:
        print(f'  {dom:28s}: worst {fmt(0.5 * l_lo / e_pt[dom])}x (pt) '
              f'/ {fmt(0.5 * l_lo / e_hi[dom])}x (CI hi)  best {fmt(0.5 * l_hi / e_lo[dom])}x')
    print('  maiduanzhi: L==0 -> E[I_gain]==0 -> EV(delay)<0 unconditionally (channel (iii) existence)')

    # ---- (6) 部分息敏感项 ----
    print('\n== (6) partial-interest sensitivity (unmeasured component) ==')
    flip = 0.5 * l_lo - e_hi[DEFAULT_DOM]
    if flip <= 0:
        print(f'  flip already achieved at CI upper WITHOUT partial interest: '
              f'E[I_gain] hi {fmt(e_hi[DEFAULT_DOM])} >= L_defer(rho=0.5) lo {fmt(0.5 * l_lo)}')
    non_full_share = 1.0 - Q_PT
    flip_pt = 0.5 * l_lo - e_pt[DEFAULT_DOM]
    print(f'  (point) flip needs extra E[I] >= {fmt(max(flip_pt, 0.0))} gold/round over ALL rounds '
          f'-> non-full rounds ({fmt(non_full_share, 2)} share) avg partial interest '
          f'>= {fmt(max(flip_pt, 0.0) / non_full_share)} gold')
    print('  aggregate corroboration (W959 sim): interest = 7.4% of total income, '
          '18 gold/match median, cap-hitting rounds concentrated r8-r9 (74/120)')

    # ---- (7) 断言(数据锁:从语料现算,不锁文档转录)----
    print('\n== (7) assertions (data-locked: q_full recomputed from corpus) ==')
    d_pt = e_pt[DEFAULT_DOM]
    # 数据锁三道:①点估计与 CI 覆盖自洽;②对文档转录基准的漂移在容差内(>0.03 触发重标,
    # 与证明检验点 1 同口径);③结构断言(通道/裕度)按现算点派生,两处翻转随语料实时判
    assert Q_LO - 1e-9 <= Q_PT <= Q_HI + 1e-9, f'q_full point {Q_PT:.4f} outside own CI'
    assert abs(Q_PT - _DOC_Q_K / _DOC_Q_N) <= Q_DRIFT_TOL, (
        f'q_full drifted {Q_PT - _DOC_Q_K / _DOC_Q_N:+.4f} vs doc baseline 0.269 '
        f'(> {Q_DRIFT_TOL}: margins in doc need re-stamping)')
    assert Q_LO < _DOC_Q_HI and Q_HI > _DOC_Q_LO, 'CI no longer overlaps doc band'
    assert abs(d_pt - Q_K / Q_N * 5) < 1e-9
    assert abs(lam_band[0] - 0.78) < 0.01 and abs(lam_band[1] - 1.48) < 0.01
    assert min(diffs) == 3 and max(diffs) == 8
    assert abs(rho_star - Q_PT) < 1e-9            # rho* = q_full(cap5 域内 L_min=5)
    m_default = 0.5 * l_lo / d_pt                  # rho=0.5 最劣格裕度(随语料现算)
    m_cap10 = 0.5 * l_lo / e_pt['lixishangdiao(cap10)']
    m_rho25 = 0.25 * l_lo / d_pt
    if m_rho25 >= 1.0:
        print(f'  [FLIP-BACK] rho=0.25 cell re-closes at current corpus '
              f'(margin {fmt(m_rho25)}x >= 1) -- doc v2.1 flip statement stale')
    else:
        print(f'  rho=0.25 worst-cell margin {fmt(m_rho25)}x < 1 (flip holds: not closing)')
    if m_cap10 >= 1.0:
        print(f'  [FLIP-BACK] cap10-domain rho=0.5 margin {fmt(m_cap10)}x >= 1 (re-closes)')
    else:
        print(f'  cap10-domain rho=0.5 margin {fmt(m_cap10)}x < 1 (flip holds: not closing)')
    print(f'  all assertions passed (q_full={fmt(Q_PT, 3)} [{Q_SOURCE}] E[I_gain]pt={fmt(d_pt)} '
          f'[CI {fmt(e_lo[DEFAULT_DOM])},{fmt(e_hi[DEFAULT_DOM])}] / rho*={fmt(rho_star, 3)} '
          f'/ rho=0.5 margin {fmt(m_default)}x)')


if __name__ == '__main__':
    main()
