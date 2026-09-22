"""P1 过渡包模型(用户指导 + plaza 784 篇 V4.4 数据实证)。

**玩法理解单一源**:双轨(过渡→终局)/ 过渡框架 / 定型判定的玩法知识归
``docs/game/currency_war/research/`` 知识树(过渡体系 → transitions.md 与
transition_combos.md;位面演化定量 → stage_transitions.md;打法纪律 →
user_playstyle.md)——**改本模块前先读并对表**,理解变更先改文档
(防实现漂移)。

**问题**:select_comp 从最终 comp 选线 → P1 买「半成型最终线」(form 0.25-0.5)
打不过玩家的「标准过渡包」(2 羁绊即成型)→ P1 后段战力崩 → boss 稳定损 30+。

**数据**(plaza lineups_HotHard.jsonl,V4.4 有效 784 篇):
- Early∩Final 重叠双峰:38% ≥80%(一条线)/ 22% ≤20%(标准过渡包,完全换阵)
- 纯过渡牌(Early 高频 → Final 必弃):艾丝妲 31%→2% / 椒丘 31%→8% /
  爻光 35%→16% / 饮月 44%→20% / 藿藿 44%→22%
- 贯穿牌:三月七 36%→36% / 千冶·刃 29%→64% / 姬子/花火 24%→48%
- 过渡框架 = 仙舟 32% + 列车 29%(主流仅两种;DOT 为挂件形态 28%)

**模型**:``TRANSITION_PACK`` = Early 高频纯过渡+贯穿牌的目标集合;
Early 期判定(plane1 + 未定型)由消费方内联声明(框架启动变体已退役)。
plan 的买牌/上阵在 Early 期以过渡包为 target(过渡包羁绊低费快成型),
P1 末/P2 起切最终 comp(select_comp 照常,积累的贯穿牌无缝继承)。

**数据宿主**:TRANSITION_PACK/FRAMEWORK_FACTIONS/FRAMEWORKS 权威副本 =
``knowledge/cw_line_facts.py``(策展数据归知识层);本模块只留 kernel 判据函数,
从 knowledge 取数,禁在本模块重建数据副本。
"""
from __future__ import annotations

from sr_od.application.currency_war.knowledge.cw_line_facts import (
    FRAMEWORK_FACTIONS,
    FRAMEWORKS,
    TRANSITION_PACK,
)


def _framework_counts(bench, deployed,
                      shop=None) -> tuple[dict[str, int], dict[str, float]]:
    """框架件计数单一源:持有权(整权)+ 合并权(持有 + shop 半权)。

    输入约定:bench/deployed 元素带 ``char_id``(None 槽跳过),shop 元素带
    ``name``。owned = deployed+bench 整权计数(只认 bot 真持有);counts =
    owned + 商店在售 0.5/张(在售 = 即可得)。禁在调用侧复算第二份。
    """
    counts: dict[str, float] = dict.fromkeys(FRAMEWORKS, 0)
    owned: dict[str, int] = dict.fromkeys(FRAMEWORKS, 0)
    for bc in (*deployed, *(b for b in bench if b is not None)):
        ent = TRANSITION_PACK.get(getattr(bc, 'char_id', ''))
        if ent and ent[0] in counts:
            counts[ent[0]] += 1
            owned[ent[0]] += 1
    if shop:
        for c in shop:
            ent = TRANSITION_PACK.get(getattr(c, 'name', ''))
            if ent and ent[0] in counts:
                counts[ent[0]] += 0.5   # 商店在售 = 即可得,半权(启动期也计入)
    return owned, counts


def pick_framework(bench, deployed, shop=None, current: str = '', portal: str = '') -> str:
    """过渡框架选定(买/上/卖三侧单一源):按当前持有(board+bench,可选 shop)的
    框架件计数取领先框架;平局/全零 → ''(未定,消费方按散件口径)。

    data 口径:主流 = 仙舟 32% + 列车 29%,其余 ≤5%(模块头 plaza 实证)。选定后:
    - 买侧:transition_score(char, fw=framework) 同框架加成(该参数未传框架时加成空转);
    - 上侧:deploy 双轨期以 FRAMEWORK_FACTIONS[framework] 为临时 target(框架牌不再是
      「off-target 散牌留 bench」);
    - 卖侧:keep 集保护当先框架的 carry/partial(防「买了→不上→被当散牌卖」循环)。

    滞后(hysteresis)设计:**切换需挑战者领先现任 ≥1(整权)** —— shop 半权
    (0.5/张)随刷新噪声每轮变动,临界区(仙2 vs 列1.5)会每轮翻转 → 买侧跟着转 →
    churn。现任保持门槛低(持平即留),换门槛高(领先 1),消除噪声翻转。

    **portal 偏置**(特型环境 = 过渡=终局重叠的成因,plaza portals 实证:
    列车概念股 126 帖+列车邀请 84 帖):开局环境给框架方向时(portal 名含框架名),
    该框架计数 +3 等效权(开局送件+概率提高 = 数据级先验;普通来牌权压不过它,
    但真金白银买到 4 张对立框架件时仍可翻转——偏置不是锁死)。portal='' 无偏置。

    三框架:量子加入 counts(FRAMEWORKS 单一源;希儿/缇宝/符玄持有计数 +
    量子契约 portal 偏置)。量子件 3 费为主 → 早期自然不被选(计数起不来),
    中后期希儿出现即上——时机交给计分,不交给特判(用户定调)。

    **开局先有鸡还是先有蛋**(实机实证):若 shop 半权只在框架
    已定后参与滞后判定,开局「持有 0-1 张 → counts<2 → 框架=''」→ 无配方评分
    引导 → 不买框架件 → 计数永远起不来 = **死锁**(前 6 轮死锁期由压缩买接管,
    板面 11 角色五阵营散买(r1-r6 实拍),hp 45 才凑齐 2 张启动——掉的血就是
    死锁代价)。**框架未定时,持有整权 + shop 在售半权合并计入启动判定**
    (1 张持有 + 2 张在售 = 2.0 ≥ 2 即可选定)——店里有三月七就值得选列车,
    买下后持有权巩固框架,死锁破。已定框架的滞后判定(领先 ≥1 才换)不变。

    **预囤**(蒙特卡洛 2000 局实证:仅「合并权启动判定」不够):单框架/商店期望仅
    0.24-0.55 张(池密度:1费20%/2费33%/3费14%/4费7%),合并权 ≥2 的启动率
    **0.5%**——死锁只是缓解未破。破法=**未定框架期「见框架件就囤」**(买最便宜
    的框架件,不管哪框架;持有最多者启动)——人类打法「拿到三月七/藿藿就围绕
    它走」。MC:C 策略(gate1.5+预囤)启动率 99.9%/r1.4 启动/4.95 框架件
    (vs B 纯降门 10.5%)。启动门同步 2→1.5(预囤在位后 1.5 = 持有1+在售1,
    足够信号;纯 shop 1.0 仍不够格防噪声)。
    """
    owned, counts = _framework_counts(bench, deployed, shop)
    if portal:
        for fw in counts:
            if fw in portal:
                counts[fw] += 3   # 环境先验等效权(约 3 张框架件;可被实际来牌翻越)
                break
    fw = max(counts, key=lambda k: counts[k])
    # 平局按 dict 序偏仙舟(FRAMEWORKS 首位)——主流先验(32% vs 29%),
    # 有意为之:同计数时选数据上更主流的框架。
    # 启动门槛 = 合并权 ≥2(持有 1+在售 2 即启动);
    # 预囤在位后启动门 1.5(纯 shop 1.0 仍不够)。
    # **选定与保持解耦**:合并权 <1.5 时,现任持有权 ≥1 仍保持
    # (shop 半权蒸发不丢框架);翻转门 = 挑战者**持有权**领先现任 ≥1(纯 shop
    # 噪声翻不动),shop 半权只参与「谁最先过启动线」。
    if counts[fw] < 1.5:
        if current and current in owned and owned[current] >= 1:
            return current   # 现任手里有真件,保持(防闪烁回退 '')
        return ''
    if current and current in owned and current in counts:
        _challenger_owned = owned[fw]
        if owned[current] >= _challenger_owned and owned[current] >= 1:
            return current   # 现任持有未被挑战者持有领先 → 保持
    return fw


# ===== 定型信号管线(用户指导:最终 comp 的选择信号从开局积累,双轨并行) =====
# 信号源(按到达顺序):简报词缀 → P1 投资策略 → P1 投资环境 → P1 商店供给倾向
# → 最晚 P2-3 投资策略/环境(最后一次有经济量转型的节点,之后锁死)。
# 权重 = 该信号对 comp 强度的证据量(词缀克制/定义型 augment 是强证据)。

#: 信号源 → 权重(**仅遥测/诊断**,信号定型门已退役,累积分
# 只进 sess_commit_scores 遥测与 leader 囤牌倾向参考,禁作决策门消费;
# 权重为相对证据强度的经验排序,未证——不进任何行为判据)。
SIGNAL_WEIGHTS: dict[str, float] = {
    'briefing_affix': 1.5,      # 开局词缀(克制/加成直接改 comp 强度;mechanics_fit 主分)
    'invest_strategy': 2.0,     # 投资策略(定义型如黑塔纪元 affinity≥0.9 = 资源入口级)
    'invest_env': 1.0,          # 投资环境(方向性弱于策略)
    'shop_supply': 0.5,         # 商店供给(每回合弱证据,持续累积)
    # 用户指导:节点随机奖励同属信号——补给(钻/装备/角色)/遭遇(三态选卡)/
    # 奖励节点(晶矿/礼盒)给的东西都是「本局走向」的证据(如补给送 Fate 角色
    # = 命运圣杯线信号;遭遇给装备 = 装备系线倾向)
    'supply_reward': 0.8,       # 补给节点产出(角色/装备定向)
    'encounter_reward': 0.6,    # 遭遇选卡(策略/装备)
    'bonus_reward': 0.4,        # 奖励节点随机产出(最弱证据)
}

# (信号定型门已退役 2026-09-04,「未证即退役」裁定:旧
# COMMIT_SIGNAL_THRESHOLD=5.0 / COMMIT_MIN_T=7 为拍死值(原注释只证了
# 「不能更低」),且 ready() 全库零生产消费(定型权威 = cw_intention.committed_authority:plane≥2 / 意向状态机 locked /
# p1_pair 非空)。连同退役:t_of 全局轮序换算(唯一消费 = 已删 ready 的
# 轮门,P2=7 节点按 9 计的量纲失真一并消失)。CommitSignals 保留为
# 遥测累积器,SIGNAL_WEIGHTS 见上注。)


class CommitSignals:
    """选卡信号累积器(局级,挂 StrategySession;接线残留的
    遥测载体,定型门退役后**无决策消费**)。

    各信号源到达时调 ``add``(源名 + 该源的 comp 分贡献),累积到每条线;
    ``leader`` 给当前倾向(仅遥测/判读参考)。定型权威 =
    ``cw_intention.committed_authority``(plane≥2 / 意向状态机 locked /
    p1_pair 非空),本类不参与定型判定(旧信号定型门已退役,见模块注)。
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
        """当前信号领先的线(名, 分);空返 None。仅遥测。"""
        if not self.scores:
            return None
        comp, sc = max(self.scores.items(), key=lambda kv: kv[1])
        return comp, sc


def transition_score(char_id: str, faction: str, framework: str = '') -> float:
    """买牌评分用:角色在过渡框架中的价值(carry>partial>drop;同框架+阵营契合加成)。

    framework 传当前选定的过渡框架('仙舟'/'列车'),同框架牌加成;
    ''(未定框架)= **预囤模式**(见框架件就囤,持有最多者启动;MC 2000 局
    实证预囤把启动率从 0.5% 拉到 99.9% @r1.4)。散件恒低分。
    预囤只对 **carry/partial**(囤了围绕它走);drop 档返 0
    (应急件,囤了 P1 末就卖 = 浪费金,与 recipe 追买口径一致)。
    阵营兜底(列车件池实为 8 人:配方羁绊
    计数认阵营池,买牌只认 TRANSITION_PACK 策展 2 人——饮月(仙舟+列车
    双阵营)/星期日/瓦尔特被当散件放过,「列车×4」难凑齐):
    阵营命中当前框架但不在策展同框架 → partial 级分(羁绊计数有贡献)。
    """
    ent = TRANSITION_PACK.get(char_id)
    fw_facs = FRAMEWORK_FACTIONS.get(framework, ()) if framework else ()
    _fac_hit = bool(framework and _char_has_faction(char_id, fw_facs))
    if ent is None:
        base = 0.6 if _fac_hit else 0.0   # 非在册但阵营命中=partial 级(阵营兜底)
    else:
        fw, tier = ent
        base = {'carry': 1.0, 'partial': 0.6, 'drop': 0.4}.get(tier, 0.3)
        if not framework and tier == 'drop':
            return 0.0   # 预囤模式不囤 drop(预囤只囤 carry/partial)
        if fw == framework:
            base += 0.3   # 同框架集中
        elif fw == '通用':
            base += 0.15  # 通用插件次之
        elif _fac_hit:
            base += 0.2   # 阵营兜底:在册他框架件但阵营命中当前框架
        # fw != framework 且 framework=''(预囤):base 保持档位分(囤任何框架件)
    if faction in FRAMEWORK_FACTIONS.get(framework, ()):
        base += 0.2
    return base


def _char_has_faction(char_id: str, fw_facs) -> bool:
    """角色注册表阵营/流派与框架阵营有交集(阵营兜底;纯查表)。"""
    from sr_od.application.currency_war.data.cw_chars import get_char
    c = get_char(char_id) if char_id else None
    if c is None:
        return False
    return bool((set(c.factions) | set(c.flows)) & set(fw_facs or ()))
