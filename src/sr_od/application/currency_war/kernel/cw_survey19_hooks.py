"""二轮扫描落地件:P1 狼狩穿戴纪律(单件模块)。

纯函数决策件(离线可测);执行侧接线(equip_all)由调用方接入。用户修正
裁定:装备是**可循环资源**(卖出回收/扳手拆)——不为狼狩牺牲合成规划;
纪律只有一条:别让装备躺在物品栏(穿了才产经验,物品栏 0 经验)。

(补给重刷判据不在本模块:单一源 = 策略层
``strategies/impl/mandate_v1/supply.py``。)
"""
from __future__ import annotations


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
