"""简报屏观察契约与上报(kernel 纯数据;迭代
2026-09-18-screen-op-flat-report design.md §2.2/§2.3)。

观察面 = 入口门判定 + 三读数(敌人词缀/位面序 boss/敌人难度;读数
挪进观察侧归迁移批,本批字段进即写)。report 写点转录来源 =
operations/cw_screen/cw_screen_briefing.py::``_read_and_advance`` 三写点
(锚 :146-215);辖域边界 = design.md §2.3——原幂等守卫辖「读+采」,
词缀效果点采与登记留守画面 op 观察侧,收编后只辖容器写。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sr_od.application.currency_war.kernel.cw_game_state import (
    ChannelSig,
    GameState,
    _validate_sig,
)


@dataclass
class CwScreenBriefingObs:
    """简报屏观察结果(摄入口 = :func:`report_screen_briefing_obs`;三读数
    字段为本屏 report 所需——读数挪进观察侧归迁移批,本批字段进即写)。"""

    on_screen: bool = False
    #: 敌人词缀名单(OCR 原名;空 = 读缺或幂等门已挡,report 不写)。
    enemy_affixes: list[str] = field(default_factory=list)
    #: 位面序 boss 名(LCS 清洗后;None = 读空,report 恒覆写 None 防
    #: 跨局残留假真值)。
    plane_bosses: list[str] | None = None
    #: 敌人难度数值(简报「敌人难度N」;None = 读缺,report 仅 None 才写)。
    enemy_difficulty: int | None = None
    #: 稳定帧引用(实机识别域载体,与现役观察类一致)。
    screen: Any = None


def report_screen_briefing_obs(gs: GameState, obs: CwScreenBriefingObs, *,
                               sig: ChannelSig | None = None) -> None:
    """简报屏观察上报:三字段分闸落容器(写点锚 =
    cw_screen_briefing.py::``_read_and_advance`` 三写点,锚 :146-215;
    读数挪进观察侧归迁移批,本函数按字段进即写)。三闸语义逐位平移:

    - ``enemy_affixes``:幂等门「容器已有不重写」保留(原幂等守卫辖
      「读+采」,收编后只辖容器写——效果点采留守画面 op);
    - ``plane_bosses``:恒覆写,读空写 None(防跨局残留假真值);
    - ``enemy_difficulty``:仅 None 才写(恒稳开局基线,逐帧旗牌真读
      到达即覆盖)。
    """
    if sig is None:
        # screen='' 沿原写点(简报三写点 sig 均带空画面标识,照抄现役原值)。
        sig = ChannelSig(family='logic_action', actor='CwScreenBriefing',
                         screen='', mode='compute')
    _validate_sig(sig, ('logic_action',))
    if obs.enemy_affixes and not gs.enemy_affixes.value:
        gs.write_logic(gs.enemy_affixes, list(obs.enemy_affixes),
                       produced_by='CwScreenBriefing', sig=sig)
    gs.write_logic(
        gs.plane_bosses,
        list(obs.plane_bosses) if obs.plane_bosses else None,
        produced_by='CwScreenBriefing', sig=sig)
    if gs.enemy_difficulty.value is None and obs.enemy_difficulty is not None:
        gs.write_logic(gs.enemy_difficulty, obs.enemy_difficulty,
                       produced_by='CwScreenBriefing', sig=sig)
