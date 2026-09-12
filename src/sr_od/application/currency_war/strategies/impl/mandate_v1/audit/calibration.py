"""值因子标定注入单一源(T-278 标定批,ADR-0639;r1 返工修订)。

推导正本 = ``.debug/temp/currency_war/T-278-标定设计.md``(批内产物,
设计稿 = 检查点交付物,r1 已同步)+ ADR-0639(含修订记录);数值全部
注册表/在库档案派生(数学先行禁拍死),复现载体 =
``tools/cw/proofs/p76_e2_band_check.py``(ε₂ 全域包络确定性重算 + Δ
三因子打印)。

生产注入位 = ``MandateV1Strategy.__init__`` → :func:`apply`(幂等:
只填 None 槽不覆写;测试经 ``provisional.reset`` 清场隔离)。

消费条件申报(01_math_framework §6.2 三要素 2):本批注入 = 门数值
可评前置布防;**CI 两端扫描下门判定方向不变**的验证归 o_plus/d_death
装配批(首个能算 θ̂ 的批)义务——翻转 = P51 B3 在册 A/B 路径补数据,
门维持封印,不进权威面。V_MS 槽位**本批不注入**(其清偿 = P84 在册
复观测排期,辖换线出口面,不因本批提前;同源单标定禁双源:后续
V_ms 消费位必须引本模块 Δ 模型,禁第二标定)。
"""
from __future__ import annotations

from sr_od.application.currency_war.strategies.impl.mandate_v1.audit import (
    provisional,
)

#: Δ = V_C−V_F(P76 §7 #1 锁线夹界完成溢价;金量纲)。
#: 推导链(模型 = Δλ对比 × E × W,P76 D 项 Δλ·(g+Φ) 同形在代表视界
#: 上的积分;λ 对比按 P51 §4-B-2 分层读法③「按节点类型分槽」取
#: **同节点(battle)对比**,不用混合桶级值):
#: Δλ对比 = 0.341 − 0.065 = **0.276**(P51 §4-B-2 分层表 p8-12×battle
#: 与 p≤7×battle 的 3 轮累积危险率,均带 CI;观察性对比,桶级存活者
#: 组成混杂见 P51 §4-B 读法③与 B3——桶间对比用途 ≠ 桶内节点代表值);
#: E = 221.7 金 = pooled p≤7 财富敞口(g 74.4 + Φ 147.3,P52 对账 1
#: 同源);W = 2 窗(代表视界 6 轮)。⇒ 点值 0.276×221.7×2 = 122.4 →
#: **122 金**。
#: CI [0, 260]:下端 = P51 B3「Δλ 本数据集不可识别,因果化需 A/B」
#: 诚实下界(丁.4 域 floor;A/B 因果化 = 收窄唯一合法通道);上端 =
#: λ3 上包络 0.391 = **P51 §4-B-2 pooled 分层表最高 95%CI 上端**
#: (p8-12×battle 行;该表观测点值最大 0.341,本格取 CI 上端系保守
#: 选择;cw3 侧明细 p13+ 混合 0.524 / p13+×battle CI 上端 1.000 更高
#: 但小样本,按「pooled 分层表口径」排除并在此申报)
#: × 221.7 × 3 窗(9 轮视界上包络)。
DELTA_V_C_MINUS_V_F = provisional.CalibValue(
    value=122.0, ci_lo=0.0, ci_hi=260.0)

#: ε₂ 集中度二阶带(P76 §3.4/§4.4 夹界余量;概率量纲,只抬 θ̂_suff
#: 保守侧)。构造 = 两反向通道在**全生产消费域**网格(m∈{1..6}
#: = 注册表 form_tiers needs 全集;L∈{1..10};T=r_remaining∈{1..27}
#: = 日程全长 (9,9,9);R∈{0..60 步 2};全注册表 25 标签域)的包络:
#: 通道①池衰减增富(侧线支出 ≤2R 金买主费档非目标 → t_c 加深)
#: 全域 max **+12.39pp**;通道②收入流差(败金差 ≤+2 金/战,P76
#: §3.4/P51 B1 量级 × T 战 → +SHOP_SLOTS·T 试验)全域 max
#: **+64.29pp**(角点 L1/仙舟/m6/T4/R0:R=0 预算饿死域一阶支配优势
#: 消失,二阶通道全量显影——P76 丙.4 弱支配域的如实取全量)。
#: 逐格和取最大 = 包络 0.6429 → 进位取安全端 **0.65**。复现 =
#: p76_e2_band_check.py(确定性,断言包络 ≤ 注入值;域外帧经
#: :func:`band_in_domain` fail-closed,不消费带值)。
E2_CONCENTRATION_BAND = provisional.CalibValue(value=0.65)

# —— ε₂ 标定网格域(r1 返工:带外 fail-closed,与值一体申报)——
#: 强制辖域只辖**注册表有界维**:needs 上界与日程上界(两者漂移 =
#: 注册表事件,域外帧 fail-closed 归 unavailable[e2_domain],绝不向
#: 夹界渗漏欠覆盖的 θ̂_suff;P76 丙.4「带外不声明」的落码形态)。
#: R(付费刷数)维生产无界(gold 无硬帽 ⇒ 递推 R 随溢余增长),不作
#: 强制辖域——其覆盖由数值验证承载:全 R 轴(R≤1200,峰宽自适应
#: 网格)重算包络恒 0.6429(argmax R=0;大 R 双臂概率饱和、带差趋零,
#: 小 q 长尾峰 ≤0.3),脚本第二断言在案。
E2_DOMAIN_M_MAX = 6            #: 注册表 form_tiers needs 全集上界(巡海击破 6)
E2_DOMAIN_R_REMAIN_MAX = 27    #: r_remaining 生产上界 = 日程全长 (9,9,9)


def band_in_domain(max_missing: int, r_remaining: int) -> bool:
    """ε₂ 带值辖域检查(装配端消费;注册表有界维任一出格 = False)。

    ``max_missing`` = 缺口分解最大单件张数(production = needs 上界);
    ``r_remaining`` = 视界(装配帧现算)。L 维全覆盖(level 1-10 全
    网格)、R 维全轴覆盖(数值验证见模块注)均无检查项。
    """
    return (max_missing <= E2_DOMAIN_M_MAX
            and r_remaining <= E2_DOMAIN_R_REMAIN_MAX)


def apply() -> None:
    """幂等注入(唯一写入口经 ``provisional.inject``;只填 None 槽,
    不覆写既有值——sim A/B 重注入等场景优先级高于本模块缺省)。"""
    if provisional.get('V_C_MINUS_V_F') is None:
        provisional.inject('V_C_MINUS_V_F', DELTA_V_C_MINUS_V_F)
    if provisional.get('E2_CONCENTRATION_BAND') is None:
        provisional.inject('E2_CONCENTRATION_BAND', E2_CONCENTRATION_BAND)
