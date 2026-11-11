"""位面情报采集屏观察契约与上报(kernel 纯数据;权威版本 =
docs/develop/sr_od/application/currency_war/screens/op-layer.md)。

观察面 = 采集收获转录(纯数据,由采集 op 装配);report 写门 =
接管补采真值落状态容器的唯一一份写门(编排单一源 = CwEntryPlaneIntel,
判断线住本屏文件):位面序 boss 全量写 + 已有真值不覆写(简报源先落
时实采不冲真值);敌人词缀写门三分支(敌后破坏补观察闭环扩面,
正本 = screens/plane_intel.md 编排门三重节)——
状态容器空(非随机态)现役 logic 直写不变 / 状态容器随机态(logic_rand,删除分支
猜测名单或开局种子)observe 通道覆盖转正(非空与空列表读数均可,差异
落 ``logic_rand_outcome`` 台账,「亲眼看覆盖随机效果」语义)/ 状态容器
logic·observation 非空不写(现役幂等保持,防真值互踩)。写门渠道签名
按分支各语义定死:采集真值落账属 logic_action 族(同简报写点族);
随机态覆盖走 obs 族新签名(与现役 logic_action 签名并存),screen =
实际采集画面(本写点有明确宿主屏,非简报写点的空 screen),actor =
写者本体;对账网已停用,不在本写门。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sr_od.application.currency_war.kernel.cw_game_state import (
    ChannelSig,
    GameState,
)

#: 写门统一签名(定死值):family = logic_action(采集真值落账族),
#: actor = 写者本体,screen = 位面详情屏(实际采集画面),mode = compute。
_WRITE_SIG = ChannelSig(family='logic_action', actor='CwScreenPlaneIntel',
                        screen='货币战争-位面详情', mode='compute')

#: 随机态覆盖分支签名(定死值;obs 族 read 子模——「亲眼看覆盖随机
#: 效果」语义,与 logic_action 落账族签名并存各分支各语义,T-45 接入调用 3)。
_OBS_WRITE_SIG = ChannelSig(family='obs', actor='CwScreenPlaneIntel',
                            screen='货币战争-位面详情', mode='read')


@dataclass
class CwScreenPlaneIntelObs:
    """位面情报采集屏观察结果(统一形态门判定 + 采集收获;纯数据)。

    - ``on_screen``/``screen``:门判定与稳定帧引用(统一形态面)。
    - ``plane_bosses``:三位面 boss 身份,3 槽保位(恒全采语义下元素
      非 None;状态容器槽位 None = 简报源未读得,仅简报写点产生)。
    - ``enemy_affixes``:词缀横条读数(空列表 = 无词缀〔含删尽态有效
      语义读数,T-45〕;None = 本轮无此面,不进写门)。
    """

    on_screen: bool = False
    screen: Any = None
    plane_bosses: list[str] | None = None
    enemy_affixes: list[str] | None = None


def report_screen_plane_intel_obs(gs: GameState, obs: CwScreenPlaneIntelObs, *,
                                  sig: ChannelSig | None = None) -> None:
    """位面情报采集屏观察上报:采集真值落状态容器(写域唯一一份写门)。

    写门两件:

    - ``plane_bosses``:已有真值不覆写(简报源先落 = 真值已在,实采
      内容再新也只是重复或残留,不覆写);无真值时 3 槽保位全量写;
    - ``enemy_affixes`` 三分支(T-45 接入调用 3,分支序即短路序):
      ①读数 None = 本轮无此面/失读,非语义读数,不进写门(维持现态,
      随机态状态容器保持随机态、补观察谓词下帧继续命中);②状态容器来源
      logic_rand → observe 通道覆盖转正,读数非空或空列表均可(被覆盖
      对象是猜测不是真值,「空表覆写抹掉已有真值」的幂等门理由在本
      分支不适用;删尽态〔单词缀局删后 = []〕读数 [] 是 obs 契约有效
      语义读数,经 observe 写空表转正、谓词解除闭环收敛;差异落
      ``logic_rand_outcome`` 台账、等值零台账,覆盖后来源转正);③状态容器
      非随机态:空状态容器 + 非空读数 → 现役 write_logic 直写(采集真值
      落账族 logic_action,不变);非空状态容器 → 不写(现役幂等保持,
      防真值互踩)。

    ``sig`` 形参为统一形态占位:本写域签名按分支定死值构造,不受形参
    影响(先例 = 备战接管域写门)。
    """
    if obs.plane_bosses and not gs.plane_bosses.value:
        gs.write_logic(gs.plane_bosses, list(obs.plane_bosses),
                       produced_by='CwScreenPlaneIntel',
                       evidence='plane_intel_row', sig=_WRITE_SIG)
    if obs.enemy_affixes is None:
        return   # 本轮无此面/失读:非语义读数不进写门,维持现态
    if gs.enemy_affixes.source == 'logic_rand':
        # 随机态状态容器(删除分支猜测名单/开局种子)→ observe 覆盖转正
        #(亲眼看覆盖随机效果:差异落 logic_rand_outcome 台账、等值
        # 零台账,覆盖后来源转正、补观察谓词解除)
        gs.observe(gs.enemy_affixes, list(obs.enemy_affixes),
                   evidence='plane_intel_affixes', sig=_OBS_WRITE_SIG)
    elif obs.enemy_affixes and not gs.enemy_affixes.value:
        gs.write_logic(gs.enemy_affixes, list(obs.enemy_affixes),
                       produced_by='CwScreenPlaneIntel',
                       evidence='plane_intel_affixes', sig=_WRITE_SIG)
    # 其余(非随机态非空状态容器)→ 不写:现役幂等保持,防真值互踩
