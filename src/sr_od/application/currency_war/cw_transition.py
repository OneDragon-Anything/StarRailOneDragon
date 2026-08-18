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


# ===== 定型信号管线(r39 用户指导:最终 comp 的选择信号从开局积累,双轨并行) =====
# 信号源(按到达顺序):简报词缀 → P1 投资策略 → P1 投资环境 → P1 商店供给倾向
# → 最晚 P2-3 投资策略/环境(最后一次有经济量转型的节点,之后锁死)。
# 权重 = 该信号对 comp 强度的证据量(词缀克制/定义型 augment 是强证据)。

#: 信号源 → 权重(mechanics_fit 的词缀 counter 是 0-1 负分,定义型 affinity≥0.9)
SIGNAL_WEIGHTS: dict[str, float] = {
    'briefing_affix': 1.5,      # 开局词缀(克制/加成直接改 comp 强度;mechanics_fit 主分)
    'invest_strategy': 2.0,     # 投资策略(定义型如黑塔纪元 affinity≥0.9 = 资源入口级)
    'invest_env': 1.0,          # 投资环境(方向性弱于策略)
    'shop_supply': 0.5,         # 商店供给(每回合弱证据,持续累积)
    # r44 用户指导:节点随机奖励同属信号——补给(钻/装备/角色)/遭遇(三态选卡)/
    # 奖励节点(晶矿球/礼盒)给的东西都是「本局走向」的证据(如补给送 Fate 角色
    # = 命运圣杯线信号;遭遇给装备 = 装备系线倾向)
    'supply_reward': 0.8,       # 补给节点产出(角色/装备定向)
    'encounter_reward': 0.6,    # 遭遇选卡(策略/装备)
    'bonus_reward': 0.4,        # 奖励节点随机产出(最弱证据)
}

#: 定型阈值:累积信号分超过此值 → 最终线定型(early 双轨期结束,卖过渡换最终)
COMMIT_SIGNAL_THRESHOLD: float = 3.0

#: 定型 deadline:P2-3 的投资策略/环境选择是最后转型节点(round 12 ≈ P2-r3);
#: 过此节点无论信号强弱必须定型(之后经济量不足以转型——用户口径)。
COMMIT_DEADLINE_T: int = 12

#: P1 过渡期人口上限(r39 用户指导 + plaza 实证:Early 上场 79% = 5 人,中位/众数 5;
#: 本质 = 低人口省升级金,尽快 50 金吃满息;等级在定型时才拉)。
EARLY_POP_CAP: int = 5


def t_of(plane: int, round_num: int) -> int:
    """全局节点序号(plane*9 + round 的简化;与 horizon 的 t 同构)。"""
    return (min(plane, 3) - 1) * 9 + max(1, min(round_num, 9))


def past_commit_deadline(plane: int, round_num: int) -> bool:
    """已过定型 deadline(P2-3 后)→ 最终线必须定型,不再双轨。"""
    return t_of(plane, round_num) >= COMMIT_DEADLINE_T


class CommitSignals:
    """最终线定型信号累积器(局级,挂 StrategySession;r39 双轨架构;r44 补全信号源)。

    各信号源到达时调 ``add``(源名 + 该源的 comp 分贡献),累积到每条线;
    ``leader`` 给当前倾向,``ready`` 判是否达定型阈值。双轨期买牌用
    ``leader`` 囤牌(bench 存最终线核心,场上仍打过渡包);``ready`` 或
    过 deadline → 定型(卖过渡换最终)。

    信号全景(r44 用户口径「当前局的整体观察」):开局词缀 → P1 投资策略/环境
    → 商店供给(持续)→ **节点随机产出**(补给角色/装备、遭遇选卡、奖励节点)
    ——凡「本局拿到了什么」都是选线证据,不是只有商店和投资。
    """

    def __init__(self) -> None:
        self.scores: dict[str, float] = {}

    def add(self, source: str, comp_scores: dict[str, float]) -> None:
        """累积一个信号源的 comp 分贡献(源权重 × 归一化分)。"""
        w = SIGNAL_WEIGHTS.get(source, 0.0)
        if w <= 0 or not comp_scores:
            return
        mx = max(comp_scores.values()) or 1.0
        for comp, s in comp_scores.items():
            self.scores[comp] = self.scores.get(comp, 0.0) + w * (s / mx)

    def leader(self) -> tuple[str, float] | None:
        """当前信号领先的线(名, 分);空返 None。"""
        if not self.scores:
            return None
        comp, sc = max(self.scores.items(), key=lambda kv: kv[1])
        return comp, sc

    def ready(self) -> bool:
        """达定型阈值(领先线信号分 ≥ COMMIT_SIGNAL_THRESHOLD)。"""
        lead = self.leader()
        return lead is not None and lead[1] >= COMMIT_SIGNAL_THRESHOLD


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
