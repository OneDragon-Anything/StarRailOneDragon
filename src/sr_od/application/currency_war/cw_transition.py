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

# P1 过渡包(plaza 数据驱动;纯过渡牌 + 贯穿牌;阵营=仙舟/DOT/群攻 系)
# 值:角色 → (优先级 0=核心 1=次选, 贯穿到最终阵容的概率档)
TRANSITION_PACK: dict[str, tuple[int, str]] = {
    # 贯穿牌(Early 高频且 Final 存活 ≥20%:过渡后无缝进最终线)
    '藿藿': (0, 'carry'),        # 44%→22% + 治疗/仙舟
    '丹恒·饮月': (0, 'carry'),   # 44%→20%
    '三月七': (0, 'carry'),      # 36%→36% 最强贯穿
    '爻光': (1, 'partial'),      # 35%→16%
    '千冶·刃': (0, 'carry'),     # 29%→64%(Final 比 Early 更高——既是过渡也是终点)
    '姬子·启行': (1, 'carry'),   # 24%→47%
    '花火': (1, 'carry'),        # 24%→48%
    # 纯过渡牌(Early 高频 Final 几乎全弃;P1 末应卖/换)
    '椒丘': (1, 'drop'),         # 31%→8%
    '艾丝妲': (1, 'drop'),       # 31%→2%(最纯过渡)
    '卡芙卡': (1, 'drop'),       # 12%→5%(DOT 件)
    '佩拉': (2, 'drop'),
    '娜塔莎': (2, 'drop'),
    '丹恒·腾荒': (1, 'partial'),  # 9%→21%
}

# 过渡包目标羁绊(快成型,低费)
TRANSITION_FACTIONS: tuple[str, ...] = ('仙舟', '持续伤害', '治疗', '列车同行')

# 过渡包阵容规模(Early 期上场人数目标;plaza Early 中位数)
TRANSITION_PACK_SIZE: int = 6


def in_early_phase(plane: int, committed: bool) -> bool:
    """Early 期判定:plane1 且最终线未 commit(form < COMMIT_FRAC 由调用方判)。"""
    return plane == 1 and not committed


def transition_score(char_id: str, faction: str) -> float:
    """买牌评分用:角色在过渡包中的价值(carry>partial>drop;阵营契合加成)。"""
    ent = TRANSITION_PACK.get(char_id)
    base = 0.0 if ent is None else {'carry': 1.0, 'partial': 0.6, 'drop': 0.4}[ent[1]]
    if faction in TRANSITION_FACTIONS:
        base += 0.3
    return base
