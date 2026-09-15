"""sim 重做·特殊角色规则(M21)。

设计正本 = ``docs/develop/sr_od/application/currency_war/changes/
2026-09-15-sim-redesign/design.md`` §2.2 M21、U26 第一期定稿口径:

- **银狼LV.999**(注册表单条目 ``data/cw_chars.py``,起始 3 费):
  升费口径 = 2星→4费、3星(5费线)→5费(U26 定稿口径,标注读数候
  实机核对);**备战栏不升费**(拖上场才变费,gameplay「角色升星」
  节)——有效费用 = 星级 × 上场态双输入;升费前商店只出基础费用档
  = 池过滤器语义(注册表仅 3 费条目,4/5 费档不作为独立卡名存在,
  池面天然只出 3 费档——无需额外过滤器,注册表现状即口径);
- 「我来当策划」二选一 overlay(升费 vs 其他)= 银狼首次升 2 星触发
  (有档触发,gameplay「角色升星」节)→ M22 planner 族(U14 已裁决
  纳入);引擎升星钩子在合成腿后消费触发判据,「首次」语义由引擎
  一次性标志承载;
- **开拓者双形态**:前台=记忆/后台=欢愉,位置决定生效——kernel
  ``cw_chars.trailblazer_form`` 单一源(部署腿按目标排形态归一已在
  kernel 转移函数内,sim 侧只供查询口与测试锚);
- 三星五费特效(≈无敌)= M13 战力特征,第一期随机输出面下无消费,
  挂披露;
- 试用角色 = 账号未拥有、面板中等(``research/equipment_mechanics.md``
  §7)——与自有同池同计数(U11),sim 无账号概念,无差异建模。

随机量与流键:无(全部确定性规则;「我来当策划」选项生成归 M22
``M21/planner``→``M22/planner`` 流)。
"""
from __future__ import annotations

from sr_od.application.currency_war.data.cw_chars import (
    is_trailblazer,
    trailblazer_form,
)

#: 银狼LV.999 注册表规范名(单一源 = ``data/cw_chars.py``;名字含
#: 「LV.999」后缀,与普通「银狼」4 费条目是两个角色)。
SILVER_WOLF_ID: str = '银狼LV.999'

#: 银狼升费口径表(U26:星级 → 有效费用;3星(5费线)→5费)。
SILVER_WOLF_COST_BY_STAR: dict[int, int] = {1: 3, 2: 4, 3: 5}

#: 三星五费特效披露键(M13 战力特征,第一期无消费面)。
THREE_STAR_FIVE_COST_PENDING: str = 'three_star_five_cost_effect_pending_u26'


def silver_wolf_effective_cost(char_id: str, star: int, *,
                               on_front: bool) -> int | None:
    """银狼有效费用(U26 口径;非银狼 → None 非本辖域)。

    - 上场态(on_front=True):星级查表 1→3 / 2→4 / 3→5(升星拖上场
      变费);
    - 备战态:恒基础 3 费(备战栏不升费,gameplay「角色升星」节);
      星级超表(非法态)按基础费保守回落。
    """
    if char_id != SILVER_WOLF_ID:
        return None
    if not on_front:
        return SILVER_WOLF_COST_BY_STAR[1]
    return SILVER_WOLF_COST_BY_STAR.get(max(1, min(3, int(star))), 3)


def planner_overlay_due(char_id: str, star_before: int,
                        star_after: int) -> bool:
    """「我来当策划」触发判据(引擎合成腿后消费):银狼升达 2 星的
    合成事件(首次语义 = 引擎一次性标志,本判据只答「该次合成触发
    吗」;重复升 2 星事件由调用方以 fired 位去重)。"""
    return (char_id == SILVER_WOLF_ID
            and int(star_before) < 2 <= int(star_after))


def trailblazer_form_of(char_id: str, row: str) -> str:
    """开拓者按排形态名(kernel 单一源引用口;非开拓者原样返回)。

    ``row`` 坐标系 = 'front'|'back'(kernel 同名参数同域);部署腿的
    形态归一已在 kernel 转移函数内,本口仅供 sim 侧查询/测试对账。
    """
    if not is_trailblazer(char_id):
        return char_id
    return trailblazer_form(char_id, row)
