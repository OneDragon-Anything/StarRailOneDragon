"""奖励节点经济纪律判据单一源(规则①②)。

裁定权威 = 用户账本 408 行(「1-1/1-2 等奖励关不需要战力:升级抑制、
买卡压牌库优先」)+ [16] 勘误(原②「奖励节点买经验合法」已删除)。
四消费位(shop M3 分支前 / shop 富余段变体 / mandate M3 触发块 /
entry posture 授权链首位)与 ②(b) 帧型判据全部消费本模块的同一谓词,
禁第二套帧型判定(D3)。

失效方向:node_type 不可辨(None)→ **抑制关(fail-open 不抑制)**。为什么:
误拦升级 = 奖励帧人口停滞,误放 = 病灶复发一次;店开观察帧节点行
被遮恒 None(cw_observation.py「prep_shop_open 节点行被遮」在案)是
结构性常态,无先验可辨向,两难取宽。
(原扑满例外守卫——扑满环境帧解除抑制——已随 P8 废弃删除:2026-10-29
用户策略令「运营正确则战力与血线自洽,不为特殊节点改变节奏」+ 扑满
节点 151 局实机与全部 sim 零观测;扑满帧并入规则①域,git 可溯。)

依赖方向:kernel 只 import data 注册表,不 import strategies/obs。
"""
from __future__ import annotations

from sr_od.application.currency_war.data.cw_invest_data import PLAZA_PORTALS
from sr_od.application.currency_war.kernel.cw_game_state import (
    GameState,
    node_kind_of,
)

#: 扑满环境名单(单一源派生):PLAZA_PORTALS 效果文本含「奖励节点替换」
#: 的环境名——当前已登记命中 = id105 经济过热 / id119 经济严重过热。
#: 派生式判据让版本重采自动跟上。**现役消费 = sim 扑满环境建模
#: (cw_sim_backend.is_piggy_node)与 investments 扑满面板矿占位校验**——
#: 原策略侧扑满例外守卫已随 P8 废弃删除(2026-10-29)。
PIGGY_ENV_NAMES: frozenset[str] = frozenset(
    p.name for p in PLAZA_PORTALS if '奖励节点替换' in p.effect)


def reward_node_suppressed(gs: GameState | None) -> bool:
    """规则①抑制谓词:可辨奖励帧 → 升级抑制。

    None fail-open(node_type 不可辨 → False)理由见模块 docstring;
    battle/encounter/boss 等战斗类节点恒 False(P72 预算闸
    照旧,本规则不覆盖)。四消费位 + ②(b) 帧型判据共用本函数,禁第二套。

    ②(b) 同谓词同向声明(D3/方案规则②):压牌库买入分支的帧型判据就是
    本函数的返回值——可辨奖励帧 = ②(b) 活跃域;None 帧与
    规则①同向取 False(②(b) 不发出),该域「禁死囤」由 ②(a) prep
    凑利息接入调用承载(其触发 = gold<g*,节点无关,见 mandate 接入调用注释);
    None 帧上 M3 因规则① fail-open 照常求值(两分支并存,义务分支先判)。
    (原扑满例外——扑满环境帧抑制解除——已随 P8 废弃删除,2026-10-29,
    git 可溯;扑满零观测,删除零行为差。)
    """
    if gs is None:
        return False
    return str(node_kind_of(gs) or '') == 'reward'
