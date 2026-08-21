"""货币战争 过渡配方/引擎阵营 常量单一源(r271 统一)。

两份子代理审查(2026-08-23)共同点名的头号双源:
- 配方四阵营(仙舟/持续伤害/列车同行/护盾)在 line_strategy
  是函数局部 set(r268 刷门/r263b 判据 ×3 处),deploy_bench 是
  模块 frozenset(r263b 纪律);配方基础档一边具名(_RECIPE_BASE=5)
  一边字面;
- 引擎三阵营(_ENGINE_FACTIONS)手抄两份且可从 BRIDGE_POOL 派生。

本模块 = 单一源;消费方一律 import,不再本地定义。
口径源:docs/game/currency_war/research/user_playstyle.md [20]
(过渡配方:3仙舟+2DOT 基础 → +2列车2护盾 渐进)。
"""
from __future__ import annotations

from sr_od.application.currency_war.cw_bridge_pool import (
    BRIDGE_POOL,
)

# 过渡配方阵营(基础 3仙舟+2DOT + 渐进 列车/护盾;攻略[20])
RECIPE_FACTIONS: frozenset[str] = frozenset(
    {'仙舟', '持续伤害', '列车同行', '护盾'})
# 配方基础线:3 仙舟 + 2 DOT = 5 档(基础未满时散件不上板/找件刷)
RECIPE_BASE: int = 5
# 引擎阵营(从桥池派生:三大桥的 engine_bonds 键并集;含 DOT flow)
ENGINE_FACTIONS: frozenset[str] = frozenset(
    bond for combo in BRIDGE_POOL for bond in combo.engine_bonds)


def recipe_tier(board: dict[str, int]) -> int:
    """板面的配方档数(board 里 ∈ RECIPE_FACTIONS 的档位和)。"""
    return sum(v for k, v in board.items() if k in RECIPE_FACTIONS)


def recipe_kinds_1cost() -> int:
    """1 费配方件的种类数(找件刷概率用;r269b 第三处手搓的收口)。"""
    from sr_od.application.currency_war.cw_chars import CHARACTERS
    return sum(1 for n, ch in CHARACTERS.items()
               if ch.cost == 1 and (ch.factions or [''])[0]
               in RECIPE_FACTIONS)
