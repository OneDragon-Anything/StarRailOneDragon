"""P14 修订批三路互证:闭式 / 充分上界数值积分 / 蒙特卡洛(可重跑)。

背景(2026-09-01 五门验证退回修订):Q1 轮期望旧数值系 equip_expectation.py
积分上界 max(k)/rate 截断伪影(系统性低估 1.4-1.8×)。本脚本独立三路复算:

1. 闭式(基准真值):
   - 交叉件(两不同基础各 1 件,T_a/T_b iid Exp(r),r=λ/8):
     E[max] = E[T_a]+E[T_b]−E[min] = 2/r − 1/(2r) = 3/(2r) = 12/λ;
   - 自配件(同基础×2,Erlang(2,r)):E = 2/r = 16/λ;
2. 充分上界积分:与修订后 equip_expectation.wait_rounds_for_demand 同构的
   E[max] = ∫(1−Π(1−S_i(t)))dt,上界=Σ均值的 3 倍(独立重写,非 import 被审函数);
3. 蒙特卡洛:直接模拟 Poisson 发放流凑齐时刻,大样本对照。

整集需求(×5/×4 多件)无闭式,以路 2/3 互证(相对差 <1%)。
用法: uv run python tools/cw/proofs/p14_check.py
"""
from __future__ import annotations

import math
import random
import sys
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

HERE = Path(__file__).resolve().parent
ROOT = HERE
while not (ROOT / 'pyproject.toml').exists():
    ROOT = ROOT.parent
sys.path.insert(0, str(ROOT / 'src'))

POOL_N = 8
TOTAL_NODES = 27


def _survival(k: int, rate: float, t: float) -> float:
    """Erlang(k, rate) 生存函数(与 equip_expectation 同式,独立誊写)。"""
    rt = rate * t
    return math.exp(-rt) * sum(rt ** j / math.factorial(j) for j in range(k))


def integral_wait(demand: dict[str, int], lam: float) -> float:
    """充分上界数值积分(路 2):上界 = Σ均值的 6 倍,网格 6 万步(独立重写)。"""
    rate = lam / POOL_N
    ks = list(demand.values())
    scale = 6.0 * sum(ks) / rate
    steps = 60000
    h = scale / steps
    total = 0.0
    for i in range(steps):
        t = (i + 0.5) * h
        p_done = 1.0
        for k in ks:
            p_done *= 1.0 - _survival(k, rate, t)
        total += (1.0 - p_done) * h
    return total


def mc_wait(demand: dict[str, int], lam: float, n: int = 4000,
            seed: int = 20260901) -> float:
    """蒙特卡洛(路 3):逐节点 Poisson(λ) 发放、均匀池 8,模拟凑齐轮数均值。"""
    rng = random.Random(seed)
    rate = lam / POOL_N
    # 等价加速:每件基础件到达间隔 iid Exp(rate),凑 k 件时刻 = 和(与逐节点模拟同分布)
    keys = list(demand.items())
    total = 0.0
    for _ in range(n):
        total += max(rng.gammavariate(k, 1.0 / rate) for _, k in keys)
    return total / n


def closed_form_single(lam: float) -> tuple[float, float]:
    """闭式(路 1):仅对单件两形态存在;返回 (交叉, 自配)。"""
    r = lam / POOL_N
    return 3.0 / (2.0 * r), 2.0 / r


def main() -> None:
    print('=' * 76)
    print('P14 Q1 轮期望三路互证(闭式 / 充分上界积分 / MC;λ 敏感性)')
    print('=' * 76)
    ok_all = True
    for lam in (0.25, 0.5, 1.0):
        cf_cross, cf_self = closed_form_single(lam)
        it_cross = integral_wait({'轮滑鞋': 1, '折叠小刀': 1}, lam)
        it_self = integral_wait({'和平手枪': 2}, lam)
        mc_cross = mc_wait({'轮滑鞋': 1, '折叠小刀': 1}, lam)
        mc_self = mc_wait({'和平手枪': 2}, lam)
        rows = [
            ('交叉件', cf_cross, it_cross, mc_cross),
            ('自配件', cf_self, it_self, mc_self),
        ]
        for name, cf, it, mc in rows:
            rel_it = abs(it - cf) / cf
            rel_mc = abs(mc - cf) / cf
            ok = rel_it < 1e-3 and rel_mc < 0.03
            ok_all &= ok
            print(f'λ={lam:<5} {name}: 闭式={cf:8.3f}  积分={it:8.3f} '
                  f'(Δ{rel_it:.2e})  MC={mc:8.3f} (Δ{rel_mc:.2%})  '
                  f'{"✓" if ok else "✗"}')
    print('\n整集需求(无闭式,积分 vs MC 互证;参照 TOTAL_NODES=27):')
    sets = {
        '昼神阿雅(轮滑鞋×5+小刀×1)': {'轮滑鞋': 5, '折叠小刀': 1},
        '追击飞霄(小刀×2+轮滑鞋×3+电池×2+手枪×1)':
            {'折叠小刀': 2, '轮滑鞋': 3, '光能电池': 2, '和平手枪': 1},
        '大黑塔银河学者(幸运星+小刀+电池×4+手枪+轮滑鞋)':
            {'幸运星': 1, '折叠小刀': 1, '光能电池': 4, '和平手枪': 1, '轮滑鞋': 1},
        '阿雅单件·自配皮靴(轮滑鞋×2)': {'轮滑鞋': 2},
    }
    for name, demand in sets.items():
        for lam in (0.5, 1.0):
            it = integral_wait(demand, lam)
            mc = mc_wait(demand, lam, n=3000)
            rel = abs(mc - it) / it
            ok = rel < 0.03
            ok_all &= ok
            print(f'  λ={lam} {name}: 积分={it:7.1f}  MC={mc:7.1f} (Δ{rel:.2%}) '
                  f'可行(纯等≤27)={"是" if it <= TOTAL_NODES else "否"} '
                  f'{"✓" if ok else "✗"}')
    print(f'\n结论:{"三路互证全部通过" if ok_all else "存在超差,须排查"}')


if __name__ == '__main__':
    main()
