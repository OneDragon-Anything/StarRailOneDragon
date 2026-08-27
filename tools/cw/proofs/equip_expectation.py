"""W210 P14 装备获取期望模型——四通道(发放合成/冶金炉/好运令牌/单位自带)决策表(可重跑)。

对应证明:docs/game/currency_war/research/proofs/p14-equipment-acquisition-ev.md
勘误(aa264947 后重写):商店**不卖装备**(用户口述「商店没有装备」)——旧版「商店直买/
买组件」通道作废;基础件来源=投资策略牌/事件/奖励节点**发放流**,期望成本=轮期望。

数据源(单一源真值,全部 import,不抄数值):
- cw_synthesis:CROSS_RECIPES / SELF_RECIPES / GUANGNENG_* / SYNTHESIS_BASES(K8 闭合图谱)
- cw_equipment_data:EQUIPMENTS(category 判可达性;工具效果原文=好运令牌定向四选一)
- cw_comps:COMP_LIBRARY(20 套终局 comp 的 key_equips = 目标集合来源)

四通道(Q1-Q5):
① 合成(Q1):基础件来自发放流(策略牌/事件/奖励节点;cw_invest_data 实证大量发放牌:
  武装箱系/枪在手/军备供应链/公司军火更新/回收计划/装备方案A·B/概念股初始装等)。
  期望成本 = **轮期望**(Poisson 化发放流下凑齐组件需求向量的 E[轮],数值积分精确);
② 冶金炉(Q2):同类池重抽,进阶池 36 件;有放回/无放回双参数;线性性定理;
③ 回收流水线准入(Q3):不变(基础件 b 合格 iff 不在 A(K) 任何配方里);
④ 好运令牌(Q5,定向四选一;R(c)=待实测)+ 单位自带装备(Q4 随机红利,不可规划;
  刷新间接抽样——金只买角色/经验/刷新)。

不确定参数(显式,勿抄成常量事实):
- λ:每节点期望发放基础件数(粗估 0.5;敏感性 {0.25, 0.5, 1.0})——cw_invest_data
  发放牌频实证粗估(几十张牌含「随机简易装备/简易武装箱」字样),标注假设;
- 发放池:均匀 8 件基础件(标准 7+光能电池;光能电池是否入池待实测,
  equipment_mechanics 待实测边角同源);
- metallurgy replacement:有放回/无放回双分支(已证 ≤0.6pp 不敏感);
- R(c):角色四件推荐进阶表——注册表无结构化数据,**待实测**。

用法: uv run python tools/cw/proofs/equip_expectation.py [--H 名,名 --K comp名 --g --r]
不传参 = 跑证明文档全部数值表 + 3 个 worked example。
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

HERE = Path(__file__).resolve().parent
ROOT = HERE
while not (ROOT / 'pyproject.toml').exists():
    ROOT = ROOT.parent
sys.path.insert(0, str(ROOT / 'src'))

from sr_od.application.currency_war.cw_comps import COMP_LIBRARY  # noqa: E402
from sr_od.application.currency_war.cw_equipment_data import EQUIPMENTS  # noqa: E402
from sr_od.application.currency_war.cw_horizon import TOTAL_NODES  # noqa: E402
from sr_od.application.currency_war.cw_synthesis import (  # noqa: E402
    SYNTHESIS_BASES,
    cross_components,
    self_base,
)

# ===== 参数(显式不确定项;默认=主表口径,敏感性另跑) =====
ADV_POOL_SIZE: int = 36                    # 进阶池件数(K8 闭合全量)
BASIC_POOL_N: int = 8                      # 发放池件数(标准7+光能电池;电池在池=假设待实测)
LAMBDA_DEFAULT: float = 0.5                # 每节点期望发放基础件数(粗估,见 docstring)
LAMBDA_SENS: tuple[float, ...] = (0.25, 0.5, 1.0)
ALL_BASES: frozenset[str] = frozenset(SYNTHESIS_BASES | {'光能电池'})


def components_of(advance: str) -> tuple[str, str] | None:
    """进阶 → 两件基础件组件;不可合成(非进阶/无配方)→ None。"""
    cross = cross_components(advance)
    if cross is not None:
        return cross
    base = self_base(advance)
    if base is not None:
        return (base, base)
    return None


def synth_reachable(advance: str) -> bool:
    """合成可达 = 图谱有配方(36 件进阶全量闭合;白昼/特权/星徽等类别不可达)。"""
    return components_of(advance) is not None


def channel_coverage(advance: str) -> dict[str, bool]:
    """单件缺件的通道覆盖判定(商店不卖装备——无直买通道)。"""
    eq = EQUIPMENTS.get(advance)
    is_advance = eq is not None and eq.category == '进阶'
    return {
        '合成(发放组件)': synth_reachable(advance),
        '冶金炉': is_advance,            # 同类池重抽,需死库存原料
        '好运令牌': is_advance,          # 四件推荐进阶中自选(R(c) 待实测)
        '单位自带': eq is not None,      # 随机红利(进阶/简易均可随单位;规律未知)
    }


# ============================================================ #
# Q1:发放流轮期望(Poisson 化;数值积分精确)
# ============================================================ #

def _survival(k: int, rate: float, t: float) -> float:
    """Erlang(k, rate) 的生存函数 P(T > t)。"""
    rt = rate * t
    return math.exp(-rt) * sum(rt ** j / math.factorial(j) for j in range(k))


def wait_rounds_for_demand(demand: dict[str, int], lam: float = LAMBDA_DEFAULT,
                           pool_n: int = BASIC_POOL_N) -> float:
    """从零库存起,发放流(每节点 Poisson(λ) 件、均匀池 pool_n)凑齐需求向量的 E[轮]。

    各基础件到达为独立 Poisson(lam/pool_n);第 k 件到达时刻 ~ Erlang(k, r)。
    E[max_i T_i] = ∫ (1 − Π_i (1 − S_i(t))) dt,数值积分(指数网格,精度 <1e-4 相对)。
    """
    rate = lam / pool_n
    if not demand:
        return 0.0
    ks = [demand[b] for b in demand]
    scale = max(k for k in ks) / rate          # 积分上界:均值最大分量的 ~3 倍覆盖
    total, h = 0.0, scale / 20000
    for i in range(20000):
        t = (i + 0.5) * h
        p_all_done = 1.0
        for k in ks:
            p_all_done *= 1.0 - _survival(k, rate, t)
        total += (1.0 - p_all_done) * h
    return total


def wait_rounds_with_stock(demand: dict[str, int], stock: dict[str, int],
                           lam: float = LAMBDA_DEFAULT) -> float:
    """已有库存 stock 抵扣后的剩余等待。"""
    residual = {b: max(0, demand[b] - stock.get(b, 0)) for b in demand}
    residual = {b: k for b, k in residual.items() if k > 0}
    return wait_rounds_for_demand(residual, lam)


def q1_full_wait_table(key_equips: list[str], stock: dict[str, int] | None = None,
                       lam: float = LAMBDA_DEFAULT) -> dict[str, object]:
    """Q1:整套 key_equips 的合成账(组件需求向量 + 凑齐轮期望 + 可行性)。"""
    stock = stock or {}
    demand: dict[str, int] = {}
    unreachable: list[str] = []
    for adv in key_equips:
        comp = components_of(adv)
        if comp is None:
            unreachable.append(adv)
            continue
        for b in comp:
            demand[b] = demand.get(b, 0) + 1
    wait = wait_rounds_with_stock(demand, stock, lam)
    return {'组件需求': demand, '不可合成件': unreachable,
            '凑齐轮期望': round(wait, 1),
            '剩余轮上界': TOTAL_NODES,
            '可行(纯等)': wait <= TOTAL_NODES}


def q2_furnace(m: int, k: int, replacement: bool) -> dict[str, float]:
    """Q2:冶金炉重抽。m=可接受缺件数,k=同刷件数。

    期望命中数线性(与放回无关):E = k·m/36。
    P(≥1 命中):有放回 = 1−(1−m/36)^k;无放回 = 1−C(36−m,k)/C(36,k)。
    """
    n = ADV_POOL_SIZE
    p_single = m / n
    if replacement:
        p_at_least_one = 1.0 - (1.0 - p_single) ** k
    else:
        from math import comb
        p_at_least_one = 1.0 - comb(n - m, k) / comb(n, k) if k <= n - m else 1.0
    return {'m': m, 'k': k, '有放回': replacement,
            '期望命中数': round(k * p_single, 4),
            'P_至少一件': round(p_at_least_one, 4)}


def q3_recycle_eligible(basic: str, acceptable_advances: set[str]) -> bool:
    """Q3:基础件回收准入。合格 iff b 不在任何可接受进阶的配方里。"""
    for adv in acceptable_advances:
        comp = components_of(adv)
        if comp and basic in comp:
            return False
    return True


def q4_decision_table(held: set[str], key_equips: list[str],
                      round_no: int, rounds_left: int,
                      stock: dict[str, int] | None = None,
                      lam: float = LAMBDA_DEFAULT,
                      recommendation_hit: bool | None = None) -> list[dict[str, object]]:
    """Q4/Q5:缺件清单 × 通道 → 逐件最优动作(资源=轮/炉/令牌;金不买装备)。

    held:持有装备集;key_equips 含重复(逐槽位);stock:基础件库存;
    recommendation_hit:好运令牌参数(None=推荐表未实测→列待判)。
    """
    need = list(key_equips)
    for h in held:
        if h in need:
            need.remove(h)
    m = len({a for a in need if EQUIPMENTS.get(a) is not None
             and EQUIPMENTS[a].category == '进阶'})
    rows: list[dict[str, object]] = []
    for adv in need:
        cov = channel_coverage(adv)
        r: dict[str, object] = {'缺件': adv, '通道覆盖': [k for k, v in cov.items() if v]}
        comp = components_of(adv)
        if recommendation_hit and cov['好运令牌']:
            r.update({'最优通道': '好运令牌(定向自选,待 R(c) 实测)', '轮成本': 0})
        elif comp is not None:
            single = wait_rounds_for_demand(dict.fromkeys(comp, 1), lam) \
                if len(set(comp)) == 2 else wait_rounds_for_demand({comp[0]: 2}, lam)
            r.update({'最优通道': '合成(用库存+等发放)',
                      '轮成本(缺库存时)': round(single, 1),
                      '可等': single <= rounds_left})
        elif cov['单位自带']:
            r.update({'最优通道': '无常规通道(白昼/特权类)或单位自带随机红利', '轮成本': None})
        rows.append(r)
    rows.append({'附注-冶金炉': f'缺可接受进阶 m={m};炉只刷死库存(角色用法 k=3,期望命中 '
                 f'{round(3 * m / ADV_POOL_SIZE, 3)} 件/炉;m=1 时 0.083/炉≈不留专料)'})
    rows.append({'附注-自带': '买角色=随机红利抽样(规律未知,run26 希儿实证存在);刷新间接'
                 '影响自带抽样,但不可规划——不计入期望通道,只做判读期红利核对'})
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description='P14 装备获取期望决策表(发放流口径)')
    parser.add_argument('--H', default='', help='持有装备,逗号分隔(可空)')
    parser.add_argument('--K', default='', help='目标 comp 名(COMP_LIBRARY)或装备逗号分隔')
    parser.add_argument('--stock', default='', help='基础件库存,名:数 逗号分隔(如 轮滑鞋:3)')
    parser.add_argument('--lam', type=float, default=LAMBDA_DEFAULT, help='每节点发放率 λ')
    parser.add_argument('--r', type=int, default=5, help='当前轮次')
    args = parser.parse_args()

    print('=' * 72)
    print('P14 装备获取期望:Q1-Q5 数值表(发放流口径,商店不卖装备)')
    print('=' * 72)

    # —— Q1:单件进阶的凑齐轮期望(λ 敏感性)——
    print('\n[Q1] 合成凑齐轮期望(Poisson 发放流,均匀池 8,λ 敏感性):')
    print('  单件进阶 = 两件组件;零库存起 E[轮] = E[max(T_a, T_b)](交叉) / E[T_b·2](自配)')
    for lam in LAMBDA_SENS:
        cross_wait = wait_rounds_for_demand({'轮滑鞋': 1, '折叠小刀': 1}, lam)
        self_wait = wait_rounds_for_demand({'和平手枪': 2}, lam)
        print(f'  λ={lam}: 交叉件(两不同基础)={cross_wait:.1f} 轮, 自配件(同基础×2)={self_wait:.1f} 轮')
    print(f'  参照:全局总轮数 TOTAL_NODES={TOTAL_NODES}')

    # —— Q2:冶金炉双参数表(不变)——
    print('\n[Q2] 冶金炉重抽(均匀池 36):P(≥1 命中) 与期望命中')
    from math import comb
    for m in (1, 2, 3, 4):
        for k in (1, 3):
            wr = q2_furnace(m, k, True)
            wo = q2_furnace(m, k, False)
            print(f'  m={m} k={k} | 有放回 {wr["P_至少一件"]:.4f} | 无放回 {wo["P_至少一件"]:.4f} '
                  f'| E[命中] {wr["期望命中数"]:.3f}')
    print(f'  无放回 k=3 增益(m=1): {1 - comb(35, 3) / comb(36, 3):.4f} vs 有放回 {(1 - (35 / 36) ** 3):.4f}'
          '  → 放回差 ≤0.6pp,不敏感')

    # —— Q3:回收准入示例(不变)——
    print('\n[Q3] 回收流水线准入(基础件 → 可接受集 A(K)):')
    for comp_name in ('昼神阿雅', '追击飞霄'):
        ke = next(c.key_equips for c in COMP_LIBRARY if c.name == comp_name)
        acceptable = {a for a in ke if synth_reachable(a)}
        elig = sorted(b for b in ALL_BASES if q3_recycle_eligible(b, acceptable))
        print(f'  {comp_name} A(K)={sorted(acceptable)} → 回收合格基础件: {elig}')

    # —— worked example / 命令行态 ——
    stock: dict[str, int] = {}
    if args.stock:
        for part in args.stock.split(','):
            name, _, cnt = part.partition(':')
            stock[name] = int(cnt or 1)

    if args.K:
        held = {h for h in args.H.split(',') if h}
        ke = (next(c.key_equips for c in COMP_LIBRARY if c.name == args.K)
              if args.K in {c.name for c in COMP_LIBRARY} else args.K.split(','))
        rounds_left = TOTAL_NODES - args.r
        print(f'\n[决策表] H={sorted(held)} stock={stock} K={args.K} λ={args.lam} '
              f'剩 {rounds_left} 轮')
        for row in q4_decision_table(held, ke, args.r, rounds_left, stock, args.lam):
            print(f'  {row}')
        return

    for comp_name in ('昼神阿雅', '追击飞霄', '大黑塔银河学者'):
        comp = next(c for c in COMP_LIBRARY if c.name == comp_name)
        print(f'\n[worked example] {comp_name}: key_equips={comp.key_equips}')
        for lam in LAMBDA_SENS:
            t = q1_full_wait_table(comp.key_equips, stock, lam)
            print(f'  λ={lam}: 组件需求={t["组件需求"]} 凑齐轮期望={t["凑齐轮期望"]} '
                  f'可行(纯等)={t["可行(纯等)"]} 不可合成={t["不可合成件"]}')
        for row in q4_decision_table(set(), comp.key_equips, 5, TOTAL_NODES - 5):
            print(f'  {row}')


if __name__ == '__main__':
    main()
