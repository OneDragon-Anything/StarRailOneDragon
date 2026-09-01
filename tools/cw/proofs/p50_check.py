"""P50 冶金炉角色用法与回收流水线 数值自检(不进 src;print 仅 ASCII)。

复算证明文档 docs/game/currency_war/research/proofs/p50-furnace-character-mode-ev.md:
  (1) 注册表地基:简易池 8 / 进阶池 36 / K8 闭合(8 基础件);冶金炉效果文本双用法;
      升级锅炉(金增强 230801)效果文本「简易→随机进阶 + 获 2 个炉」;
  (2) 吞吐账:每炉命中率表(P(>=1 命中) 与 E[命中数],r=1..3 次重掷;
      基础 1/8 -> 1-(7/8)^3 = 169/512 = 0.330078125;进阶 1/36 -> 1-(35/36)^3
      = 3781/46656 ~= 0.081036)——亲算并锁;
  (3) 可接受集 m 泛化:每炉命中率 1-((N-m)/N)^3 与 E[炉次->首中] 两口径(R1/B1 修正):
      单件 = N/m(每炉 1 掷);角色 = 1/q(几何分布,q=1-((N-m)/N)^3)——NOT N/(3m)
      (后者是线性口径误配,炉次比恒 <3:进阶 m=1 真 3781/1296≈2.918、简易 m=1
      真 169/64≈2.641;E[命中数/炉]=3m/N 才恰 3 倍),m=1..4 全表断言;
  (4) 批量账:d 件死库存 -> ceil(d/3) 炉;每件炉耗表 d=1..9,角色模式 d>=2 严格省,
      最优点在 d==0 (mod 3);
  (5) 组件路径期望(精确线性方程组解):交叉目标 E[基础重掷]=12 / 自配=16 vs
      进阶直取=36——合成免费(equipment_mechanics)下组件路径炉效 2.25-3 倍;
  (6) 升级锅炉账:每用净炉增量 +1(-1+2),炉库存单调不降(F0>=1 永不枯竭);
      期望基础件消耗 36/命中;三通道资源账单 + 盈亏平衡不等式;
  (7) 准入捆绑约束(R1 两支,min(d,3) 显式建模):
      (a) 替换支(池>=3):同 d 同 r,EV 退化 = -Sum(ell) 线性、零吞吐补偿;
      (b) 增量支(池<3):混批增大 d -> 多得一次掷,净账 = w - ell(边际掷价值 w),
          占优性由 p42 ③ 支配不等式(ell >= w)承接,ell < w 的可违格显式不闭合;
      部分批 d=2 严格优于 2 次单件(同分布结果、更少炉);
  (8) 时机:确定性交换论证——同一到达流(炉到货/合格件凑齐)下,批模式策略的
      炉消耗 <= 单件模式,等号仅当合格池从未达到 2;
  (9) 产出处置(R4 修正):按剩余需求向量(含成品同名抵扣)分类——进阶先过
      「y ∈ 剩余 K」、基础按 component_demand 正缺口(hoard_gaps 为其机械化,
      支撑只含基础件);hoard_gaps/recycle_qualified 互斥性例证(阿雅线)。

口径:池均匀 = p42 A9 同款承重假设(实测分布后幅度项复核);炉到货外生
(投资牌流,economy §8 / equipment_mechanics §5 获取通道)。
"""
import os
import random
import sys
from fractions import Fraction

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'src'))

from sr_od.application.currency_war.data.cw_equipment_data import (
    EQUIPMENTS,  # noqa: E402
)
from sr_od.application.currency_war.data.cw_invest_data import (
    PLAZA_AUGMENTS,  # noqa: E402
)
from sr_od.application.currency_war.data.cw_synthesis import (  # noqa: E402
    component_demand,
    hoard_gaps,
    recycle_qualified,
)

N_BASIC = 8    # 简易池(p42 A9:含光能电池 8 件均匀)
N_ADV = 36     # 进阶池(K8 闭合:C(8,2)=28 交叉 + 8 自配)


def check(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


# ---------- (1) 注册表地基 ----------
basics = [n for n, e in EQUIPMENTS.items() if e.category == '简易']
advances = [n for n, e in EQUIPMENTS.items() if e.category == '进阶']
check(len(basics) == N_BASIC, f'简易池 {len(basics)} != 8')
check(len(advances) == N_ADV, f'进阶池 {len(advances)} != 36')
furnace = EQUIPMENTS['冶金炉']
check(furnace.category == '工具', '冶金炉类别应为工具')
check('同类型的随机' in furnace.effect and '取下所有装备' in furnace.effect,
      '冶金炉效果文本应含单件/角色双用法')
boiler = next(a for a in PLAZA_AUGMENTS if a.id == '230801')
check(boiler.name == '升级锅炉' and '随机进阶' in boiler.effect and '获得2个' in boiler.effect,
      '升级锅炉 230801 效果文本不符')
print(f'[1] registry: basics={len(basics)} advances={len(advances)} '
      f'furnace=ok boiler=ok({boiler.id})')

# ---------- (2) 吞吐账(每炉命中率,r=重掷数) ----------
print('\n[2] per-furnace hit (m=1):')
print('  r | basic P(>=1) | adv P(>=1)   | E[hits] basic | E[hits] adv')
rows = []
for r in (1, 2, 3):
    pb = 1 - Fraction(N_BASIC - 1, N_BASIC) ** r
    pa = 1 - Fraction(N_ADV - 1, N_ADV) ** r
    rows.append((r, pb, pa))
    print(f'  {r} | {float(pb):.6f}    | {float(pa):.6f}    | {r}/{N_BASIC}={r / N_BASIC:.4f}'
          f'  | {r}/{N_ADV}={r / N_ADV:.4f}')
check(rows[2][1] == Fraction(169, 512), 'basic r=3 应恰为 169/512')
check(rows[2][2] == Fraction(3781, 46656), 'adv r=3 应恰为 3781/46656')
check(abs(float(rows[2][1]) - 0.330078125) < 1e-12, 'basic r=3 ~ 0.3301 (33%)')
check(abs(float(rows[2][2]) - 0.081036) < 1e-5, 'adv r=3 ~ 0.0810 (8.1%)')
check(Fraction(1, N_BASIC) == Fraction(1, N_BASIC) * 1, 'per-item hit unchanged r=1')
# 每件命中率不变(m/N);每炉 P(>=1) 严格小于 E[命中数](无放回耦合的重叠事件)
check(1 - Fraction(N_BASIC - 1, N_BASIC) ** 3 < 3 * Fraction(1, N_BASIC),
      'basic r=3: P(>=1) 应 < E[hits]=3/8(非线性折扣)')

# ---------- (3) 可接受集 m 泛化(R1/B1 修正:炉次口径 = 几何分布 1/q) ----------
print('\n[3] acceptable-set m: two calibers (furnace geometric 1/q vs hits linear 3m/N)')
print('  m | basic P | adv P | E[furn] single adv | batch adv=1/q | ratio(<3) | batch basic=1/q')
adv_batch_anchor = {1: Fraction(46656, 3781), 2: Fraction(5832, 919),
                    3: Fraction(1728, 397), 4: Fraction(729, 217)}
basic_batch_anchor = {1: Fraction(512, 169), 2: Fraction(64, 37),
                      3: Fraction(512, 387), 4: Fraction(8, 7)}
for m in (1, 2, 3, 4):
    pb = 1 - Fraction(N_BASIC - m, N_BASIC) ** 3
    pa = 1 - Fraction(N_ADV - m, N_ADV) ** 3
    e_single_a = Fraction(N_ADV, m)          # 单件:1 炉 = 1 掷,几何 p=m/N
    e_batch_a = 1 / pa                       # 角色:1 炉 = 伯努利 q=pa,E = 1/q
    e_batch_b = 1 / pb
    ratio = e_single_a / e_batch_a           # 炉次口径批量/单件比(恒 <3)
    print(f'  {m} | {float(pb):.4f} | {float(pa):.4f} | {float(e_single_a):7.3f} '
          f'| {float(e_batch_a):14.3f} | {float(ratio):.4f} | {float(e_batch_b):.4f}')
    check(pb > pa, '同 m 下基础池每炉命中率应更高')
    check(e_batch_a == adv_batch_anchor[m], f'adv m={m}: E[furnace] batch 应为精确分数 1/q')
    check(e_batch_b == basic_batch_anchor[m], f'basic m={m}: E[furnace] batch 应为精确分数 1/q')
    check(ratio < 3, f'm={m}: 炉次口径比应严格 <3(几何分布非线性折扣)')
    check(e_batch_a > Fraction(N_ADV, 3 * m),
          f'm={m}: N/(3m) 系统低估批量所需炉数(初稿错误列,已废止)')
# 口径分层:恰 3 倍只在 E[命中数/炉](线性口径)成立 —— 3m/N / (m/N) = 3
for m in (1, 2, 3, 4):
    check(Fraction(3 * m, N_ADV) == 3 * Fraction(m, N_ADV),
          'E[hits/furnace] 线性口径恰 3 倍(与炉次口径 <3 并存,口径分层)')
check(Fraction(N_ADV, 1) / adv_batch_anchor[1] == Fraction(3781, 1296),
      'adv m=1 炉次比应恰 3781/1296 (约2.918)')
check(Fraction(N_BASIC, 1) / basic_batch_anchor[1] == Fraction(169, 64),
      'basic m=1 炉次比应恰 169/64 (=2.641)')

# ---------- (4) 批量账 ceil(d/3) ----------
print('\n[4] d items -> furnaces & furnace-per-item:')
print('  d | furn | f/item')
best = {}
for d in range(1, 10):
    f = -(-d // 3)
    best[d] = f / d
    print(f'  {d} |  {f}   | {f / d:.3f}')
check(best[1] == 1.0, 'd=1 每件 1 炉')
check(abs(best[2] - 0.5) < 1e-12 and abs(best[3] - 1 / 3) < 1e-12,
      'd=2/3 每件炉耗应 1/2, 1/3')
check(all(best[d] < 1.0 for d in range(2, 10)), 'd>=2 角色模式严格省炉')
check(best[3] == min(best.values()), '最优点 d=3(此后 6 同值)')

# ---------- (5) 组件路径期望(精确解) ----------
# 状态 = 已持有组件集合(目标 A = 交叉(b1,b2) 或自配 b*2);
# 每次基础重掷:1/8 落各基础件。求 E[重掷数 | 完成收集]。
def e_collect(cross: bool) -> float:
    """E[rerolls] to complete cross(b1,b2) / self(b twice), exact linear solve."""
    if cross:
        # E0: none held; Eb: one of the two held(needing the other, symmetric)
        # E0 = 1 + (1/8)*Eb + (1/8)*Eb + (6/8)*E0 ; Eb = 1 + (7/8)*Eb
        eb = 1 / (1 - 7 / 8)
        e0 = (1 + 2 * eb / 8) / (1 - 6 / 8)
        return e0
    # self: negative binomial r=2, p=1/8
    return 2 / (1 / 8)

e_cross, e_self, e_direct = e_collect(True), e_collect(False), float(N_ADV)
print(f'\n[5] component path: cross={e_cross:.4f} self={e_self:.4f} direct={e_direct:.1f}')
check(abs(e_cross - 12.0) < 1e-9, '交叉目标 E[基础重掷] 应恰 12')
check(abs(e_self - 16.0) < 1e-9, '自配目标 E[基础重掷] 应恰 16')
check(e_cross < e_direct and e_self < e_direct, '组件路径炉效应优于进阶直取')
check(abs(e_direct / e_cross - 3.0) < 1e-9, '直取/交叉 恰 3 倍')
check(abs(e_direct / e_self - 2.25) < 1e-9, '直取/自配 恰 2.25 倍')

# ---------- (6) 升级锅炉账 ----------
# 对简易使用:耗 1 炉 -> 随机进阶 + 获 2 炉 => 净炉增量 +1/用。
delta = -1 + 2
check(delta == 1, '锅炉净炉增量应为 +1')
f0, stock, min_stock = 1, 1, 1
for _ in range(1000):            # 库存路径:F0>=1 时单调不降、永不为 0
    stock += delta
    min_stock = min(min_stock, stock)
check(min_stock >= f0, '锅炉模式下炉库存应单调不降(F0=1)')
e_boiler_basics = float(N_ADV)   # 每用 1/36 命中特定进阶 -> E[基础件消耗]=36
print(f'\n[6] boiler: delta=+1 furnace/use, min_stock={min_stock}, '
      f'E[basic consumed per hit]={e_boiler_basics:.0f}')
# 三通道资源账单(目标 = 特定进阶 A):
#   advance-mode : E=36 炉   , 0 件库存销毁(循环喂)
#   component    : E=12/16 炉, 2 件基础死库存销毁(合成消耗), 合成免费
#   boiler       : E=0 净炉  , E=36 件基础死库存销毁(+1 炉/用自给)
# 盈亏平衡(R2 方向修正):boiler 优 <=> 36*v_B - salvage < 12*v_F + 2*v_B
#   <=> v_F/v_B > (36-2-salvage/v_B)/12 <= 34/12(salvage>=0 ⟹ 阈值 <= 34/12,
#   salvage=0 取上确界 = 保守充分阈;salvage 升高阈值降低、更利好锅炉;自配通道
#   (34-s)/16 更低,17/6 为两通道最保守值)
breakeven = Fraction(36 - 2, 12)
check(breakeven == Fraction(17, 6), '盈亏平衡比应为 17/6 ~ 2.833')
print('  channel bills: adv=36 furnaces | comp=12/16 furnaces + 2 basics | '
      'boiler=36 basics + 0 net furnaces')
print(f'  breakeven v_F/v_B > {float(breakeven):.3f} (conservative sufficient threshold, '
      f'salvage=0 supremum; salvage raises -> threshold drops, favors boiler)')

# ---------- (7) 准入捆绑约束(R1 两支:min(d,3) 显式建模) ----------
# r = min(d, 3):d = 入池件数。替换支(池>=3)与增量支(池<3)分账。
def rerolls(d: int) -> int:
    """每炉重掷数 = min(d,3);混入有用件会增大 d —— 池<3 时多得一次掷。"""
    return min(d, 3)


def batch_ev(d: int, ells: list[float], per_reroll: float = 1.0) -> float:
    """EV = 重掷吞吐价值 − 混入有用件损失(符号项,未货币化辖域)。"""
    return rerolls(d) * per_reroll - sum(ells)


# (a) 替换支(池>=3):同 d=3,有用件换掉合格件,r 不变 → 退化恰 -Sum(ell) 线性
clean = batch_ev(3, [])
check(rerolls(3) == 3 and abs(batch_ev(3, [0.2, 0.35]) - (clean - 0.55)) < 1e-12,
      '(a) 替换支:同 d 同 r,退化应恰为 -Sum(ell) 线性(零吞吐补偿)')
# (b) 增量支(池<3):纯批 d=2 → 2 掷;混 1 件 d=3 → 3 掷,净账 = w − ell
w = 1.0    # 边际掷期望价值(符号项)
ell = 0.4
check(rerolls(2) == 2 and rerolls(3) == 3, 'min(d,3) 显式建模:池<3 混批多得一次掷')
check(abs((batch_ev(3, [ell]) - batch_ev(2, [])) - (w - ell)) < 1e-12,
      '(b) 增量支净账应 = w − ell')
# 占优判归 p42 ③ 支配不等式(ell >= w ⟹ 混入被支配);本脚本只验符号账方向:
check(batch_ev(3, [w]) <= batch_ev(2, []),
      'ell >= w(取等边界)时增量混入不占优 —— p42 ③ 支配辖域')
check(batch_ev(3, [0.5 * w]) > batch_ev(2, []),
      'ell < w(p42 ③ 带内可违格形态)时增量混入占优 —— 显式未闭合边角,判归 p42 层 1')
# 部分批 d=2 严格优于 2 次单件:同分布结果(每次重掷独立同分布),炉 1 < 2。
rng = random.Random(50)
furn_single = furn_batch = 0
hit_single = hit_batch = 0
p = 1 / N_ADV
for _ in range(20000):
    furn_single += 2                                   # 两件各单件用炉
    hit_single += (rng.random() < p) + (rng.random() < p)
    furn_batch += 1                                    # 同两件穿一人,角色用法 1 炉
    hit_batch += (rng.random() < p) + (rng.random() < p)
print(f'\n[7] admission: linear degradation ok | MC d=2: furnaces {furn_single} vs '
      f'{furn_batch}, hits {hit_single} vs {hit_batch}')
check(furn_batch * 2 == furn_single, 'MC: 批模式炉耗应恰为单件模式之半')
check(abs(hit_batch - hit_single) < 4 * (furn_single ** 0.5), 'MC: 命中数应同分布')

# ---------- (8) 时机:确定性交换论证 ----------
# 同一到达流(事件序固定):策略 S=炉到货即对每件单件用;B=凑满 min(3,pool) 批用。
# 结论:对任意到达流,B 的炉耗 <= S,等号仅当合格池从未 >= 2。
def simulate(stream, batch_policy: bool):
    """stream: 事件序列,'F'=炉到货,'I'=一件合格死库存到库。返回炉耗/重掷数。"""
    furnaces = items = used_f = rerolls = 0
    for ev in stream:
        if ev == 'F':
            furnaces += 1
        else:
            items += 1
        # 决策:有炉且有件
        while furnaces >= 1 and items >= (3 if batch_policy else 1):
            k = min(3 if batch_policy else 1, items)
            items -= k
            furnaces -= 1
            used_f += 1
            rerolls += k
    return used_f, rerolls

streams = ['FIIFIF', 'FFIIII', 'IFIFIF', 'IIIIIIFF', 'FIFIIFFI', 'IIFIFIIF']
print('\n[8] timing exchange (used_f, rerolls):')
for s in streams:
    su = simulate(s, False)
    ba = simulate(s, True)
    print(f'  {s}: single={su} batch={ba}')
    check(ba[0] <= su[0], '批模式炉耗应 <= 单件模式')
# 注:部分清算流上批模式的「掷数」可多可少(炉充裕时批模式多掷、炉稀缺时少掷)——
# 交换论证的主张是炉耗维度;完整清算流(库存清空)下掷数相等、炉耗严格低:
# 完整清算流(9 件 + 炉充裕到各自都能清空):两模式掷数同为 9,炉耗 3 vs 9:
su_total = simulate('I' * 9 + 'F' * 9, False)
ba_total = simulate('I' * 9 + 'F' * 9, True)
check(ba_total[0] < su_total[0] and su_total[0] == 9 and ba_total[0] == 3,
      '完整清算下批模式炉耗应严格低(3 vs 9)')
check(ba_total[1] == su_total[1] == 9, '完整清算下两模式掷数应同为 9(清空库存)')
print(f'  full-clear 9 items / furnaces-rich: single={su_total} batch={ba_total}')

# ---------- (9) 产出处置:hoard_gaps 分类 + recycle_qualified 互斥 ----------
k_aya = ['反重力皮靴', '反重力皮靴', '火力风暴潮']       # 阿雅线(p42 ① 同例)
demand = component_demand(k_aya)
rq = recycle_qualified(k_aya)
check('轮滑鞋' in demand and '轮滑鞋' not in rq, '需求件不应回收合格')
check('以太钻头' in rq, '非需求基础件应回收合格')
check(rq.isdisjoint(set(demand)), 'recycle_qualified 与需求向量应互斥')
gaps = hoard_gaps(k_aya, owned=['轮滑鞋', '轮滑鞋', '折叠小刀'])
check(gaps == {'轮滑鞋': 3}, '轮滑鞋缺 5-2=3、小刀已齐(5=皮靴2双4+风暴潮1)')
gaps2 = hoard_gaps(k_aya, owned=['轮滑鞋'])
check(gaps2 == {'轮滑鞋': 4, '折叠小刀': 1}, '缺口 = 需求向量减库存(5-1, 1-0)')


# R4 修正:按剩余需求向量(含成品同名抵扣)分类,hoard_gaps 只覆盖基础件段
# (其支撑不含进阶成品——按字面支撑判会把目标进阶件误入批量池)。
def classify_output(y: str, k: list[str], owned: list[str]) -> str:
    """产出处置:返回 'hoard' / 'batch_pool' / 'merge21'。

    进阶:先过「y ∈ 剩余 K」(owned 同名成品 1:1 抵扣)——命中囤、未命中入批量池;
    简易:component_demand(剩余 K) 正缺口(hoard_gaps 机械化)——命中囤、否则 2合1。
    """
    rem = list(k)
    for o in owned:
        if o in rem:
            rem.remove(o)
    cat = EQUIPMENTS[y].category
    if cat == '进阶':
        return 'hoard' if y in rem else 'batch_pool'
    if cat == '简易':
        return 'hoard' if y in hoard_gaps(rem, owned) else 'merge21'
    return 'other'


# hoard_gaps 的字面支撑不含进阶成品(R4 陷阱实证):
check('反重力皮靴' not in gaps2, 'hoard_gaps 支撑只含基础件(目标进阶件不在差集)')
check(classify_output('反重力皮靴', k_aya, []) == 'hoard',
      'R4: 目标进阶成品命中剩余 K → 囤(旧字面规则会误判入批量池)')
check(classify_output('火力风暴潮', k_aya, []) == 'hoard', 'R4: 目标进阶成品(第2件)→ 囤')
check(classify_output('电磁弹射器', k_aya, []) == 'batch_pool',
      'R4: 非目标进阶 → 入批量池')
check(classify_output('反重力皮靴', k_aya, ['反重力皮靴', '反重力皮靴']) == 'batch_pool',
      'R4: 成品已抵扣满(剩余 K 不含)→ 非目标进阶 → 入批量池')
check(classify_output('轮滑鞋', k_aya, ['轮滑鞋']) == 'hoard', 'R4: 基础件命中组件缺口 → 囤')
check(classify_output('以太钻头', k_aya, ['轮滑鞋']) == 'merge21',
      'R4: 非需求基础件 → 2合1 流水线前段')
print(f'\n[9] disposal: demand={dict(demand)} rq={sorted(rq)} gaps={gaps2} '
      f'classify(R4)=target-adv:hoard non-target-adv:batch_pool')

print('\nALL P50 CHECKS PASSED')
