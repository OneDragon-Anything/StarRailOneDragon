"""卡牌静态持有排除集(凑息/筹资卖面资格的静态身份面;过渡载体)。

同一「买入资格 × 卡牌身份」面上此前散布多套并列前件(M2 线内 /
dominance 零重叠 / C1 终局阵容锁定核心 / ③ registry 核心 / ④ 转线件)
——三分档 helper ``line_identity_tier`` 曾是「非线内身份」单一源;统一
保护集迭代(changes/2026-10-15-unified-protection-set design.md §2.4)
后消费点全部迁移(②(b) prio/D7 拒因/hold 登记档位 → 保护集口径,
C1 → ``CORE_SINGLE_CARD_REGISTRY`` 直判),函数随批退役。本模块现役
只余卖面静态持有排除集(:func:`sell_hold_exclusion_names`),其 ④
放行集构成随卖面五消费点迁移逐批退役(终态 = 保护集 ∪ registry 核心,
design §2.3 表;函数本体退役归 3.3)。

数据源(单一源,禁第二表):
- registry 核心 = ``kernel.cw_comps.CORE_SINGLE_CARD_REGISTRY``
  (谓词式唯一入选规则,出处指针随值);
- ④ 放行集 = ``knowledge.cw_line_facts.TRANSITION_PACK`` 档 ∈
  {carry, partial}(退役中的策展口径,仅 :func:`sell_hold_exclusion_
  names` 过渡消费)。禁消费 kernel/cw_transition 的同名迁移副本
  (该文件内明令「勿新增消费」)。

依赖方向:本模块只 import data/knowledge/kernel 注册表,不 import
strategies 面(kernel 输入纯度,同 cw_line_facts 声明)。
"""
from __future__ import annotations

from sr_od.application.currency_war.kernel.cw_comps import (
    CORE_SINGLE_CARD_REGISTRY,
)
from sr_od.application.currency_war.kernel.cw_line_defs import (
    ENGINE_FACTIONS,
)
from sr_od.application.currency_war.knowledge.cw_line_facts import (
    TRANSITION_PACK,
)

#: ④放行档位集(TRANSITION_PACK 值元组第二位;drop 档不入选的理由见
#: 模块 docstring;随下方 ④ 放行集读口同批退役)。
_TRANSITION_RELEASE_TIERS: frozenset[str] = frozenset({'carry', 'partial'})


def transition_release_names() -> frozenset[str]:
    """④放行集 = TRANSITION_PACK 档 ∈ {carry, partial} 的已登记件名集。

    为什么按档过滤而非取全表:drop 档(卡芙卡/椒丘/艾丝妲)= P1 末弃
    应急件,买入价值低(cw_line_facts.py 档位注释 + transition_score
    既有「预囤不囤 drop」取向同源);计算式候选(char_routes +
    pivot_overlap)已否决——「可达」需相似度阈值 = 拍值。
    TEMPO_POOL 是本集子集,不另并(cw_comps.py 两表包含关系在案)。

    退役申报(统一保护集 design §2.2/§2.4):④ 转投分支已随 3.2 退役,
    本函数余下唯一消费 = :func:`sell_hold_exclusion_names`(过渡载体,
    3.3 随该函数退役;身份单一源 = mandate_v1/protection)。
    """
    return frozenset(
        name for name, (_frame, tier) in TRANSITION_PACK.items()
        if tier in _TRANSITION_RELEASE_TIERS)


def sell_hold_exclusion_names() -> frozenset[str]:
    """凑利息卖出资格集的静态持有类排除集。

    集合 = CORE_SINGLE_CARD_REGISTRY ∪ transition_release_names()——
    ③④语义 = 持有,整类从凑利息/筹资燃料资格排除,覆盖「已买待持有」
    与「在售未买」两态,防跨轮卖回(1★ 全额退会让 (a) 凑利息分支机械抵消
    ③④买入)。drop 档与普通燃料件**不**在本集——排除集取窄设计:
    name 型零重叠语义下(statefn/predicates.zero_overlap 是纯名成员判定)
    静态全集排除会把 (a) 的全部 1★ 燃料资格掏空(方案审 v3 攻击点①
    实证),静态/动态切分是不掏空的窄形态。

    退役申报(统一保护集 design §2.3 五消费面表):本函数 = ④ 时代的
    静态持有面,五消费点逐批迁移(hold 登记名字腿已迁保护集 ∪ registry
    核心 = 3.2;余下四点归 3.3),迁毕函数退役——身份单一源 =
    mandate_v1/protection.protection_membership。
    """
    return (frozenset(CORE_SINGLE_CARD_REGISTRY)
            | transition_release_names())


def is_engine_piece(name: str) -> bool:
    """引擎件身份(注册表现算单一源;种子排除,P78-7)。

    判据 = 角色注册表 factions∪flows 与引擎三阵营(ENGINE_FACTIONS,
    桥池 engine_bonds 派生)交集非空——与 ``cw_line_defs.classify_buy``
    的 ``'engine'`` 分支同判据;本函数 = 生产决策位可直调的单一源
    (禁第二实现)。种子身份 = 本谓词 ∧ 购买时未持有(第二合取需购买史语境,
    由 sell_gate 种子登记簿在获取时点承载)。

    import 边申报:cw_line_defs 头部迁移待办的「勿新增消费」明示对象
    = RECIPE_FACTIONS/RECIPE_BASE/recipe_tier 三符号(权威副本在
    knowledge/cw_line_facts);ENGINE_FACTIONS 无 knowledge 侧权威
    副本,本 import 是既有判定核的消费边非复制。
    """
    from sr_od.application.currency_war.data.cw_chars import CHARACTERS
    ch = CHARACTERS.get(name or '')
    if ch is None:
        return False
    bonds = set(ch.factions) | set(ch.flows)
    return bool(bonds & set(ENGINE_FACTIONS))
