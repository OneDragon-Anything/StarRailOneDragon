"""奖励节点经济纪律判据单一源(T-115 规则①②;ADR-0580)。

裁定权威 = 用户账本 408 行(「1-1/1-2 等奖励关不需要战力:升级抑制、
买卡压牌库优先」)+ [16] 勘误(原②「奖励节点买经验合法」已删除)。
四消费位(shop M3 臂前 / shop 必花域变体 / mandate M3 触发块 /
entry posture 授权链首位)与 ②(b) 帧型判据全部消费本模块的同一谓词,
禁第二套帧型判定(D3)。

两个失效方向各自按自身误判代价定,显式声明防混用(ADR-0580):
- node_type 不可辨(None)→ **抑制关(fail-open 不抑制)**。为什么:
  误拦升级 = 奖励帧人口停滞,误放 = 病灶复发一次;店开观察帧节点行
  被遮恒 None(cw_observation.py「prep_shop_open 节点行被遮」在案)是
  结构性常态,无先验可辨向,两难取宽。
- active_env 不可辨(空串缺省)→ **守卫关(抑制照常)**。为什么:环境
  缺省空串是常态先验——绝大多数局无过热环境;按「守卫开(豁免抑制)」
  会使规则①在常态局结构性失效。扑满帧 node_type 仍读 'reward'
  (cw_screen_prep.py「扑满=奖励图标已实证」在案),仅凭 node_type
  不可辨扑满,守卫必须用环境名单判据。

依赖方向:kernel 只 import data 注册表,不 import strategies/obs。
"""
from __future__ import annotations

from sr_od.application.currency_war.data.cw_invest_data import PLAZA_PORTALS
from sr_od.application.currency_war.kernel.cw_board_state import (
    BoardState,
    node_kind_of,
)

#: 扑满环境名单(单一源派生):PLAZA_PORTALS 效果文本含「奖励节点替换」
#: 的环境名——当前在册命中 = id105 经济过热 / id119 经济严重过热
#: (cw_invest_data.py;方案审 v3 已做派生完备性检查:PLAZA_PORTALS
#: 全表内含该子串者仅此两行,其余命中在 PlazaAugment 表,不在名单源)。
#: 派生式判据让版本重采自动跟上;失配方向(版本改词致漏派生)= 守卫
#: 对过热局系统性关闭,代码内不可检测,已申报盲区(版本重采检查单
#: 把 PLAZA_PORTALS 效果文本比对列入,ADR-0580)。
PIGGY_ENV_NAMES: frozenset[str] = frozenset(
    p.name for p in PLAZA_PORTALS if '奖励节点替换' in p.effect)


def is_piggy_reward_frame(bs: BoardState | None) -> bool:
    """扑满例外守卫:奖励型节点 ∧ 本局环境在扑满名单 → 抑制解除。

    环境读点 = ``state.active_env``(单一源 = 观测装配回写链:
    session.active_env 经 cw_observation 装配非空才拷入 state,实现
    禁绕开观测装配直读 session)。环境名不可辨(空串/不在名单)→
    False(守卫关,抑制照常,理由见模块 docstring 失效方向②)。
    """
    if bs is None:
        return False
    return str(bs.active_env.value or '') in PIGGY_ENV_NAMES


def reward_node_suppressed(bs: BoardState | None) -> bool:
    """规则①抑制谓词:可辨奖励帧 ∧ 非扑满环境 → 升级抑制。

    None fail-open(node_type 不可辨 → False)理由见模块 docstring
    失效方向①;battle/encounter/boss 等战斗类节点恒 False(P72 预算闸
    照旧,本规则不辖)。四消费位 + ②(b) 帧型判据共用本函数,禁第二套。

    ②(b) 同谓词同向声明(D3/方案规则②):压库买入臂的帧型判据就是
    本函数的返回值——可辨奖励帧(非扑满)= ②(b) 活跃域;None 帧与
    规则①同向取 False(②(b) 不发射),该域「禁死囤」由 ②(a) prep
    凑息接线承载(其触发 = gold<g*,节点无关,见 mandate 接线注释);
    None 帧上 M3 因规则① fail-open 照常求值(两臂并存,义务臂先判)。
    """
    if bs is None:
        return False
    if str(node_kind_of(bs) or '') != 'reward':
        return False
    return not is_piggy_reward_frame(bs)
