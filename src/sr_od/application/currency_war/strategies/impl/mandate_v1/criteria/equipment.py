"""criteria/equipment——装备面(§2.6;M7 基础穿戴义务在 mandate)。

修复池落点:D-B(非 key_equips 穿戴释放三态门 ``wear_release``——
不再用无边界 opening 布尔拦穿)、D-F46(词缀条件装备分配
``affix_allocation``——「软弱无力」类敌词缀下主输出位优先凑满 3 件,
OPEN=sim 定谳)、D-P3(收尾段终局投资语境输入)。
"""
from __future__ import annotations

# 敌方词缀条件键(D-F46;词缀 id/名注册表随 data 批定谳,当前在册 =
# 复盘 195720-F「软弱无力:未满 3 件伤害 8 折」单例)
AFFIX_WEAKNESS: str = 'weakness'


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


def affix_allocation(enemy_affixes: list[str],
                     candidates: list[tuple[str, int]],
                     ) -> list[tuple[str, int]]:
    """D-F46 词缀条件装备分配排序(谓词,非发射)。

    ``candidates`` = [(单位名, 已穿件数)];出现 AFFIX_WEAKNESS(未满
    3 件伤害打折)⇒ 排序切换为「主输出位优先凑满 3 件」:已穿 <3 的
    单位升序优先(凑满通道);无词缀 ⇒ 原序(均匀/先到先得)。
    主输出位识别( carry 标记)随 comp 知识批定谳——当前以已穿件数
    代理(OPEN 呈报)。
    """
    if AFFIX_WEAKNESS not in enemy_affixes:
        return list(candidates)
    return sorted(candidates, key=lambda c: (min(c[1], 3), c[0]))


def keep_policy(redemption_distance: int) -> tuple[bool, str]:
    """§2.6 keep_policy:近兑现距离 d*≤1 绝不喂(P42 ③ 零参数公理)。"""
    if redemption_distance <= 1:
        return False, 'near_redemption'
    return True, ''


def endgame_context(r_remaining: int) -> str:
    """D-P3 收尾段语境(r7-r9 终局投资:星级/等级转向)。"""
    return 'endgame' if r_remaining <= 3 else 'midgame'
