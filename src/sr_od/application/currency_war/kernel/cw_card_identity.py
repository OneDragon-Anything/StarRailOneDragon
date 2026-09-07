"""卡牌身份分层单一源(T-115 规则③④共用判据;ADR-0580)。

同一「买入资格 × 卡牌身份」面上此前散布多套并列前件(M2 线内 /
dominance 零重叠 / C1 锁线核心 / ③ registry 核心 / ④ 转线件)——本模块
把「非线内身份」收拢为三分档单一源,新身份类需求只扩本 helper,不再加
并列前件(ADR-0580「架构归并方向」节)。

数据源(单一源,禁第二表):
- registry_core 层 = ``kernel.cw_comps.CORE_SINGLE_CARD_REGISTRY``
  (谓词式唯一入选规则,出处指针随值);
- transition_component 层 = ``knowledge.cw_line_facts.TRANSITION_PACK``
  档 ∈ {carry, partial}(T-115 规则④放行集;drop 档 = P1 末弃应急件
  不放行,cw_line_facts.py 档位值注释语义)。禁消费 kernel/cw_transition
  的同名迁移副本(该文件内明令「勿新增消费」,本模块是唯一新消费点)。

依赖方向:本模块只 import data/knowledge/kernel 注册表,不 import
strategies 面(kernel 输入纯度,同 cw_line_facts 声明)。
"""
from __future__ import annotations

from sr_od.application.currency_war.kernel.cw_comps import (
    CORE_SINGLE_CARD_REGISTRY,
)
from sr_od.application.currency_war.knowledge.cw_line_facts import (
    TRANSITION_PACK,
)

#: 身份档:registry 核心(③恒买辖域;C1 通道消费层)。
TIER_REGISTRY_CORE: str = 'registry_core'
#: 身份档:转线前瞻件(④放行辖域;Early 双轨期放行,定型后收窄)。
TIER_TRANSITION: str = 'transition_component'
#: 身份档:真无关件(维持 non_line 拒买)。
TIER_UNRELATED: str = 'unrelated'

#: ④放行档位集(TRANSITION_PACK 值元组第二位;drop 档不入选的理由见
#: 模块 docstring)。
_TRANSITION_RELEASE_TIERS: frozenset[str] = frozenset({'carry', 'partial'})


def transition_release_names() -> frozenset[str]:
    """④放行集 = TRANSITION_PACK 档 ∈ {carry, partial} 的在册件名集。

    为什么按档过滤而非取全表:drop 档(卡芙卡/椒丘/艾丝妲)= P1 末弃
    应急件,买入价值低(cw_line_facts.py 档位注释 + transition_score
    既有「预囤不囤 drop」取向同源);计算式候选(char_routes +
    pivot_overlap)已否决——「可达」需相似度阈值 = 拍值(ADR-0580)。
    TEMPO_POOL 是本集子集,不另并(cw_comps.py 两表包含关系在案)。
    """
    return frozenset(
        name for name, (_frame, tier) in TRANSITION_PACK.items()
        if tier in _TRANSITION_RELEASE_TIERS)


def sell_hold_exclusion_names() -> frozenset[str]:
    """凑息卖出资格集的静态持有类排除集(T-115 Z1 修法;ADR-0580)。

    集合 = CORE_SINGLE_CARD_REGISTRY ∪ transition_release_names()——
    ③④语义 = 持有,整类从凑息/筹资燃料资格排除,覆盖「已买待持有」
    与「在售未买」两态,防跨轮卖回(1★ 全额退会让 (a) 凑息臂机械抵消
    ③④买入)。drop 档与普通燃料件**不**在本集——排除集取窄设计:
    name 型零重叠语义下(statefn/predicates.zero_overlap 是纯名成员判定)
    静态全集排除会把 (a) 的全部 1★ 燃料资格掏空(方案审 v3 攻击点①
    实证),静态/动态切分是不掏空的窄形态。
    """
    return (frozenset(CORE_SINGLE_CARD_REGISTRY)
            | transition_release_names())


def line_identity_tier(name: str, k_members: tuple[str, ...] = ()) -> str:
    """非线内身份三分档(③④与拒因遥测共用单一源)。

    返回 ``TIER_REGISTRY_CORE`` / ``TIER_TRANSITION`` /
    ``TIER_UNRELATED`` 之一;两注册表对表即可判定,调用方先判线内
    (k_members/义务集)再消费本函数。

    ``k_members`` 参数是**前向扩展位**(ADR-0580 架构归并申报):当前
    三分档判定不消费它——预留语义 = 未来若分档需要「相对目标线」的
    语境(如转线相关性随已持线变化)在此扩展,**禁**在调用侧另挂第六套
    并列判据;签名含参是为防实施者误以为调用侧补语境是新挂点。
    """
    if name in CORE_SINGLE_CARD_REGISTRY:
        return TIER_REGISTRY_CORE
    if name in transition_release_names():
        return TIER_TRANSITION
    return TIER_UNRELATED
