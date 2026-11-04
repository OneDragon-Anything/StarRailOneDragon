"""货币战争 观测反馈层(RoundOutcome + PerformanceTracker;纯逻辑,可测,不碰游戏)。

**哲学(用户 2026-08-03 定调)**:观测驱动 ≠ 预测驱动。不建精确战斗模拟器(星铁战斗太复杂、
版本会迭代、维护不起)。人看的是"这回合掉了多少血 / boss 血条动没动"这个**结果**。故用
OCR ground-truth 反馈,不用预测模型。

设计依据:``strategy-docs/15_observation_multisource_arbitration.md``(观察多源仲裁篇)。
"""
from __future__ import annotations

from dataclasses import dataclass

# ===== RoundOutcome(双侧观测;r6 F1/F3/F4)=====

@dataclass
class RoundOutcome:
    """一回合战斗的双侧观测结果(OCR 填;telemetry 采集)。

    - 自身侧(生存信号):hp_after + hp_confidence。
    - 敌方侧(击杀信号,r6 F3):enemy_hp_after / damage_dealt / killed —— 观测确证"打得动 boss 吗"。
      None = 游戏不暴露(阶段 4 实机确认)。
    - comp_tag(r6 F4):打这关时的 target 阵容名,obs 按阵容归因(pivot 后旧阵容降权而非全删)。
    - intentional_fold(r6 F1):本回合"故意输攒钱"态(plan fold 写入)。
    """
    round_num: int
    plane: int
    node_type: str              # "普通战斗"/"精英"/"遭遇"/"boss"
    comp_tag: str               # 打这关时的 target 阵容名
    intentional_fold: bool = False
    # —— 自身侧 ——
    hp_after: int | None = 0    # 结算后 HP(hp_delta = 本回合 − 上回合,差分);
    # None 仅收束终局行携带(cw_loop._write_terminal_outcome_row,不发 hp 真值)
    hp_confidence: float = 1.0  # OCR 置信度(0-1)
    # —— 敌方侧(击杀信号)——
    enemy_hp_after: int | None = None
    damage_dealt: int | None = None
    killed: bool | None = None
    # —— 进度真值(2026-08-18 用户点破:「扣血=战斗失败,游戏内有记录」)——
    progress_delta: int | None = None   # 结算屏「挑战进度 ±N」带符号(赢 +2 / 输 -22);None=未读到
    # —— streak(连胜/连败;2026-08-11 结算「连胜×N」前缀=方向,fixture 核实)——
    streak: int | None = 0    # 带符号:+N 连胜 / -N 连败 / 0 无(结算 OCR 读;economy C 杠杆用);
    # None 仅收束终局行携带(不发 streak 真值,镜像 hp_after 口径)
    # —— 结算三项遥测(docs/develop/currency_war/strategy/05_observation.md §3.1(迭代工作面原稿 SETTLE_OCR_DESIGN §3;P15 脱删失/P12 幅度授权真值通道)——
    # progress_fill_ratio = 挑战进度条填充率 [0,1](幅度绝对值通道;±N 浮字是符号+
    # 增量真值,两通道同帧并记互为交叉核对);damage_base/damage_unfinished_progress =
    # 掉血说明 tooltip 两分量(进页瞬窗内捕获,miss=None 删失显式可辨,勿造假值);
    # damage_breakdown_visible = tooltip 是否在场(False+两分量 None=不在场,
    # True+None=在场但解析失败,两态可分)。条不可见/面板不在场 → None。
    # heal_longline = tooltip 第三行「长线作战」(战斗回血,恒 ≥0;实机实证
    # 常量 +2/场,口述+80→82→84 连胜轨迹)——链差(净变化)含它、
    # 两掉血分量不含,是「tooltip 幅度 = 链差 + 2」系统偏移的机制项
    #;此前解析器已读但 schema 缺字段被静默丢弃。
    progress_fill_ratio: float | None = None
    damage_base: int | None = None
    damage_unfinished_progress: int | None = None
    damage_breakdown_visible: bool = False
    heal_longline: int | None = None
    # —— 遭遇选档观测扩字段(E-2):difficulty_node = 结算快照取该节点最近
    # 备战帧现场真读敌方难度读数值(live 位为门,无现场读 → None;遭遇行取值随读点
    # 定案两变体,未定案期装 None);encounter_tier = 遭遇战决策落点难度档
    # (经验档层其五/六正证据的行内通道;普通战斗行恒 None)。
    difficulty_node: float | None = None
    encounter_tier: int | None = None
    # —— 收束终局行标记:仅对局收束终局行携带('stopped'/'abandoned'),
    # 普通结算行恒 ''(字段语义与读端消费边界 =
    # telemetry.schema.OutcomeRecord.match_result 注)。
    match_result: str = ""


class PerformanceTracker:
    """跨回合观测追踪器(回合结果存档面)。

    ⚖️ 敌方侧无生产写端:_update_required_damage(no-op 体)/
    set_required_damage+required_damage(无读者)/boss_kill_signal(无调用)/_last_hp_after
    (只写)等死链已清——敌方观测整条从未接通,伤害真值走结算屏
    progress_delta/killed。
    RoundOutcome 敌方三字段(enemy_hp_after/damage_dealt/killed)保留 dataclass 定义
    (telemetry OutcomeRecord 同 schema;enemy_hp 仍未灌值,damage_dealt 已由结算屏「数据统计」面板求和灌值)。
    """

    def __init__(self) -> None:
        self.history: list[RoundOutcome] = []

    def record(self, outcome: RoundOutcome) -> None:
        """存档一条回合观测。"""
        self.history.append(outcome)


#: OCR 置信度门槛(结算覆盖写端 cw_screen_battle_wait 消费:低于此值的
#: hp_after 不落状态容器真值,防 OCR 抖动污染 hp 结算覆盖)。
HP_CONFIDENCE_THRESHOLD: float = 0.7
