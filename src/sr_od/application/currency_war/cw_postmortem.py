"""反事实复盘层 v0(redesign 14 号;ADR-0207):决策点筛选 + ex-ante 悔恨框架。

**诊断(14 号)**:实机局信息萃取率最低却是唯一 ground truth;轨迹五路落盘
(decisions/outcomes/runs/exec_events/exogenous)但没有「回到那一步重问一次」
的消费方式。发现「次优」(无 bug 无误执行,就是打得差)只有两条路:再打几局
(单局方差 >> 改进量)或人看日志(人工小时计)。

**v0 落地**(纯函数,离线;消费 telemetry 落盘数据):
- ``select_decision_points``:三类优先筛选(不可逆动作/候选分接近/高杠杆时刻),
  预算 top 5-15/局——不是每个决策都值得反事实;
- ``ex_ante_regret``:判决条件 = **决策时刻的信念**(非事后真值)——当时读数
  毒化下做的「对动作」不算悔恨(那是状态错,路由感知修复),只有「当时信念下
  换一个动作期望更好」才是策略悔恨(防事后偏差,14 号灵魂);
- ``below_noise_floor``:悔恨区间跨零/超宽 → 判「不可归因」(一等输出,防下游
  拿噪声当证据);层级聚合(单决策→类别→局)留 v1。

分支 rollout(CRN 对齐/前缀保真)挂 v1——需 02 outcome model 或
PerformanceTracker 近邻查表作战斗黑盒;数据基础(telemetry)本轮已全绿。
"""
from __future__ import annotations

from dataclasses import dataclass

# 不可逆动作集(07 号定义过;类名匹配 telemetry actions 的 __type__)
IRREVERSIBLE_ACTIONS: frozenset[str] = frozenset({
    'SellBench', 'ComposeEquip', 'DeployMove',   # 卖/合成/上阵位置
    'CommitComp', 'PivotComp',                    # 线承诺/转型
    'MegaStarBind', 'InvestPickPrism',            # 巨星绑定/棱彩投资
})

# 高杠杆时刻(node 转换类;exogenous.kind='node_enter' 的 detail 前缀)
HIGH_LEVERAGE_PREFIXES: tuple[str, ...] = (
    'boss_done', 'plane_enter', 'battle_done:boss',
)

TOP2_GAP_THRESHOLD: float = 0.10   # 候选分接近阈值(top-2 分差 < 此 = bot 自己不确定)
BUDGET_PER_RUN: int = 15           # 每局分支预算上限


@dataclass
class DecisionPoint:
    """一个值得反事实的决策点(筛选产物)。"""

    t: int                      # round_num
    category: str               # 'irreversible' / 'close_call' / 'high_leverage'
    action_type: str            # __type__ 或节点事件
    detail: str = ''
    score_gap: float | None = None   # close_call 时记录 top-2 分差


def select_decision_points(decisions: list[dict],
                           exogenous: list[dict] | None = None,
                           budget: int = BUDGET_PER_RUN) -> list[DecisionPoint]:
    """从 decisions.jsonl(run 级)筛反事实决策点。

    输入:telemetry decisions 行(dict;含 round_num/actions/candidate_scores)。
    三类优先:不可逆 > 分接近 > 高杠杆;同类保序(时间序);截预算。
    """
    out: list[DecisionPoint] = []
    for d in decisions:
        acts = d.get('actions') or []
        # ① 不可逆动作
        for a in acts:
            at = a.get('__type__', '') if isinstance(a, dict) else ''
            if at in IRREVERSIBLE_ACTIONS:
                out.append(DecisionPoint(
                    t=d.get('round_num', 0), category='irreversible',
                    action_type=at, detail=str(a)[:80]))
                break   # 一回合一个不可逆点即够
        # ② 候选分接近(top-2 分差 < 阈;bot 自己不确定)
        scores = d.get('candidate_scores') or {}
        if len(scores) >= 2:
            srt = sorted(scores.values(), reverse=True)
            gap = srt[0] - srt[1]
            if gap < TOP2_GAP_THRESHOLD:
                out.append(DecisionPoint(
                    t=d.get('round_num', 0), category='close_call',
                    action_type='candidate', score_gap=round(gap, 4)))
    # ③ 高杠杆(exogenous 事件)
    for e in exogenous or []:
        det = e.get('detail', '')
        if any(det.startswith(p) for p in HIGH_LEVERAGE_PREFIXES):
            out.append(DecisionPoint(
                t=e.get('round_num', 0), category='high_leverage',
                action_type='node_event', detail=det[:60]))
    # 优先级排序(不可逆 > 分接近 > 高杠杆),同类时间序;截预算
    prio = {'irreversible': 0, 'close_call': 1, 'high_leverage': 2}
    out.sort(key=lambda p: (prio[p.category], p.t))
    return out[:budget]


@dataclass
class RegretReport:
    """单决策点 ex-ante 悔恨判决(v0:框架 + 语义;rollout 值挂 v1)。"""

    t: int
    category: str
    verdict: str = 'pending'          # 'attributable' / 'below_floor' / 'state_error' / 'pending'
    ex_ante_regret: float | None = None   # E[最优备选] − E[实选](当时信念下)
    ci_width: float | None = None
    note: str = ''


def ex_ante_regret(belief_at_decision: dict,
                   actual_action_ev: float,
                   best_alternative_ev: float) -> RegretReport:
    """ex-ante 悔恨判决(14 号灵魂:条件=决策时刻信念,非事后真值)。

    belief_at_decision 含当时读数与置信度;读数低置信(hp_readable=False 等)下
    的「错动作」判 state_error(修感知),不进策略悔恨——防教策略层
    「基于错误读数做对动作」。
    """
    readable = belief_at_decision.get('hp_readable', True)
    regret = best_alternative_ev - actual_action_ev
    if not readable:
        return RegretReport(t=belief_at_decision.get('round_num', 0),
                            category='state_error',
                            note='信念毒化(hp_readable=False):路由感知修复,非策略悔恨')
    return RegretReport(t=belief_at_decision.get('round_num', 0),
                        category='attributable',
                        ex_ante_regret=round(regret, 4))


def below_noise_floor(regret: float, ci_width: float) -> bool:
    """悔恨低于噪声地板判(区间跨零或宽超悔恨量 → 不可归因,一等输出)。"""
    if ci_width <= 0:
        return False
    return (regret - ci_width / 2 <= 0 <= regret + ci_width / 2) or (ci_width > 2 * abs(regret))
