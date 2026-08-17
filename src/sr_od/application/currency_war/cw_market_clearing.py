"""市场清算所 v0(redesign 43 号;ADR-0189):tâtonnement 迭代撮合 + 套利预算度量。

**诊断(43 号)**:15 个影子模块一遍瀑布级联(上游输出当下游常数,缝上价格各算各的)——
权威自 DP 的错价只能事后审计(35),不能被结构性否决;组合次优无度量。

**v0 落地**(纯函数,离线;43 号 §2 的最小闭环):
- ``Trader``:报价适配接口(net_demand(π) → 资源净超额需求;注入式——生产接 03/06/38/07/
  21/08/18 各模块的局部解,测试/mock 与 A1+cap 现状代理);
- ``clear``:π₀ ← DP 差分(35 提取器)→ 循环 {各交易者按 π 解局部问题报净需求 z;
  π ← π + η·z(阻尼+投影)}→ 停机:max|z|<ε / 迭代预算 B / 振荡检测 → 返回终价 π*、
  各交易者局部解(协调后决策)、价格路径;
- ``arbitrage_budget``:各资源模块间边际估值全距(J1 语义:瀑布级联相对联合优化的损失
  上界 + 市场存在性判据——全带内 → 市场无存在必要,自我证伪条款);
- 降级链:B=0 → 精确 π₀ 单轮(=现状级联的零漂移锚);不收敛 → 取最优迭代点;振荡 →
  报告(13 号「清算震荡」合约族候选)。

J3 韧性注入(测试):π₀ 故意错(模拟 DP 常数错)→ 清算收敛价显著更稳(交易者否决坏价)。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


class Trader(Protocol):
    """交易者接口:按价向量解局部问题,报资源净超额需求(>0 想多要,<0 想卖出)。"""

    name: str

    def net_demand(self, prices: dict[str, float]) -> dict[str, float]: ...


@dataclass
class ClearingResult:
    """清算输出:终价 + 各交易者局部解 + 路径 + 诊断。"""

    prices: dict[str, float]
    net_demands: dict[str, dict[str, float]]   # 交易者名 → 终价下的净需求(协调后解)
    path: list[dict[str, float]] = field(default_factory=list)
    iterations: int = 0
    converged: bool = False
    oscillated: bool = False


def clear(traders: list[Trader], pi0: dict[str, float], *,
          eta: float = 0.3, max_iter: int = 50, eps: float = 1e-3,
          floor: float = 0.01) -> ClearingResult:
    """tâtonnement:阻尼调价到净需求≈0(无套利)或预算耗尽。

    价格投影:非负下界 floor(资源价不为负;23 号证据区间作箱投影挂消费批次)。
    振荡检测:价格路径符号翻转 ≥3 次且幅度不衰 → oscillated(取最优点=残差最小)。
    """
    pi = dict(pi0)
    path: list[dict[str, float]] = [dict(pi)]
    best_pi, best_res = dict(pi), float('inf')
    flip_streak = 0
    prev_signs: dict[str, int] = {}
    converged = False
    it = 0
    for it in range(1, max_iter + 1):   # noqa: B007  it 计数进 ClearingResult
        z_total: dict[str, float] = {}
        for tr in traders:
            for k, z in tr.net_demand(pi).items():
                z_total[k] = z_total.get(k, 0.0) + z
        res = max(abs(v) for v in z_total.values()) if z_total else 0.0
        if res < best_res:
            best_res, best_pi = res, dict(pi)
        if res < eps:
            converged = True
            break
        # 振荡检测:净需求符号连续翻转
        signs = {k: (1 if v > 0 else (-1 if v < 0 else 0)) for k, v in z_total.items()}
        if prev_signs and all(
                prev_signs.get(k, 0) != 0 and s != 0 and s == -prev_signs[k]
                for k, s in signs.items() if s != 0) and signs:
            flip_streak += 1
        else:
            flip_streak = 0
        prev_signs = signs
        if flip_streak >= 3:
            break
        for k, z in z_total.items():
            pi[k] = max(floor, pi[k] + eta * z)
        path.append(dict(pi))
    finals = {tr.name: tr.net_demand(pi if converged else best_pi) for tr in traders}
    return ClearingResult(prices=pi if converged else best_pi, net_demands=finals,
                          path=path, iterations=it, converged=converged,
                          oscillated=flip_streak >= 3)


def arbitrage_budget(traders: list[Trader], pi: dict[str, float]) -> dict[str, float]:
    """套利预算(J1):各资源**未成交残差** |Σzᵢ(π)|(个体需求在均衡处非零——撮合成交
    供需相抵;残差才是级联损失的代理)。全资源 |z_total| < 带 → 市场无存在必要
    (自我证伪条款;阈值由消费端按噪声地板定)。"""
    z_total: dict[str, float] = {}
    for tr in traders:
        for k, z in tr.net_demand(pi).items():
            z_total[k] = z_total.get(k, 0.0) + z
    return {k: abs(v) for k, v in z_total.items()}
