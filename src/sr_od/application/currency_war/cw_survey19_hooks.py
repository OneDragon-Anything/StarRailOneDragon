"""二轮扫描落地件(strategy/19 剩余项):P9 遭遇接难度账本 + P1 狼狩穿戴纪律 + P8 补给重刷判据。

三件均为纯函数决策件(离线可测);执行侧接线(equip_all/run_supply_node/handle_encounter)
走消费批次。用户修正裁定:
- P1:装备是**可循环资源**(卖出回收/扳手拆)——不为狼狩牺牲合成规划;纪律只有一条:
  别让装备躺在物品栏(穿了才产经验,物品栏 0 经验);
- P8:补给重刷 = 免费重采样权,「未出钻 → 刷」;
- P9:难度增减的场合依赖(大胜 0/边际峰值/无解 0)进遭遇档位选择。
"""
from __future__ import annotations

from sr_od.application.currency_war.cw_difficulty_account import marginal_value


def encounter_tier_score(d_now: float, tier_delta: int, gap: float,
                         plane: int) -> float:
    """P9:遭遇节点难度档评分 = marginal_value 包装(36 号账本三态+P1 尖峰+地板/溢出守卫)。

    档位候选各算一次,取最高;负 delta(压难度)在边际局(P1 尤甚)得高分——
    替代 08 号线性归一的局部选择。
    """
    return marginal_value(d_now, float(tier_delta), gap, plane=plane)


def wear_discipline_alert(inventory_equips: list[str],
                          total_slots: int,
                          worn_count: int,
                          faction_hunt_active: bool) -> dict:
    """P1:狼狩穿戴纪律(用户修正版:装备可循环,唯一纪律 = 别积压)。

    - 非狼狩局:仅报积压(战力视角,穿了总比躺着强);
    - 狼狩局:积压量化为步离人经验损失(每件每战 +1 经验,进阶算 2);
    - 合成规划不受影响(key_equips 优先序照旧)——拆装重组的间隙最小化即可。
    """
    idle = max(0, len(inventory_equips))
    free_slots = max(0, total_slots - worn_count)
    overflow = max(0, idle - free_slots)   # 无空槽可穿的部分才是真积压
    xp_loss_per_battle = overflow if faction_hunt_active else 0
    return {'idle_equips': idle, 'free_slots': free_slots,
            'unwearable_overflow': overflow,
            'hunt_xp_loss_per_battle': xp_loss_per_battle,
            'alert': overflow > 0,
            'note': '狼狩:物品栏件 0 经验,穿着每战 +1(进阶+2);拆装重组间隙最小化'}


def supply_reroll_decision(any_option_has_diamond: bool,
                           reroll_used: bool) -> str:
    """P8:补给重刷判据(免费重采样权)。

    出钻 → 选;未出钻且可刷 → 刷(重掷钻概率);刷过仍无 → 按价值正常选。
    """
    if any_option_has_diamond:
        return 'pick_diamond'
    if not reroll_used:
        return 'reroll'
    return 'pick_best'
