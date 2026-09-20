"""备战屏观察契约与上报(kernel 纯数据)。

观察面 = 重型屏薄包装 + 可选域。``prep`` = 现役 ``PrepObservation`` 整包
(kernel.cw_prep_actions,事件 overlay 面住整包内 ``prep.event_overlay``,
bail 控制信号不另立顶层字段防双源漂移)——其容器写端在观察漏斗
(read_game_state / observe_full 装配链)内部,本函数不重复承接。
可选域 = 本屏 op 层散落写点的收编载体,写点转录来源 =
operations/cw_screen/cw_screen_prep.py::``_write_prep_node_chain``
(备战帧现行链,gs.observe 双写 + 基线幂等)与
``_takeover_collect_if_needed``(接管局补采四写点,write_logic);
sig/actor/evidence 逐位沿用原写点原值。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sr_od.application.currency_war.kernel.cw_game_state import (
    ChannelSig,
    GameState,
    NodeChain,
    _validate_sig,
)
from sr_od.application.currency_war.kernel.cw_prep_actions import (
    PrepObservation,
)


@dataclass
class CwScreenPrepObs:
    """备战屏观察结果(重型屏薄包装 + 可选域;摄入口 =
    :func:`report_screen_prep_obs`,可选域字段在场才写,None = 本轮无此面)。

    - ``prep``:现役 ``PrepObservation`` 整包(事件 overlay 面 =
      ``prep.event_overlay``);容器写端在观察漏斗内部,本域无 report
      摄入面(不做二次落容器)。
    - ``event_overlay``:事件 overlay bail 标签镜像(取自
      ``prep.event_overlay``,便于决策侧/测试零穿透消费;无容器写域)。
    - ``node_path_chain``:备战帧现行链(挂点 = 备战入口 heavy 观察的
      节点行读;在场 = 本帧轮位对齐 clean 读,写 = node_path 双写 +
      node_path_baseline 幂等回填)。
    - ``takeover_tries``/``takeover_collect_done``:接管补采尝试计数 /
      完成闩(ResumeAttach 渠道③;每帧补采挂点按需写)。
    - ``plane_bosses``/``enemy_affixes``:接管补采收获(位面序保位写 /
      词缀空缺不写,门在采集链)。
    - ``screen``:稳定帧引用(实机识别域载体,与现役观察类一致)。
    """

    prep: PrepObservation = field(default_factory=PrepObservation)
    event_overlay: str | None = None
    node_path_chain: NodeChain | None = None
    takeover_tries: int | None = None
    takeover_collect_done: bool | None = None
    plane_bosses: list[str] | None = None
    enemy_affixes: list[str] | None = None
    screen: Any = None


def report_screen_prep_obs(gs: GameState, obs: CwScreenPrepObs, *,
                           sig: ChannelSig | None = None) -> None:
    """备战屏观察上报:可选域字段在场才写(全 None = 零写)。

    写点锚 = cw_screen_prep.py 原写点逐位(sig/actor/evidence 原值):

    - ``node_path_chain`` → ``gs.observe`` 双写:node_path(evidence=
      'prep_row')+ node_path_baseline 幂等回填(已有值不覆写,evidence=
      'prep_row_first');``sig`` 形参缺省时按备战帧观察渠道原值构造
      (family='obs', actor='CwScreenPrep', screen='货币战争-备战',
      mode='read', quality={'bench': 'real_read'})。
    - ``takeover_tries``/``takeover_collect_done``/``plane_bosses``/
      ``enemy_affixes`` → ``write_logic``(渠道③接管协议 logic_hook,
      actor='ResumeAttach',sig/evidence 在函数内按原写点构造,不受
      ``sig`` 形参影响——观察域与接管域渠道族不同,形参只辖观察域)。
    - ``prep``/``event_overlay``/``screen``:无容器摄入域(容器写端在
      观察漏斗),不产生写入。
    """
    if sig is None:
        sig = ChannelSig(family='obs', actor='CwScreenPrep',
                         screen='货币战争-备战', mode='read',
                         quality={'bench': 'real_read'})
    _validate_sig(sig, ('obs',))
    if obs.node_path_chain is not None:
        gs.observe(gs.node_path, obs.node_path_chain,
                   evidence='prep_row', sig=sig)
        if gs.node_path_baseline.value is None:
            gs.observe(gs.node_path_baseline, obs.node_path_chain,
                       evidence='prep_row_first', sig=sig)
    if obs.takeover_tries is not None:
        gs.write_logic(gs.takeover_tries, obs.takeover_tries,
                       produced_by='ResumeAttach',
                       evidence='takeover_collect_tries',
                       sig=ChannelSig(family='logic_hook',
                                      actor='ResumeAttach', mode='compute'))
    if obs.takeover_collect_done is not None:
        gs.write_logic(gs.takeover_collect_done, obs.takeover_collect_done,
                       produced_by='ResumeAttach',
                       evidence='takeover_collect_done',
                       sig=ChannelSig(family='logic_hook',
                                      actor='ResumeAttach', mode='compute'))
    if obs.plane_bosses is not None:
        gs.write_logic(gs.plane_bosses, obs.plane_bosses,
                       produced_by='ResumeAttach',
                       sig=ChannelSig(family='logic_hook',
                                      actor='ResumeAttach',
                                      screen='', mode='compute'))
    if obs.enemy_affixes is not None:
        gs.write_logic(gs.enemy_affixes, obs.enemy_affixes,
                       produced_by='ResumeAttach',
                       sig=ChannelSig(family='logic_hook',
                                      actor='ResumeAttach',
                                      screen='', mode='compute'))
