"""P37v2 晚转 XP 机会成本 期望口径闭合自检(print 仅 ASCII,不进 src)。

复算证明文档 docs/game/currency_war/research/proofs/p37-late-xp-conversion-cost.md (v2):
  (1) 注册表直调锚:利息律常量(INTEREST_THRESHOLD/INTEREST_RATE/回退 cap=THRESHOLD//10)
      与息律投资 interest_cap_override 例外域(开源节流 9/利息上调 10/买断制 0);
  (2) 收益端期望口径 E[I_gain] = q_full x cap,按 resolved cap 域(5/9/10)分列
      —— q_full=0.17-0.25(W959 健康带满息轮占比,单批 n=300 计数,证明 §2 转录);
  (3) 纯金流通道(P51 同源):p<=7 x battle 分层 lambda3=0.065 [0.046,0.086]
      -> 每轮边际危险率 h=1-(1-lambda3)^(1/3) -> h x g(存息帧 g>=50 下界)
      + 败局纯金流差通道(连胜置零底线口径:仅当轮表差,不计断链重爬);
  (4) 金当量显式模型带:L_defer(rho) = rho x L(tau 带 5-8 hp/轮,保守折价假设/关联级);
      rho 敏感性扫描 + 闭合阈值 rho* = E[I_gain]max / L_min;
  (5) 符号裕度表(最劣格= L_min / E[I]max)按 cap 域 x rho 分列;
  (6) 部分息敏感项:翻转所需非满息轮平均附加息量;
  (7) 聚合佐证锚(W959:利息占总收 7.4%、每局中位 18、达帽轮集中 r8-r9)打印。

输入全部为文档引用常数(来源逐条注在行尾),无数据文件依赖,确定性可重跑:
  uv run python tools/cw/proofs/p37/p37v2_ev_closure.py
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

    # ---- (2) 收益端期望口径 ----
    # q_full: W959 健康带(r4-r7)行末金>=50 轮占比 17%-25%(P37 v2 §2 计数带,单批 n=300)
    q_lo, q_hi = 0.17, 0.25
    print('\n== (2) E[I_gain] = q_full x cap (expected-account band) ==')
    e_gain: dict[str, tuple[float, float]] = {}
    for dom, cap in caps.items():
        lo, hi = q_lo * cap, q_hi * cap
        e_gain[dom] = (lo, hi)
        print(f'  {dom:28s} cap={cap:2d}: E[I_gain] = [{fmt(lo)}, {fmt(hi)}] gold/round')

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
    print('  (P51 §5-11 note: magnitude-comparison form only, not a gate; R=dist-to-end is ex-post)')
    # 败局纯金流差(连胜置零底线=仅当轮连胜表差,不计断链重爬 -> 下界)
    diffs = [s + loss for s in STREAK_GOLD_TABLE for loss in LOSS_GOLD_BY_NODE.values()]
    print(f'  per-extra-defeat flow diff (streak-zero floor): '
          f'min={min(diffs)} max={max(diffs)} gold '
          f'(STREAK_GOLD_TABLE={STREAK_GOLD_TABLE}, LOSS_GOLD_BY_NODE={LOSS_GOLD_BY_NODE})')
    # 闭合所需额外败率(点估计与 CI 极端)
    for tag, lam in (('point', lam3_pt), ('CI-lo', lam3_lo)):
        dp_need = (e_gain[DEFAULT_DOM][1] - hazard_per_round(lam) * g_floor) / min(diffs)
        print(f'  {tag}: lambda-path closure needs delta_p_extra >= {fmt(max(dp_need, 0.0))} '
              f'(vs E[I_gain] hi {fmt(e_gain[DEFAULT_DOM][1])})')

    # ---- (4) 金当量显式模型带 ----
    print('\n== (4) L_defer(rho) = rho x L(tau), rho = declared model param (NOT a gate) ==')
    # L(tau): 首达 lv7 每晚 1 轮 ~ 终局 hp -5 ~ -8(W959 代理;v2 降格=保守折价假设/关联级)
    l_lo, l_hi = 5.0, 8.0
    print('  rho grid: L_defer band / worst-cell margin (L_min / E[I_gain]max), default cap=5')
    for rho in (0.15, 0.25, 0.3, 0.4, 0.5):
        m_lo, m_hi = rho * l_lo, rho * l_hi
        margin = m_lo / e_gain[DEFAULT_DOM][1]
        print(f'    rho={fmt(rho)}: L_defer=[{fmt(m_lo)}, {fmt(m_hi)}] '
              f'gold/round; worst-cell margin vs default cap = {fmt(margin)}x')
    rho_star = e_gain[DEFAULT_DOM][1] / l_lo
    print(f'  closure threshold rho* = E[I_gain]max / L_min = {fmt(rho_star)} '
          f'(sign closes, margin>=1); margin>=2x needs rho >= {fmt(2 * rho_star)}')

    # ---- (5) 符号裕度表(按 cap 域) ----
    print('\n== (5) worst-cell margin by resolved-cap domain (rho=0.5 = deprecated-0.5 anchor) ==')
    for dom in caps:
        lo, hi = e_gain[dom]
        print(f'  {dom:28s}: worst {fmt(0.5 * l_lo / hi)}x  best {fmt(0.5 * l_hi / lo)}x')
    print('  maiduanzhi: L==0 -> E[I_gain]==0 -> EV(delay)<0 unconditionally (channel (iii) existence)')

    # ---- (6) 部分息敏感项 ----
    print('\n== (6) partial-interest sensitivity (unmeasured component) ==')
    flip = 0.5 * l_lo - e_gain[DEFAULT_DOM][1]
    non_full_share = 1.0 - q_lo
    print(f'  flip needs extra E[I] >= {fmt(flip)} gold/round over ALL health-band rounds '
          f'-> non-full rounds ({fmt(non_full_share, 2)} share) avg partial interest '
          f'>= {fmt(flip / non_full_share)} gold (g~{int(flip / non_full_share * 10)}+)')
    print('  aggregate corroboration (W959): interest = 7.4% of total income, '
          '18 gold/match median, cap-hitting rounds concentrated r8-r9 (74/120)')

    # ---- (7) 断言(证明文档数值锁) ----
    print('\n== (7) assertions ==')
    d = e_gain[DEFAULT_DOM]
    assert abs(d[0] - 0.85) < 1e-9 and abs(d[1] - 1.25) < 1e-9
    assert abs(lam_band[0] - 0.78) < 0.01 and abs(lam_band[1] - 1.48) < 0.01
    assert min(diffs) == 3 and max(diffs) == 8
    assert abs(rho_star - 0.25) < 1e-9
    m_default = 0.5 * l_lo / e_gain[DEFAULT_DOM][1]
    assert 2.0 <= m_default < 2.1  # 最劣格 2.0x
    m_cap10 = 0.5 * l_lo / e_gain['lixishangdiao(cap10)'][1]
    assert abs(m_cap10 - 1.0) < 0.01  # cap=10 域最劣格仅 1.0x -> 降格声明成立
    print('  all assertions passed (E[I_gain]=0.85-1.25 / lambda-band 0.78-1.48 / '
          'flow diff 3-8 / rho*=0.25 / margins 2.0x & 1.0x)')


if __name__ == '__main__':
    main()
