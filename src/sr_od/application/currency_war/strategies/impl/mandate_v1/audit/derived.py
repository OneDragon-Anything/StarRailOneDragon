"""【推】推导量计算器注册表(01_math_framework §6 第 2 形态;原 design_economy
§E4.0 第 2 条已删档,取回口径=ADR-0644)。

登记全部【推】项的入口函数与依赖注册表清单——审计时按此表核对
「数值随注册表重算,无自由参数」(NMF §3.2)。**子形态【推·语料拟合】**
(R29-6):系数系对实机语料回归、残差中位 0 的拟合量(随语料分布漂移),
非「可从注册表重算的推导量」——审计不得按机制推导量放行,须按
「系数随 P51_V3_REBUILD §2 重算物版本重算 + 漂移哨兵(对账持续偏差)
在线监督」口径单独核;单列禁与机制推导量混列放行。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable


@dataclass(frozen=True)
class DerivedEntry:
    """【推】项登记:入口函数 + 依赖注册表清单 + 子形态标记。"""

    name: str
    entry: str                    # 模块.函数(符号索引,懒解析防 import 环)
    registry_deps: tuple[str, ...]
    subtag: str = ''              # '语料拟合' = 【推·语料拟合】(R29-6)


#: 登记表(审计单一源;数值实现本体在 statefn 各模块)
ENTRIES: tuple[DerivedEntry, ...] = (
    DerivedEntry(
        'L_loss_exact', 'statefn.interest.loss_exact',
        ('cw_plane_table.GOLD_CAP_INTEREST',),
        # P47 双轨迹递推;cap 按 resolved 参数化(P47 修复批)
    ),
    DerivedEntry(
        'E_refreshes', 'statefn.odds.expected_refreshes',
        ('cw_shop_odds.REFRESH_PROB', 'cw_shop_odds.POOL_COPIES_PER_CARD',
         'cw_shop_odds.DISTINCT_CARDS_PER_COST'),
        # 超几何 DP(P49 命题 1:E 全走 taken 参数精确 DP)
    ),
    DerivedEntry(
        'p_bar_exact', 'statefn.odds.p_bar_exact',
        ('cw_shop_odds.REFRESH_PROB', 'cw_shop_odds.POOL_COPIES_PER_CARD',
         'cw_shop_odds.DISTINCT_CARDS_PER_COST',
         'cw_chars.CHARACTERS'),
        # 多项×超几何精确式(P16 修复批;旧 union bound 高估 +8.1% 已勘误)
    ),
    DerivedEntry(
        'v_comp_table', 'statefn.vopt.v_comp_table',
        ('cw_shop_odds.expected_refreshes', 'cw_shop_odds.refresh_prob'),
        # P49 ①② 压缩表;线性律在非目标池近耗尽处失效,带外禁外推
    ),
    DerivedEntry(
        'delta_v_streak', 'statefn.vopt.delta_v_streak',
        ('cw_economy.STREAK_GOLD_TABLE', 'cw_economy.LOSS_GOLD_BY_NODE'),
        # P43 引擎口径 DP 两次求值相减
    ),
    DerivedEntry(
        'floor_eff', 'statefn.lambda_death.floor_eff',
        ('statefn.interest.interest_cap_resolved',),
        # arm2 结构守息门 10×cap_resolved(R8-4;0.1 投影已退役 R26-H1)
    ),
    DerivedEntry(
        'delta_interest_flow', 'statefn.horizon.delta_interest_flow',
        ('statefn.interest.INTEREST_CAP_SUP',
         'audit.proof_consts.LAMBDA3_WINDOW'),
        # Δ息流̂ 生产式(R9-3 上界形态;cap_sup 口径 R63-1)
    ),
    DerivedEntry(
        'r_global', 'statefn.horizon.r_global',
        ('cw_plane_table.schedule_of', 'cw_plane_table.PLANE_FALLBACK_PRIORS'),
        # R_全局(L-R3-2:长度唯一真值源=schedule_of,禁新建长度常量 §6.1)
    ),
    DerivedEntry(
        'difficulty_interim', 'statefn.lambda_death.difficulty_band',
        ('cw_investments.INVESTMENT_STRATEGIES',),
        # 【登记对齐,IMPL_ADV_R200 OBS-4】interim 兜底公式(难度=108基础
        # +品质加成[银0/金3/棱彩6,远见豁免]+遭遇等级[缺位置0]+特殊[伟大
        # 征服+当前连胜],P51_V3_REBUILD §2)**未落码**——现行实现
        # difficulty_band 仅承载「真值优先」半边(局内旗牌读取真值→分带;
        # 缺读 None 直返 None 落域外,不产 interim 假真值,与函数 docstring
        # 一致)。落码归属=λ 表重建批(公式需品质/遭遇/特殊三分量的
        # 可观测载体,现观察面未载);subtag 维持「语料拟合」——系数
        # 归宿不变(§2 重算物),落码后按同 subtag 单独核。
        subtag='语料拟合',
    ),
)


def entry_points() -> dict[str, Callable[..., object]]:
    """懒解析全部入口函数(审计钩子;import 失败即报=登记漂移信号)。"""
    import importlib
    pkg = 'sr_od.application.currency_war.strategies.impl.mandate_v1.'
    out: dict[str, Callable[..., object]] = {}
    for e in ENTRIES:
        mod_name, func_name = e.entry.rsplit('.', 1)
        mod = importlib.import_module(pkg + mod_name)
        out[e.name] = getattr(mod, func_name)
    return out


def subtag_of(name: str) -> str:
    """子形态查询('' = 机制推导量;'语料拟合' = 【推·语料拟合】)。"""
    for e in ENTRIES:
        if e.name == name:
            return e.subtag
    raise KeyError(f'unknown derived entry: {name}')


__all__ = ['ENTRIES', 'DerivedEntry', 'entry_points', 'subtag_of']
