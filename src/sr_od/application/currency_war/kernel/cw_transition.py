"""定型信号累积器(遥测载体)。

**玩法理解单一源**:双轨(过渡→终局)/ 过渡框架 / 定型判定的玩法知识归
``docs/game/currency_war/research/`` 知识树(过渡体系 → transitions.md 与
transition_combos.md;位面演化定量 → stage_transitions.md;打法纪律 →
已退役口述登记簿(2026-10-16 删))——**改本模块前先读并对表**,理解变更先改文档
(防实现漂移)。

**退役申报(统一保护集迭代 changes/2026-10-15-unified-protection-set
design.md §2.4)**:本模块原承载的策展过渡包判据族(框架件计数
``_framework_counts``/框架选定 ``pick_framework``/买牌打分
``transition_score``)判据数据源 = TRANSITION_PACK 策展名单与
carry/partial/drop 档位标签,符号删除后为死码,随符号删除(全仓
grep 零生产消费方,仅测试直挂);框架成员现算单一源 =
``knowledge/cw_line_facts.framework_members``,方向选定 = 终局
候选-锁制定(12 号篇)。保留面 = ``CommitSignals`` 信号累积器
(SIGNAL_WEIGHTS 加权;仅遥测/诊断,定型权威 =
``cw_intention.committed_authority``)。
"""
from __future__ import annotations

# ===== 定型信号管线(用户指导:最终阵容的选择信号从开局积累,双轨并行) =====
# 信号源(按到达顺序):简报词缀 → P1 投资策略 → P1 投资环境 → P1 商店供给倾向
# → 最晚 P2-3 投资策略/环境(最后一次有经济量转型的节点,之后锁死)。
# 权重 = 该信号对阵容强度的证据量(词缀克制/定义型 augment 是强证据)。

#: 信号源 → 权重(**仅遥测/诊断**,信号定型门已停用,累积分
# 只进 sess_commit_scores 遥测,禁作决策门消费;
# 权重为相对证据强度的经验排序,未证——不进任何行为判据)。
SIGNAL_WEIGHTS: dict[str, float] = {
    'briefing_affix': 1.5,      # 开局词缀(克制/加成直接改阵容强度;mechanics_fit 主分)
    'invest_strategy': 2.0,     # 投资策略(定义型如黑塔纪元 affinity≥0.9 = 资源入口级)
    'invest_env': 1.0,          # 投资环境(方向性弱于策略)
    'shop_supply': 0.5,         # 商店供给(每回合弱证据,持续累积)
    # 用户指导:节点随机奖励同属信号——补给(钻/装备/角色)/遭遇(三态选卡)/
    # 奖励节点(晶矿/礼盒)给的东西都是「本局走向」的证据(如补给送 Fate 角色
    # = 命运圣杯线信号;遭遇给装备 = 装备系线倾向)
    'supply_reward': 0.8,       # 补给节点产出(角色/装备定向)
    'encounter_reward': 0.6,    # 遭遇选卡(策略/装备)
    'bonus_reward': 0.4,        # 随机产出(最弱证据)
}

# (信号定型门已停用 2026-09-04,「未证即停用」裁定:旧
# COMMIT_SIGNAL_THRESHOLD=5.0 / COMMIT_MIN_T=7 为拍死值(原注释只证了
# 「不能更低」),且 ready() 全库零生产消费(定型权威 = cw_intention.committed_authority:plane≥2 / 意向状态机 locked /
# p1_pair 非空)。连同停用:t_of 全局轮序换算(唯一消费 = 已删 ready 的
# 轮门,P2=7 节点按 9 计的量纲失真一并消失)。CommitSignals 保留为
# 遥测累积器,SIGNAL_WEIGHTS 见上注。)


class CommitSignals:
    """选卡信号累积器(局级,挂 StrategySession;接线残留的
    遥测载体,定型门停用后**无决策消费**)。

    各信号源到达时调 ``add``(源名 + 该源的阵容分贡献),累积到每条线,
    累积分仅作遥测判读(原当前倾向读口已随死代码清偿移除)。定型权威 =
    ``cw_intention.committed_authority``(plane≥2 / 意向状态机 locked /
    p1_pair 非空),本类不参与定型判定(旧信号定型门已停用,见模块注)。
    """

    def __init__(self) -> None:
        self.scores: dict[str, float] = {}

    def add(self, source: str, comp_scores: dict[str, float]) -> None:
        """累积一个信号源的阵容分贡献(源权重 × 归一化分)。"""
        w = SIGNAL_WEIGHTS.get(source, 0.0)
        if w <= 0 or not comp_scores:
            return
        mx = max(comp_scores.values()) or 1.0
        for comp, s in comp_scores.items():
            self.scores[comp] = self.scores.get(comp, 0.0) + w * (s / mx)
