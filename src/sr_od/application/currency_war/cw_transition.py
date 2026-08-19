"""P1 过渡包模型(r37;用户指导 + plaza 784 篇 V4.4 数据实证)。

**玩法理解单一源**:`docs/game/gameplay/currency_war.md` §「玩法策略模型」S2(双轨/
过渡框架)与 S4(定型信号)——**改本模块前先读该文档并对表**,理解变更先改文档
(防实现漂移);数据锚与决策史见 ADR-0209。

**问题**:select_comp 从最终 comp 选线 → P1 买「半成型最终线」(form 0.25-0.5)
打不过玩家的「标准过渡包」(2 羁绊即成型)→ P1 后段战力崩 → boss 稳定损 30+。

**数据**(plaza lineups_HotHard.jsonl,V4.4 有效 784 篇):
- Early∩Final 重叠双峰:38% ≥80%(一条线)/ 22% ≤20%(标准过渡包,完全换阵)
- 纯过渡牌(Early 高频 → Final 必弃):艾丝妲 31%→2% / 椒丘 31%→8% /
  爻光 35%→16% / 饮月 44%→20% / 藿藿 44%→22%
- 贯穿牌:三月七 36%→36% / 千冶·刃 29%→64% / 姬子/花火 24%→48%
- 过渡框架 = 仙舟 32% + 列车 29%(主流仅两种;DOT 为挂件形态 28%)

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
    '花火': ('列车', 'carry'),          # 20%→46%(2费,非 4 费——注册表+plaza 双核实)
    # —— 双框架通用插件 ——
    '千冶·刃': ('通用', 'carry'),       # 19%→51%(Final 反超:最强通用插件)
    # 纯过渡散件(框架外,仅应急)
    '艾丝妲': ('散件', 'drop'),         # 22%→3% 最纯过渡
}
# 移除记录(r100 复核):瓦尔特(5费 Early 0.2%=终局 core,非过渡件;列车终局 comp
# 已有)/娜塔莎(0.7%)/佩拉(1.1%)/丹恒·腾荒(6.8%)——Early 资格不足。

# 框架 → 目标羁绊(Early 期 form 判定用)
FRAMEWORK_FACTIONS: dict[str, tuple[str, ...]] = {
    '仙舟': ('仙舟', '持续伤害'),       # 3仙舟+2DOT(guide 口径)
    '列车': ('列车同行',),               # 4 列车
}
FRAMEWORKS: tuple[str, ...] = ('仙舟', '列车')


def in_early_phase(plane: int, committed: bool) -> bool:
    """Early 期判定:plane1 且最终线未 commit(form < COMMIT_FRAC 由调用方判)。"""
    return plane == 1 and not committed


def pick_framework(bench, deployed, shop=None, current: str = '') -> str:
    """r70 过渡框架选定(买/上/卖三侧单一源):按当前持有(board+bench,可选 shop)的
    框架件计数取领先框架;平局/全零 → ''(未定,消费方按散件口径)。

    data 口径:主流 = 仙舟 32% + 列车 29%,其余 ≤5%(模块头 plaza 实证)。选定后:
    - 买侧:transition_score(char, fw=framework) 同框架加成(r70 前该参数恒 '' = 加成空转);
    - 上侧:deploy 双轨期以 FRAMEWORK_FACTIONS[framework] 为临时 target(框架牌不再是
      「off-target 散牌留 bench」);
    - 卖侧:keep 集保护当先框架的 carry/partial(防「买了→不上→被当散牌卖」循环)。

    r72 review 滞后(hysteresis):**切换需挑战者领先现任 ≥1(整权)** —— shop 半权
    (0.5/张)随刷新噪声每轮变动,临界区(仙2 vs 列1.5)会每轮翻转 → 买侧跟着转 →
    churn。现任保持门槛低(持平即留),换门槛高(领先 1),消除噪声翻转。
    """
    counts = {'仙舟': 0, '列车': 0}
    for bc in (*deployed, *bench):
        ent = TRANSITION_PACK.get(getattr(bc, 'char_id', ''))
        if ent and ent[0] in counts:
            counts[ent[0]] += 1
    if shop:
        for c in shop:
            ent = TRANSITION_PACK.get(getattr(c, 'name', ''))
            if ent and ent[0] in counts:
                counts[ent[0]] += 0.5   # 商店在售 = 即可得,半权
    fw = max(counts, key=lambda k: counts[k])
    if counts[fw] < 2:
        return ''
    if current and current in counts and counts[current] >= counts[fw] - 1.0:
        return current   # 滞后:现任未被领先 ≥1 → 保持(防 shop 噪声每轮翻转)
    return fw


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

#: 定型阈值:累积信号分超过此值 → 最终线定型(early 双轨期结束,卖过渡换最终)。
#: r56 审查#1 修:3.0→5.0(旧值下 词缀1.5+策略2.0=3.5 即 ready → r1-r2 必定型,
#: 双轨期形同虚设;live 实锤反甲白厄 r2 定型)。5.0 = 词缀+策略+环境+供给
#: 的持续积累(单靠两源不够)。
COMMIT_SIGNAL_THRESHOLD: float = 5.0

#: 最早定型轮门(r56 审查#1):t<COMMIT_MIN_T 不允许信号定型(P1 早期证据不足,
#: 强制双轨观察;deadline 仍兜底)。
COMMIT_MIN_T: int = 7

#: 定型边界(2026-08-18 P2-3 语义收口):**进位面 2 即定型**(t=10,P2-r1;消费方
#: ``default_strategy._committed`` 的 ``state.plane >= 2``)。旧 COMMIT_DEADLINE_T=12
#: (P2-3)分支被 plane>=2 恒短路(10 < 12)永不触发 = 死代码,已删 —— 保留的行为是
#: 更严的 P2-r1 边界(ADR-0209「双轨期 = P1 且未定型」的原始设计,live 验证)。
#: 文档口径「P2-3 是最后转型节点」仍成立:P2-r1 定型早于 P2-3,满足同一约束。

#: P1 过渡期人口上限(r39 用户指导 + plaza 实证:Early 上场 79% = 5 人,中位/众数 5;
#: 本质 = 低人口省升级金,尽快 50 金吃满息;等级在定型时才拉)。
EARLY_POP_CAP: int = 5


def t_of(plane: int, round_num: int) -> int:
    """全局节点序号(plane*9 + round 的简化;与 horizon 的 t 同构)。"""
    return (min(plane, 3) - 1) * 9 + max(1, min(round_num, 9))


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

    def ready(self, t: int = 0) -> bool:
        """达定型条件:领先线信号分 ≥ 阈值 **且** t ≥ COMMIT_MIN_T(r56 审查#1:
        轮门防 r1-r2 证据不足即锁;早轮双轨强制观察)。t=0(缺省)不设门(兼容)。"""
        if t and t < COMMIT_MIN_T:
            return False
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
