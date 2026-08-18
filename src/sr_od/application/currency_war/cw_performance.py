# 未验证(货币战争自主推进期代码,需进对应画面按 od-dev-screen-onboarding 等 skill review 重审后才能信)

"""货币战争 观测反馈层(PerformanceTracker + comp_viability + 死局检测;纯逻辑,可测,不碰游戏)。

**哲学(用户 2026-08-03 定调)**:观测驱动 ≠ 预测驱动。不建精确战斗模拟器(星铁战斗太复杂、
版本会迭代、维护不起)。人看的是"这回合掉了多少血 / boss 血条动没动"这个**结果**。故用
OCR ground-truth 反馈当"阵容强不强"的信号,不用预测模型。

review 历史:r5(修 9 个观测单点漏洞)+ r6(修 r5 扶正观测后引入的 4 个交互级漏洞)。
本模块用**测试锁住** r6 的 4 个交互行为(open-fold 污染 / boss None / pivot 归因 / 冷启动 None)。

设计依据:``docs/develop/currency_war/strategy/10_battle_and_enemies.md``。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from sr_od.application.currency_war.cw_comps import (
    ScoreContext,
    clamp,
    equip_fit,
    form_progress,
    mechanics_fit,
    weighted_mean,
)
from sr_od.application.currency_war.cw_state import GameState

if TYPE_CHECKING:
    from sr_od.application.currency_war.cw_comps import Comp


# ===== RoundOutcome(双侧观测;r6 F1/F3/F4)=====

@dataclass
class RoundOutcome:
    """一回合战斗的双侧观测结果(OCR 填;telemetry 采集)。

    - 自身侧(生存信号):hp_after + hp_confidence。
    - 敌方侧(击杀信号,r6 F3):enemy_hp_after / damage_dealt / killed —— 观测确证"打得动 boss 吗"。
      None = 游戏不暴露(阶段 4 实机确认);此时击杀能力靠 comp_viability 先验兜底。
    - comp_tag(r6 F4):打这关时的 target comp 名,obs 按 comp 归因(pivot 后旧 comp 降权而非全删)。
    - intentional_fold(r6 F1):本回合"故意输攒钱"态(plan fold 写入),排除污染 trend。
    """
    round_num: int
    plane: int
    node_type: str              # "普通战斗"/"精英"/"遭遇"/"boss"
    comp_tag: str               # 打这关时的 target comp 名
    intentional_fold: bool = False
    # —— 自身侧 ——
    hp_after: int = 0           # 结算后 HP(hp_delta = 本回合 − 上回合,差分)
    hp_confidence: float = 1.0  # OCR 置信度(0-1);<0.7 不进 trend(防 OCR 抖动)
    # —— 敌方侧(击杀信号;r6 F3)——
    enemy_hp_after: int | None = None
    damage_dealt: int | None = None
    killed: bool | None = None
    # —— 进度真值(2026-08-18 用户点破:「扣血=战斗失败,游戏内有记录」)——
    progress_delta: int | None = None   # 结算屏「挑战进度 ±N」带符号(赢 +2 / 输 -22);None=未读到
    # —— streak(连胜/连败;2026-08-11 结算「连胜×N」前缀=方向,fixture 核实)——
    streak: int = 0           # 带符号:+N 连胜 / -N 连败 / 0 无(结算 OCR 读;economy C 杠杆用)


# 节点类型 → 预期掉血(相对值;r6 F2 归一化用)。先验,历史 refine。
EXPECTED_DROP: dict[str, float] = {
    "普通战斗": 1.0, "精英": 1.5, "遭遇": 1.2, "boss": 3.0,
}
HP_CONFIDENCE_THRESHOLD: float = 0.7   # 低于此置信度的 outcome 不进 trend(r5)

# perf_for_comp 归一化:掉这么多(归一化)HP/回合 → perf=0(占位,待实玩校准)
HP_LOSS_FULL: float = 30.0


class PerformanceTracker:
    """跨回合观测追踪器(掉血 trend → maybe_pivot 信号;comp_viability 观测项)。

    ⚖️ 敌方侧死链已删(2026-08-16 review D4-D7):_update_required_damage(no-op 体)/
    set_required_damage+required_damage(无读者)/boss_kill_signal(无调用)/_last_hp_after
    (只写)——r6 F3 敌方观测整条从未接通(2026-08-18 二刀:原定归宿 19 号伤害账本
    cw_damage_ledger 属未接线孤儿批次,已删;伤害真值走结算屏 progress_delta/killed)。
    RoundOutcome 敌方三字段(enemy_hp_after/damage_dealt/killed)保留 dataclass 定义
    (telemetry OutcomeRecord 同 schema;enemy_hp/damage 仍未灌值)。
    """

    def __init__(self) -> None:
        self.history: list[RoundOutcome] = []

    def record(self, outcome: RoundOutcome) -> None:
        """存档(低置信 outcome 也存 history,但 recent_hp_loss_trend 跳过)。"""
        self.history.append(outcome)

    def _qualifying(self, comp_tag: str | None) -> list[tuple[RoundOutcome, float]]:
        """筛选可进 trend 的 outcome + 权重(r6 F1 排除 fold / F4 comp_tag 降权)。

        返回 [(outcome, weight)]:intentional_fold 全排;低置信全排;comp_tag 不匹配 ×0.3 降权(不全删)。
        """
        out: list[tuple[RoundOutcome, float]] = []
        for o in self.history:
            if o.intentional_fold:
                continue                       # r6 F1:排除"故意输"污染
            if o.hp_confidence < HP_CONFIDENCE_THRESHOLD:
                continue                       # 低置信不进 trend(防 OCR 抖动)
            w = 1.0
            if comp_tag is not None and o.comp_tag != comp_tag:
                w = 0.3                         # r6 F4:旧 comp 降权 0.3(不全删,保留信号)
            out.append((o, w))
        return out

    def recent_hp_loss_trend(self, comp_tag: str | None = None, window: int = 4) -> float | None:
        """归一化掉血 trend(r6 F2):hp_delta / expected_drop(node_type),全部样本进**同一条** trend。

        - 归一化而非完全划分(r6 F2):消除"打 boss 掉得多=我弱"偏差,又不丢样本/不震荡。
        - hp_delta = prev.hp_after − cur.hp_after(正=掉血);trend = 加权均值(delta / expected_drop[cur.node_type])。
        - 过滤:F1 排 fold / F4 comp_tag 降权 / 低置信跳过。
        - 冷启动(r6 F6):<2 qualifying outcome(无首个差分)→ None。
        """
        recent = self._qualifying(comp_tag)[-window:]
        if len(recent) < 2:
            return None                         # r6 F6:需 ≥2 outcome 才有首个差分
        sum_d_w = 0.0
        total_w = 0.0
        # recent[1:] 比 recent 短 1(成对差分),strict=False 容许不等长
        for (cur, w_cur), (prev, _w_prev) in zip(recent[1:], recent, strict=False):
            loss = prev.hp_after - cur.hp_after   # 正 = 掉了血
            ed = EXPECTED_DROP.get(cur.node_type, 1.0)
            sum_d_w += (loss / ed) * w_cur
            total_w += w_cur
        if total_w <= 0:
            return None
        return sum_d_w / total_w

    def is_losing_streak(self, comp_tag: str | None = None, window: int = 3) -> bool:
        """近 window 回合是否大掉血(trend > LOSING 阈值)。样本不足 → False。

        PvE 无每局 win/lose,只有 HP;"losing streak" = 持续高掉血。排除 fold。
        """
        trend = self.recent_hp_loss_trend(comp_tag=comp_tag, window=window)
        if trend is None:
            return False
        return trend > HP_LOSS_FULL * 0.6       # 掉血 > 18(归一化)算 streak(占位)

    def perf_for_comp(self, comp_tag: str, window: int = 6) -> float | None:
        """某 comp 的归一化表现(供 comp_viability 观测项;0..1,掉血少→高)。

        trend=None(冷启动/样本不足)→ None。trend 映射:0 掉血→1.0,HP_LOSS_FULL 掉血→0。
        pivot 后旧 comp 经 comp_tag 降权 ×0.3(r6 F4)。
        """
        trend = self.recent_hp_loss_trend(comp_tag=comp_tag, window=window)
        if trend is None:
            return None
        return clamp(1.0 - trend / HP_LOSS_FULL, 0.0, 1.0)


def star_achievement(comp: Comp, state: GameState) -> float:
    """核心角色星级达成(0..1;review round-4 HIGH-1:限时 AV 星级=输出,高星核心角色更强)。

    核心角色(``char_id in comp.core_chars``)在 bench/deployed 的 star —— 取 **bot 跟踪** star
    (``simulate`` 维护:buy=卡星 + 3合1 升星),非 ``read_star`` 旁路(read_star 是 offline/漂移校验,
    不进 bot 跟踪)。归一化:平均 star,1 星=0 / 2 星=0.5 / 3 星=1.0。无核心角色持有(早期未成型)→ 0。
    """
    if not comp.core_chars:
        return 0.0
    stars = [bc.star for bc in (*state.bench, *state.deployed)
             if bc.char_id in comp.core_chars]
    if not stars:
        return 0.0
    avg = sum(stars) / len(stars)
    return clamp((avg - 1.0) / 2.0, 0.0, 1.0)


# ===== comp_viability(评 current 已 commit comp;先验 + 观测 blend)=====

def comp_viability(comp: Comp, state: GameState, ctx: ScoreContext,
                   tracker: PerformanceTracker) -> float:
    """评 **current 已 commit** comp 的可行性(pivot/eval 用;先验 + 观测 blend,0..1)。

    与 cw_comps.comp_score 区别(拆双签名,r5):comp_score 评 **candidate 未 commit**(无观测);
    本函数评 **current 已打过几关**(有观测)。用已 commit 阵容的观测评未 commit candidate 是逻辑错位。

    - obs = tracker.perf_for_comp(comp.name);None(冷启动)→ obs_weight=0,纯先验。
    - rounds_seen 增 → obs_weight 升(0.1→0.5;观测越多越信观测)。
    - 先验 = 0.40 form + 0.25 equip + 0.20 mechanics + 0.15 star(动态归一 sum=1;不含 strength,已 commit 不看 research;
      star=核心角色星级达成,review round-4 HIGH-1 限时 AV 星级=输出;权重先验占位待 stage6 实跑校准)。
      动态归一(ADR-0107):equip/mechanics 无数据返 None → 剔除 + 权重重分配给 form/star(治死重常量地板)。
    """
    obs = tracker.perf_for_comp(comp.name)
    prior = weighted_mean([
        (0.40, form_progress(comp, state)),
        (0.25, equip_fit(comp, state)),
        (0.20, mechanics_fit(comp, ctx.mechanics)),
        (0.15, star_achievement(comp, state)),   # review round-4 HIGH-1:限时 AV 星级=输出
    ])
    if obs is None:
        return clamp(prior, 0.0, 1.0)   # 冷启动:纯先验(obs_weight=0)
    rounds_seen = sum(1 for o in tracker.history if o.comp_tag == comp.name)
    obs_weight = clamp(0.1 + 0.4 * (rounds_seen / 18), 0.1, 0.5)
    prior_weight = 1.0 - obs_weight
    return clamp(prior_weight * prior + obs_weight * obs, 0.0, 1.0)


# ===== 死局检测(三门;r5 + r6 F9)=====

DEAD_HP: int = 20             # HP 低于此 + trend 高 + 锁不住血节点 → 死局(占位,待 difficulty 校准)
TREND_THRESHOLD: float = HP_LOSS_FULL * 0.5   # trend 超此(归一化掉血 15+)算"锁不住血"
LOCK_NODES: set[str] = {"boss", "遭遇", "精英"}   # 锁不住血的节点类型(普通关可能锁血翻盘)


def is_run_dead(state: GameState, tracker: PerformanceTracker,
                next_node_type: str) -> bool:
    """死局检测(三门):HP 低 + trend 高 + 下回合是锁不住血节点 → True。

    r6 F9:"普通关可能锁血翻盘"依赖锁血机制 —— 阶段 4 实机确认货币战争是否有锁血;
    无则删 next_node_type 门,纯 HP+trend 两门。trend None(冷启动)→ False(不误判死)。
    """
    trend = tracker.recent_hp_loss_trend(window=3)
    if trend is None:
        return False
    if state.hp < DEAD_HP and trend > TREND_THRESHOLD:
        return next_node_type in LOCK_NODES
    return False
