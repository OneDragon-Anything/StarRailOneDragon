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


# ===== r356(策略架构反思 B):P1 阶段目标形态检查点 =====
# 局38-44 七败的结构性判读:决策系统对「成型进度」无感知、对
# 「成型 deadline」无响应——各局在不同 seed 下投影出不同表层
# 卡点(七局七根因=发散信号)。本表 = 缺失的控制变量。
# 口径:V4.0 过渡框架(transitions.md §1)+ 用户节奏(user_playstyle
# [2][12][13]):r3 桥雏形 / r6 配方 5 档 / r8 成型锁方向。
_P1_FORMATION_TARGETS: dict[str, int] = {
    'bridge2': 2,    # r1-r3:桥方向 ≥2 阵营各 ≥2 档
    'recipe5': 5,    # r4-r6:配方线 recipe_tier ≥5(RECIPE_BASE)
    'recipe7': 7,    # r7-r8:配方 7 档+方向锁定(boss 前形态)
}
#: 各 deadline 的轮界(含);r9=boss 决战窗不适用检查点
_P1_FORMATION_ROUND_EDGES: tuple[int, int, int] = (3, 6, 8)


def p1_formation_target(round_num: int,
                        board: dict[str, int]) -> tuple[str, int, int]:
    """P1 成型进度检查(r356)→ (阶段键, 目标档, 当前档)。

    阶段判据(V4.0 过渡节奏):
    - r≤3(bridge2):桥雏形 = 板面引擎阵营中 ≥2 档的阵营数 ≥2;
      当前档 = 达标阵营数(目标 2);
    - r≤6(recipe5):recipe_tier(board) ≥ RECIPE_BASE;
    - r≤8(recipe7):recipe_tier ≥ 7(渐进 +2 列车/护盾);
    - r9+:返 ('boss', 0, 0)(决战窗,检查点不适用)。
    消费方(formation_push):gap>0 → 当轮全预算补差。
    """
    if round_num <= _P1_FORMATION_ROUND_EDGES[0]:
        cur = sum(1 for f, c in board.items()
                  if c >= 2 and f in ENGINE_FACTIONS)
        return 'bridge2', _P1_FORMATION_TARGETS['bridge2'], cur
    if round_num <= _P1_FORMATION_ROUND_EDGES[1]:
        return 'recipe5', _P1_FORMATION_TARGETS['recipe5'], \
            recipe_tier(board)
    if round_num <= _P1_FORMATION_ROUND_EDGES[2]:
        return 'recipe7', _P1_FORMATION_TARGETS['recipe7'], \
            recipe_tier(board)
    return 'boss', 0, 0
