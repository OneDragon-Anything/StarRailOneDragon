"""货币战争 线/过渡包注册事实(自 kernel 死刑判据文件迁入的权威副本)。

迁入出处:`docs/develop/currency_war/archive/redesign/03_legacy_cleanup_plan.md` 批 0
第 1/3/5 项——telemetry 保留层(schema/cw_win_model/query)与 kernel 保留件
(cw_system_cards/cw_battle_calib)消费的**数据半部**符号迁出死刑文件;
这些符号是攻略/实盘数据锚(出处逐条随行注明),不是决策拍值,归知识层。

依赖方向:本模块只 import 数据注册表(cw_chars/cw_factions),不 import
任何 kernel 判据/决策符号(设计 01_strategy_layer.md §1 权限规则)。

零漂移契约:各符号与旧位置(kernel/cw_line_defs、kernel/cw_transition、
kernel/cw_intention)逐字同体;旧位置副本仅为未迁消费点(sim/旧判据)
保留,随各自处死批次(处死计划批 2/3)删除。**新增消费一律 import 本模块。**
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


# —— 核心三人组(原 kernel/cw_line_defs._CORE_TRIO;r358)——
#: r358:核心三人组(combo_methodology 终版:功能链不可拆;
#: 数据单一源 = 桥池 xianzhou_dot 的 fixed+core 交集)
_CORE_TRIO: frozenset[str] = frozenset({'爻光', '藿藿', '丹恒·饮月'})

# —— P1 过渡包(原 kernel/cw_transition.TRANSITION_PACK)——
# P1 过渡双框架(r38 修正:plaza 549 篇阵营激活口径,主流 = 仙舟系 32% + 列车系 29%,
# 其余各 ≤5%;用户口径「DOT 和仙舟两种」——饮月/卡芙卡等仙舟阵营 flows 带 DOT,
# 「3仙舟+2DOT」在数据上呈现为仙舟大羁绊)。两包各自内部自洽,选其一集中买。
# 值:角色 → (框架, 档:carry=贯穿最终 / drop=P1末弃 / partial)
# ⚠️ r100 数据复核修正(用户抓的统计错误):入包双条件 = **Early 出现率 ≥8%** AND
# 过渡功能(保留率分档只在满足前者后才有意义)。旧口径按保留率分档混入了
# 「终局阵容成员」——瓦尔特(5费,Early 0.2%:等级锁刷不出,保留率暴涨是反向
# 指标=纯终局核心)被误标 列车/partial;娜塔莎(0.7%)/佩拉(1.1%)/腾荒(6.8%)
# Early 出现率过低无过渡资格。三者移除;花火(2费,Early 20%)/姬子·启行
# (3费,14%)数据核实无错保留。
TRANSITION_PACK: dict[str, tuple[str, str]] = {
    # —— 仙舟框架(32% 主流;3 仙舟大羁绊 + DOT flows)——
    '藿藿': ('仙舟', 'carry'),          # Early 33%→Final 20%
    '丹恒·饮月': ('仙舟', 'carry'),     # 31%→20%
    '爻光': ('仙舟', 'partial'),        # 25%→14%
    '卡芙卡': ('仙舟', 'drop'),         # 9%→7%(DOT 件)
    '椒丘': ('仙舟', 'drop'),           # 21%→8%
    # —— 列车框架(29% 主流;4 列车或 2 小羁绊)——
    '三月七': ('列车', 'carry'),        # 23%→31% 最强贯穿
    '姬子·启行': ('列车', 'carry'),     # 14%→39%
    # —— 量子框架(r102 统一化;希儿 59 帖:主流=3量子+2贝,量子契约/贝概念股环境;
    # 「过渡=终局雏形」线——carry 档=过渡终局同体,定型零交接)——
    '花火': ('量子', 'carry'),
    # ↑ 框架标签修正(comp 审计修复项4,2026-08-31):旧标 ('列车','carry') 系「花火有列车阵营」
    #   的误记——注册表 cw_chars 花火=盛会之星(阵营)+战技点/量子同频(流派),**无列车阵营**;
    #   其过渡/终局贡献走量子同频流派成员口径(20%→46%,Early 出现率与保留率数据不变,仅框架归属改)。
    '希儿': ('量子', 'carry'),          # 3费(Lv4 起 10%)Early 69%→贯穿 0.70(来牌即信号)
    '缇宝': ('量子', 'partial'),        # 2费(Lv4 起 25%)48% Early(量子+群攻双 flow)
    '符玄': ('量子', 'partial'),        # 4费(Lv5 起 2%——r102 审计①修正:非 2 费;
    #                                    量子 core 三件两件 ≥3费 → 配方成型窗口整体偏后,
    #                                    Lv5 前贝洛伯格档主要靠 pack 外贝件,属设计内)
    # —— 双框架通用插件 ——
    '千冶·刃': ('通用', 'carry'),       # 19%→51%(Final 反超:最强通用插件)
    # 纯过渡散件(框架外,仅应急)
    '艾丝妲': ('散件', 'drop'),         # 22%→3% 最纯过渡
}
# 移除记录(r100 复核):瓦尔特(5费 Early 0.2%=终局 core,非过渡件;列车终局 comp
# 已有)/娜塔莎(0.7%)/佩拉(1.1%)/丹恒·腾荒(6.8%)——Early 资格不足。
# r102 复核残留注记修正(修复项4,2026-08-31):r102 曾裁定「花火移列车框架不动(她双 flow:
# 列车阵营+量子)」——前半句与注册表冲突(花火阵营=盛会之星,无列车),已按注册表归位量子框架;
# 策略加分统一走 env/augment affinity,不走 pack(此口径不变)。

# —— 体系键与成员集(原 kernel/cw_intention)——
#: 希儿系体系键(单卡二元判定,不占羁绊键;与 cw_battle_calib._engines_count
#: 的希儿系哨兵同口径)。
SEELE_SYSTEM: str = '希儿系'


def _bond_members(bond: str) -> set[str]:
    """单羁绊成员名集(阵营∪流派全成员口径,与 cw_intention._pair_members
    同式;希儿系=希儿∪两放大器阵营成员)。遥测 ρ 实测的在店判据单一源。"""
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
