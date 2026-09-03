"""L(g,d,R,Ī) 息档损失递推(P47 规范解;税基单一源)。

NMF §2 「L(息档损失)」的唯一实现:双轨迹递推(基线守 50 溢余即花 vs 花后
守 50),**cap 按 resolved 参数化**(P47 修复批:默认 5 / 息律投资 10 /
开源节流 9 / 买断制 0——值经 cw_investments 的 interest_cap_override 语境
解析,不在本模块散落)。对拍锚 = ``tools/cw/proofs/p47_check.py`` 的
``loss_exact``(全档位网格,§5.3 对拍「P47 L 递推」行);税基单一源纪律 =
P47 息账与 P51 存量清零账互不包含(NMF §6 第 4 条)。
"""
from __future__ import annotations

from sr_od.application.currency_war.kernel.cw_plane_table import (
    GOLD_CAP_INTEREST,
)

#: 默认息帽档数 = 息封顶金位/10(cw_plane_table.GOLD_CAP_INTEREST=50 的
#: 结构派生,【注】机制真值;禁在本模块另写裸 5)
DEFAULT_INTEREST_CAP: int = GOLD_CAP_INTEREST // 10

#: cap 视界上确界(注册表 interest_cap 值域上界 10;R61-1/R62-3 上界陈述形态:
#: kernel 覆写下调通道只减真值收入 ⇒ 上界单调保持)。Δ息流̂ 生产式与
#: C_int/C_stay 等 cap 消费位按 canonical 枚举表(design_economy §E4.2)
#: 一律消费 cap_sup 而非决策帧现值 cap_resolved(R63-1)。
INTEREST_CAP_SUP: int = 10


def interest(gold: int, cap: int = DEFAULT_INTEREST_CAP) -> int:
    """利息 = min(g//10, cap);g<0 按 0 计(防负金越界,p47 A1 同源)。"""
    return min(max(gold, 0) // 10, cap)


def interest_cap_resolved(interest_cap_override: int | None = None) -> int:
    """resolved 息帽(语境修正开关单一源 = cw_investments.STRATEGY_ECONOMY
    overlay 登记 + MechanismMutation 运行时突变视图,NMF §2 末行)。

    override=None(默认局/无突变)→ DEFAULT_INTEREST_CAP;买断制 0/息律 10/
    开源节流 9 由调用方传注册表 override 值——本函数只做「无突变回默认」的
    单点归一,禁在判据侧内联 cap 字面量(E4.0 第 1 条)。
    """
    if interest_cap_override is None:
        return DEFAULT_INTEREST_CAP
    return max(0, int(interest_cap_override))


def saturation_line(cap_resolved: int) -> int:
    """息律饱和线 g* = 10×cap_resolved(守息门/arm2 金下限同源派生;
    与 lambda_death.floor_eff 同式——floor_eff 的命名落位在 §1 lambda_death
    行,本函数是息侧同源命名,值恒等)。"""
    return 10 * cap_resolved


def loss_exact(gold: int, spend: int, rounds: int, net_income: int,
               cap: int = DEFAULT_INTEREST_CAP) -> int:
    """金位 gold 花 spend 金后未来 rounds 轮的精确期望息损(P47 命题 2)。

    双轨迹对照:基线 B(不花,守饱和线,溢余即花)vs A(花后守线);每轮息损
    = interest(B) − interest(A),两轨迹同收入演化。截断视界 R=rounds 由
    horizon 层供给(schedule_of 实际长度,禁写死,§6.1)。
    """
    gold_cap = 10 * cap
    g0 = max(gold, 0)
    b = min(g0, gold_cap)
    # A 轨迹起点=实金扣(对齐锚 p47_check L51-52:先扣 spend 再谈守线)。
    # 溢金域(gold>10×cap)下「先截断再扣」会把溢余重复花掉——A 轨迹起点
    # 低估→息损高估→花费决策保守偏;实金扣后溢余只在轨迹演化中按守线
    # 截断消费一次(IMPL_ADV_R194 症2 修复)。gold<0 钳 0 与锚同值(锚域 g>=0)。
    a = max(g0 - spend, 0)
    total = 0
    for _ in range(rounds):
        ib, ia = interest(b, cap), interest(a, cap)
        total += ib - ia
        b = min(b + net_income + ib, gold_cap)
        a = min(a + net_income + ia, gold_cap)
    return total


__all__ = [
    'DEFAULT_INTEREST_CAP', 'INTEREST_CAP_SUP', 'interest',
    'interest_cap_resolved', 'loss_exact', 'saturation_line',
]
