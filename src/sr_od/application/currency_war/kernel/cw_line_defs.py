"""货币战争 过渡配方/引擎阵营 常量单一源。

收敛曾经的头号双源:
- 配方四阵营(仙舟/持续伤害/列车同行/护盾)与配方基础档此前在
  line_strategy(已删)与 deploy_bench 两处各写一份;
- 引擎三阵营(_ENGINE_FACTIONS)手抄两份且可从 BRIDGE_POOL 派生。

本模块 = 单一源;消费方一律 import,不再本地定义。
口径源:已退役口述登记簿条目 [20](git 历史可溯)
(过渡配方:3仙舟+2DOT 基础 → +2列车2护盾 渐进)。
"""
from __future__ import annotations

from sr_od.application.currency_war.kernel.cw_bridge_pool import (
    BRIDGE_POOL,
)

# ⚠️ 迁移待办(docs/develop/currency_war/archive/redesign/03_legacy_cleanup_plan.md):
# 权威副本 = knowledge/cw_line_facts(RECIPE_FACTIONS/RECIPE_BASE);
# 本副本仅为 sim/旧判据未迁消费点保留,按该计划随文件删除;勿新增消费。
# 过渡配方阵营(基础 3仙舟+2DOT + 渐进 列车/护盾;攻略[20])
RECIPE_FACTIONS: frozenset[str] = frozenset(
    {'仙舟', '持续伤害', '列车同行', '护盾'})
# 配方基础线:3 仙舟 + 2 DOT = 5 档(基础未满时散件不上板/找件刷)
RECIPE_BASE: int = 5
# 引擎阵营(从桥池派生:三大桥的 engine_bonds 键并集;含 DOT flow)
ENGINE_FACTIONS: frozenset[str] = frozenset(
    bond for combo in BRIDGE_POOL for bond in combo.engine_bonds)

