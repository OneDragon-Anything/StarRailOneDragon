"""货币战争 线注册事实(知识层权威副本)。

出处 = 阵容审计修正后的权威副本;旧 kernel/cw_transition 数据副本
已停用,策展过渡包(TRANSITION_PACK/档位标签)及其休眠判据族已随
统一保护集迭代删除。这些符号是攻略/实盘数据锚(出处逐条随行注明),
不是决策拍值,归知识层。

依赖方向:本模块只 import 数据注册表(cw_chars/cw_factions),不 import
任何 kernel 判据/决策符号(知识层单向依赖,禁反向 import 判据/决策层)。

单一源纪律:**新增消费一律 import 本模块,禁重建数据副本**;cw_line_defs/
cw_intention 的 sim/旧判据残留副本已标权威指向本模块,随各自消费点迁移淘汰。
"""
from __future__ import annotations

from sr_od.application.currency_war.data.cw_chars import CHARACTERS

# —— 过渡配方阵营/基础档(原 kernel/cw_line_defs;r271 统一单一源)——
# 口径源:docs/game/currency_war/research/user_playstyle.md [20]
# (过渡配方:3仙舟+2DOT 基础 → +2列车2护盾 渐进)。
RECIPE_FACTIONS: frozenset[str] = frozenset(
    {'仙舟', '持续伤害', '列车同行', '护盾'})
# 配方基础线:3 仙舟 + 2 DOT = 5 档(基础未满时散件不上板/找件刷)
RECIPE_BASE: int = 5


def recipe_tier(board: dict[str, int]) -> int:
    """板面的配方档数(board 里 ∈ RECIPE_FACTIONS 的档位和)。"""
    return sum(v for k, v in board.items() if k in RECIPE_FACTIONS)


# —— 核心三人组 ——
#: r358:核心三人组(combo_methodology 终版:功能链不可拆;
#: 数据单一源 = 桥池 xianzhou_dot 的 fixed+core 交集)
_CORE_TRIO: frozenset[str] = frozenset({'爻光', '藿藿', '丹恒·饮月'})

# —— P1 过渡框架键面(策展知识归知识层)——
# 框架 → 目标羁绊(Early 期 form 判定用)
FRAMEWORK_FACTIONS: dict[str, tuple[str, ...]] = {
    '仙舟': ('仙舟', '持续伤害'),       # 3仙舟+2DOT(guide 口径)
    '列车': ('列车同行',),               # 4 列车
    '量子': ('量子同频', '贝洛伯格'),    # 3量子+2贝(希儿线主流构成)
    # 狼狩/贝洛伯格两条已封存桥(hunt3/dot_belog)的
    # 框架映射随桥删除(已封存线不再有框架豁免通道);
    # 量子键的贝洛伯格保留——那是希儿线主流构成(希儿系判据内)。
}

# —— 体系键与成员集(原 kernel/cw_intention)——
#: 希儿系体系键(单卡二元判定,不占羁绊键;与 cw_battle_calib._engines_count
#: 的希儿系哨兵同口径)。
SEELE_SYSTEM: str = '希儿系'


def bond_members(bond: str) -> set[str]:
    """单羁绊成员名集(阵营∪流派全成员口径,与 cw_intention._pair_members
    同式;希儿系=希儿∪两放大器阵营成员)。遥测 ρ 实测的在店判据单一源。

    公开化(统一保护集迭代 changes/2026-10-15-unified-protection-set
    design.md §2.1):跨层成员枚举消费本公开口,禁各消费层同式复写第
    N 份;零行为改名。"""
    if bond == SEELE_SYSTEM:
        bonds: set[str] = {'量子同频', '贝洛伯格'}
        out: set[str] = {'希儿'}
    else:
        bonds = {bond}
        out = set()
    for name, c in CHARACTERS.items():
        if (set(c.factions) | set(c.flows)) & bonds:
            out.add(name)
    return out


def framework_members(framework: str) -> list[str]:
    """过渡框架成员名单(注册表现算;统一保护集迭代 design.md §2.4 ①:
    策展档位标签消费的迁移单一源,替代已删除的 TRANSITION_PACK 过滤)。

    成员 = 框架键面(:data:`FRAMEWORK_FACTIONS`)各羁绊 :func:`bond_members`
    的并集(阵营∪流派口径);未注册框架返回空表。返回序 = ``CHARACTERS``
    声明序——消费面(配方 core_chars)对序敏感,禁无序集合直出。"""
    bonds = FRAMEWORK_FACTIONS.get(framework, ())
    if not bonds:
        return []
    members: set[str] = set()
    for bond in bonds:
        members |= bond_members(bond)
    return [name for name in CHARACTERS if name in members]
