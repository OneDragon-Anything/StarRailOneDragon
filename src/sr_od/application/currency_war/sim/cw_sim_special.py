"""sim 重做·特殊角色规则(M21)。

设计正本 = ``docs/develop/sr_od/application/currency_war/changes/
2026-09-15-sim-redesign/design.md`` §2.2 M21、U26 第一期定稿口径:

- **银狼LV.999**(注册表单条目 ``data/cw_chars.py``,起始 3 费):当前
  费用档 = 容器推演状态 ``gs.lv999_cost_tier``(读口唯一 =
  ``kernel.cw_economy.effective_cost``;写端 = pick_planner 升费腿 /
  deploy_move 上阵变费腿;2026-09-18 定谳:升费 = 变下一个费用档的
  1 星)。池桶归属(商店发牌/效果授予采样空间)经 ``kernel.cw_pool``
  档感知出口承接,本模块不再持有费用档派生口径;
- 「我来当策划」二选一 overlay(升费 vs 其他)= 银狼首次升 2 星触发
  (有档触发,gameplay「角色升星」节)→ M22 planner 族(U14 已裁决
  纳入);引擎升星钩子在合成腿后消费触发判据,「首次」语义由引擎
  一次性标志承载;
- **开拓者双形态**:前台=记忆/后台=欢愉,位置决定生效——kernel
  ``cw_chars.trailblazer_form`` 单一源(部署腿按目标排形态归一已在
  kernel 转移函数内,sim 侧只供查询口与测试锚);
- 三星五费特效(≈无敌)= M13 战力特征,第一期随机输出面下无消费,
  挂披露;
- 试用角色 = 账号未拥有、面板中等(``docs/game/gameplay/currency_war.md``
  「试用角色」行 :81)——与自有同池同计数,sim 无账号概念,无差异
  建模。

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

#: 三星五费特效披露键(M13 战力特征,第一期无消费面)。
THREE_STAR_FIVE_COST_PENDING: str = 'three_star_five_cost_effect_pending_u26'


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
