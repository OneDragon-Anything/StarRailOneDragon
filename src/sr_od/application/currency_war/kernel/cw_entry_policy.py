"""入口链难度确认屏的选职级缺省判据(判据单一源居 kernel)。

「选哪个难度」属策略选择(「在多个候选间做选择」归策略层,入口链不自拟
判据;判据居本模块纯函数,行为保持契约 = 同输入同动作):缺省策略 =
「恒选最高职级」——难度确认屏「按钮-返回最高职级」
在场即玩家未在最高职级,先切最高(按钮消失 = 已在最高)再开始对局。此前该
判据以「按钮在场性」形式内联入口链(operations/cw_entry/cw_entry_start.py
难度确认段,2026-08-03 入口画面建档发现),本模块立纯函数单一源,入口链降为
「观察难度屏(按钮在场 + 职级读数)→ 按意图机械点击」。

行为保持契约:同输入同动作,判据语义零改。
``current_difficulty`` 职级读数(如 "A5"/"A8",读不到为 None/"")是观察事实、
不参与本缺省策略分支——恒选最高不依赖当前职级;入参保留 = 观察束完整透出,
供遥测对账与后续策略化(如显式目标职级配置)时免改签名。职级下游消费链 =
effective_hp_threshold(D-32;单一源 kernel/cw_economy DIFFICULTY_HP_TABLE)。
依赖方向:本模块零 import(纯函数零 IO);kernel 禁依赖上层,入口链单向消费。
"""
from __future__ import annotations

from enum import StrEnum


class DifficultyEntryIntent(StrEnum):
    """难度确认屏的下一步动作意图词表(入口链按意图机械点击,不自拟判据)。"""

    #: 「按钮-返回最高职级」在场 = 未在最高职级 → 先点它切最高(恒选最高缺省)。
    SWITCH_TO_HIGHEST = 'switch_to_highest'
    #: 切最高按钮不在场(已在最高职级)且「按钮-开始对局」在场 → 点它开始对局。
    START_MATCH = 'start_match'
    #: 两按钮都未读到(转场帧/非难度确认屏)→ 不动作,入口链落回其余推进分支。
    KEEP_OBSERVING = 'keep_observing'


def difficulty_entry_intent(go_highest_btn_present: bool,
                            start_btn_present: bool,
                            current_difficulty: str | None
                            ) -> DifficultyEntryIntent:
    """难度确认屏动作意图缺省判据(「恒选最高」;纯函数零 IO)。

    输入 = 入口链观察事实:「按钮-返回最高职级」在场布尔(在场 = 未在最高
    职级)、「按钮-开始对局」在场布尔、当前职级读数(见模块 docstring)。
    输出 = 下一步动作意图。

    切最高先于开始对局(原入口链分支序,行为保持):同帧双在场按原行为
    先切最高;两按钮皆缺 → KEEP_OBSERVING(入口链按原行为落回其余推进
    分支,不点任何东西)。
    """
    if go_highest_btn_present:
        return DifficultyEntryIntent.SWITCH_TO_HIGHEST
    if start_btn_present:
        return DifficultyEntryIntent.START_MATCH
    return DifficultyEntryIntent.KEEP_OBSERVING
