"""sim 重做基座:容器写入签名/证据标签的共用面。

设计正本 = ``docs/develop/sr_od/application/currency_war/changes/
2026-09-15-sim-redesign/design.md``(下称「重做设计稿」)§2.0.1/§2.0.3:
sim 真值写 obs 渠道(与 live 同一容器、同一渠道架构),动作应用写
logic_action 渠道(经 kernel 单一转移函数)。本模块只承载「sim 侧
怎么署名写入」,不含任何游戏规则。

evidence 前缀 = ``sim:engine:``:与旧引擎同前缀契约——该前缀在容器
``_MISMATCH_SUPPRESS_PREFIXES`` 登记为失配抑制面,内核零改动即可复用
(重做设计稿 §2.4.3「契约平移」)。
"""
from __future__ import annotations

from sr_od.application.currency_war.kernel.cw_game_state import (
    ChannelSig,
)

#: sim 引擎写入者名(重做引擎全部 obs/logic 写入署名此名)。
SIM_ENGINE_ACTOR: str = 'SimEngineV2'

#: sim 真值写入证据前缀(失配抑制登记面契约,见模块 docstring)。
SIM_EVIDENCE_PREFIX: str = 'sim:engine:'


def sim_evidence(tag: str) -> str:
    """证据标签 = 前缀 + 写点语义 tag(如 ``opening``/``income:p1r3``)。"""
    return f'{SIM_EVIDENCE_PREFIX}{tag}'


def obs_sig(group_id: str | None = None) -> ChannelSig:
    """sim 真值合成签名(obs 族,mode=synthesized;重做设计稿 §2.0.1
    「环境事件以 obs 渠道写容器」的署名形态)。"""
    return ChannelSig(family='obs', actor=SIM_ENGINE_ACTOR,
                      mode='synthesized', group_id=group_id)


def logic_sig(group_id: str) -> ChannelSig:
    """动作应用签名(logic_action 族;动作经 kernel 单一转移函数署名)。"""
    return ChannelSig(family='logic_action', actor=SIM_ENGINE_ACTOR,
                      mode='compute', group_id=group_id)
