"""P1 过渡包模型(r37;用户指导 + plaza 784 篇 V4.4 数据实证)。

**问题**:select_comp 从最终 comp 选线 → P1 买「半成型最终线」(form 0.25-0.5)
打不过玩家的「标准过渡包」(2 羁绊即成型)→ P1 后段战力崩 → boss 稳定损 30+。

**数据**(plaza lineups_HotHard.jsonl,V4.4 有效 784 篇):
- Early∩Final 重叠双峰:38% ≥80%(一条线)/ 22% ≤20%(标准过渡包,完全换阵)
- 纯过渡牌(Early 高频 → Final 必弃):艾丝妲 31%→2% / 椒丘 31%→8% /
  爻光 35%→16% / 饮月 44%→20% / 藿藿 44%→22%
- 贯穿牌:三月七 36%→36% / 千冶·刃 29%→64% / 姬子/花火 24%→48%
- 过渡框架 = 3仙舟 + 2DOT(guide「中期护航」同源)

**模型**:``TRANSITION_PACK`` = Early 高频纯过渡+贯穿牌的目标集合;
``in_early_phase`` 判 Early(plane1 + 未 commit 最终线);
plan 的买牌/上阵在 Early 期以过渡包为 target(过渡包羁绊低费快成型),
P1 末/P2 起切最终 comp(select_comp 照常,积累的贯穿牌无缝继承)。
"""
from __future__ import annotations

# P1 过渡双框架(r38 修正:plaza 549 篇阵营激活口径,主流 = 仙舟系 32% + 列车系 29%,
# 其余各 ≤5%;用户口径「DOT 和仙舟两种」——饮月/卡芙卡等仙舟阵营 flows 带 DOT,
# 「3仙舟+2DOT」在数据上呈现为仙舟大羁绊)。两包各自内部自洽,选其一集中买。
# 值:角色 → (框架, 档:carry=贯穿最终 / drop=P1末弃 / partial)
TRANSITION_PACK: dict[str, tuple[str, str]] = {
    # —— 仙舟框架(32% 主流;3 仙舟大羁绊 + DOT flows)——
    '藿藿': ('仙舟', 'carry'),          # Early 44%→Final 22%
    '丹恒·饮月': ('仙舟', 'carry'),     # 44%→20%
    '爻光': ('仙舟', 'partial'),        # 35%→16%
    '卡芙卡': ('仙舟', 'drop'),         # 12%→5%(DOT 件)
    '椒丘': ('仙舟', 'drop'),           # 31%→8%
    '娜塔莎': ('仙舟', 'drop'),
    # —— 列车框架(29% 主流;4 列车或 2 小羁绊)——
    '三月七': ('列车', 'carry'),        # 36%→36% 最强贯穿
    '姬子·启行': ('列车', 'carry'),     # 24%→47%
    '花火': ('列车', 'carry'),          # 24%→48%
    '瓦尔特': ('列车', 'partial'),
    # —— 双框架通用插件 ——
    '千冶·刃': ('通用', 'carry'),       # 29%→64%(Final 反超:最强通用插件)
    '丹恒·腾荒': ('通用', 'partial'),   # 9%→21%
    # 纯过渡散件(框架外,仅应急)
    '艾丝妲': ('散件', 'drop'),         # 31%→2% 最纯过渡
    '佩拉': ('散件', 'drop'),
}

# 框架 → 目标羁绊(Early 期 form 判定用)
FRAMEWORK_FACTIONS: dict[str, tuple[str, ...]] = {
    '仙舟': ('仙舟', '持续伤害'),       # 3仙舟+2DOT(guide 口径)
    '列车': ('列车同行',),               # 4 列车
}
FRAMEWORKS: tuple[str, ...] = ('仙舟', '列车')


def in_early_phase(plane: int, committed: bool) -> bool:
    """Early 期判定:plane1 且最终线未 commit(form < COMMIT_FRAC 由调用方判)。"""
    return plane == 1 and not committed


def transition_score(char_id: str, faction: str, framework: str = '') -> float:
    """买牌评分用:角色在过渡框架中的价值(carry>partial>drop;同框架+阵营契合加成)。

    framework 传当前选定的过渡框架('仙舟'/'列车'),同框架牌加成;
    ''(未定框架)= 仅按档位。散件恒低分(应急才买)。
    """
    ent = TRANSITION_PACK.get(char_id)
    if ent is None:
        base = 0.0
    else:
        fw, tier = ent
        base = {'carry': 1.0, 'partial': 0.6, 'drop': 0.4}.get(tier, 0.3)
        if fw == framework:
            base += 0.3   # 同框架集中
        elif fw == '通用':
            base += 0.15  # 通用插件次之
    if faction in FRAMEWORK_FACTIONS.get(framework, ()):
        base += 0.2
    return base
