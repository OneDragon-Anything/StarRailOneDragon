"""开局血量(hp)初值表——遥测实证的先验,替代「开局 hp=None 诚实未知」的实证过档。

**数据出处 = hp0_survey 普查(2026-09-06,
`.debug/temp/currency_war/hp0_survey/报告.md`,133 局对局档案逐局 p1-r1 读数,
settlement 源 hp_confidence=1.0)**。

与已废止的「开局兜底 100」(引入、废止)的本质区别:
- 兜底 100 是无证据假值(实测定值非 100,毒化遥测);
- 本表只填**实证过的档**:A8/难度 108 下基础值 82(109 局零方差)、
  词缀「开局不利」恒 −20 → 62(7/7 局)。**其他难度/数值难度无数据,
  保持 None(诚实未知),禁外推**——133 局样本全为 A8/108,难度维度无法验证。

消费端 = ``cw_reconcile.reconcile_hp`` 开局分支(读不到且 session 无真值):
初值是**先验**不是真读——返回 readable=False,后续真值帧按既有新鲜度门
正常覆盖,禁覆盖真读。「时间刺客」不另设值(初值仍 82):它通过局内周期
扣血污染 1-1 读数(实测 r1=44/46,r2 回 84/86),不改初值;该污染的判读
由 hp 下行拒信/复现确认通道既有防线兜住,本表不碰判读。
"""
from __future__ import annotations

#: 基础初值(A8/数值难度 108,无修正词缀;109 局零方差)。
OPENING_HP_BASE: int = 82

#: 数值难度实证档(唯一有数据的档;其他数值难度无数据不查表)。
_KNOWN_ENEMY_DIFFICULTY: int = 108

#: 职级实证档(133 局全 A8;其他职级无数据不查表)。
_KNOWN_SELECTED_DIFFICULTY: str = 'A8'

#: 确定性词缀修正(词缀识别键 = 简报 OCR 原名,affix_effects_data 注册表同名键;
#: 「开局不利」效果原文「游戏开始时,小队生命值减少20点」,7/7 局实测 82−20)。
_AFFIX_HP_DELTA: dict[str, int] = {
    '开局不利': -20,
}


def opening_hp_prior(briefing_affixes: list[str] | None,
                     selected_difficulty: str | None,
                     enemy_difficulty: int | None) -> int | None:
    """开局 hp 初值 = f(词缀集),限实证过的难度档。

    Args:
        briefing_affixes: 简报敌人词缀 OCR 原名(session.briefing_affixes;
            None/空 = 未采到,按无修正词缀处理——词缀读链失败时初值仍可给,
            与「无词缀局」同值 82,实证上无修正词缀档占 109/116)。
        selected_difficulty: 本局职级(session.selected_difficulty;'' = 未检测)。
        enemy_difficulty: 数值难度(session.enemy_difficulty;None = 未读到)。

    Returns:
        实证档内的初值(82/62);难度档无实证(A8/108 之外,含未读到)→ None。
    """
    if (selected_difficulty or '').strip() != _KNOWN_SELECTED_DIFFICULTY:
        return None
    if enemy_difficulty != _KNOWN_ENEMY_DIFFICULTY:
        return None
    affixes = set(briefing_affixes or [])
    hp = OPENING_HP_BASE
    for name, delta in _AFFIX_HP_DELTA.items():
        if name in affixes:
            hp += delta
    return hp
