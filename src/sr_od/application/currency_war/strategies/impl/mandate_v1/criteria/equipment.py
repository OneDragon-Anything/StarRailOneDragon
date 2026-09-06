"""criteria/equipment——装备面(§2.6;M7 基础穿戴义务在 mandate)。

修复池落点:D-B(非 key_equips 穿戴释放三态门 ``wear_release``——
不再用无边界 opening 布尔拦穿)、D-P3(收尾段终局投资语境输入)。
D-F46(词缀条件装备分配)的生产单一源 =
``cw_equip_env.resolve_affix_priority_order``(cw_op_equip_all 消费);
本模块原 ``affix_allocation`` 系其孤儿第二实现且键 'weakness' 死键,
已随判据出处纠错批删除(墓碑见 criteria/__init__.py BYPASS_TABLE 行)。
"""
from __future__ import annotations


def wear_release(opening_achieved: bool, node_type: str | None,
                 simple_item: bool) -> tuple[bool, str]:
    """D-B 穿戴释放三态门(替代无边界 opening 布尔)。

    ①简易件(simple_item:分层规则即穿,零门槛)⇒ 放行;
    ②进阶成品:首引擎/过渡里程碑达成(opening_achieved)⇒ 收窄后
      放行(「攒给成型核心」窗口显式释放);
    ③强敌节点释放:node_type ∈ {encounter, boss} ⇒ 放行
      (进阶成品上场通道,D-D 共根组 2 词缀/威胁语境维度)。
    三态全不放行 = 旧「整局不穿 11-13 件积压到死」病灶(181254-B)。
    """
    if simple_item:
        return True, 'simple_item'
    if opening_achieved:
        return True, 'opening_achieved'
    if node_type in ('encounter', 'boss'):
        return True, 'hard_node'
    return False, 'saving_for_core'


def keep_policy(redemption_distance: int) -> tuple[bool, str]:
    """§2.6 keep_policy:近兑现距离 d*≤1 绝不喂(P42 ③ 零参数公理)。"""
    if redemption_distance <= 1:
        return False, 'near_redemption'
    return True, ''


def endgame_context(r_remaining: int) -> str:
    """D-P3 收尾段语境(r7-r9 终局投资:星级/等级转向)。"""
    return 'endgame' if r_remaining <= 3 else 'midgame'
