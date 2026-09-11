"""货币战争战斗校准纯表(分包期 0b 单元6 自 cw_sim.py 两段式下沉,§3.3-②/§4.3)。

data 桶:只有表和常量,零包内依赖(§3.2 依赖矩阵);消费方 =
kernel/cw_battle_calib(校准函数族)、cw_sim(Δ池采样/结算)、
decision_v2.handoff(深度分桶)、测试锁。行段历史与语料 provenance
随原注释保留在条目上;数值变更须走标定批 + ADR,禁散改。
"""
from __future__ import annotations

from dataclasses import dataclass

# ===== P1 结算幅度常量(回退层;校准出处见各条注释,原址 cw_sim) =====

#: r1-r2 弱敌小胜
EARLY_WIN_DELTA: int = 2
#: 战斗胜时的轮结算
WIN_DELTAS: tuple[int, ...] = (2, 2, 0, -4)
#: r3 基础损
LOSS_BASE: float = 7.0
#: 每多一轮加重(r7≈-23 对齐观测;r259 二次校准 139 轮干净差分,原 3.5 系数
#: 低估后段流血 → 提到 4.0;方向分桶样本小且与「发牌差的队锁线晚」混杂,
#: ADR-0308 起胜负面不由方向门控,幅度层保留方向无关的轮次递增)
LOSS_PER_ROUND: float = 4.0
# 遭遇结算强度 = boss 档 × 1.15(用户口述:遭遇三四可比 boss 难;
# 遭遇一/二较温和 → 取均值系数,模拟无法读档位时的近似)
ENCOUNTER_MULT: float = 1.15
#: (方向建立轮上限, boss 基础损, 抖动幅度)
BOSS_BY_DIR_ROUND: tuple[tuple[int, float, float], ...] = (
    (2, 14.0, 8.0),
    (4, 22.0, 8.0),
    (6, 30.0, 8.0),
    (99, 36.0, 10.0),
)

# ===== 节点×轮次胜率阶梯(回退层胜负面单一源;ADR-0308,W31 实测) =====
# 来源:replay outcomes 语料 plane=1 & killed 非空 & board_before 非空
# = n=192(killed True 104 / False 88),按 (node_type, round) 统计的
# killed 胜率——W31 报告(`deep_read/W31_报告.md` §2,原始件已灭失
# (2026-09-12 清理))。替换旧拍脑袋胜负面:
#   battle  方向二元门控(方向已立→胜)——胜率从未按节点实测;
#   encounter 结构性恒败(p=0);
#   boss    rung 表 (0, 0, 0.25) + rung2 桶外推(ADR-0306,跨节点
#           外推边界已声明)。
# 逐轮实测:奖励轮 r1/r2/r8 全胜;battle r3 0.30 / r4 0.29;
# encounter r7 0.04;boss r9 0.05。未观测的 (node, round) 组合按
# 节点类型边际值兜底(``NODE_WIN_P_BY_TYPE``)。
# ⚠️ 数据边界(ADR-0308):语料全部来自旧策略(line_strategy)病局
# ——「六局同型败的镜像」,阶梯是旧策略在各种板面下的**边际**胜率,
# 不含成型度条件性(rung 维被压平);decision_v2 新策略语料攒够后
# **应重标本表**(届时遥测 board_before 补记角色名+星级,条件性才可标定)。
NODE_WIN_P_LADDER: dict[tuple[str, int], float] = {
    ('battle', 3): 0.30,
    ('battle', 4): 0.29,
    ('encounter', 7): 0.04,
    ('boss', 9): 0.05,
}
NODE_WIN_P_BY_TYPE: dict[str, float] = {
    'reward': 1.0,    # 零战力节点,实测 100% 胜
    'supply': 1.0,
    'battle': 0.29,
    'encounter': 0.04,
    'boss': 0.05,
}
# 胜时小额(与 reward/supply 的 EARLY_WIN_DELTA 同档;「大胜」
# 形态待样本后校准——W31 语料只有 killed 二值,无胜幅度分层)。
# ⚠️ P1 初始 HP=80 非 100(simulate_p1 `st.hp = 80`;批⑪ 自纠记档
# ——按 100 锚算 boss 损失会出伪影)。
BOSS_WIN_DELTA: int = 2

# ===== P2 战斗回退档(语料 `w151_p2/`:P2+ 战斗 1 胜 8 败;败掉血带
# 15-17;结算屏三项拆解 P2r1 实证 +2/-10/-15)。Δ池 plane=2 桶可及
# 时经验分布优先;缺桶走本带(ADR-0362)。=====
P2_BATTLE_WIN_P: float = 0.11
P2_LOSS_BAND: tuple[int, int] = (15, 17)


# ===== P2 战斗存活层参数化校准族(`w193_p2sim/`/ADR-0377) =====
# 结构:win_p = clip(p0 + β·form − γ·drift(round)),form=板面质量键
# (engines 数[deployed 口径,_settle_rung 同源]+level 折算+星级深度折算);
# 负=分段掉血带内均匀。**校准层(非真战斗机制)**,诚实边界:
# - 21 run 语料只够钉边界不够点估计 β——p0/β/γ 取保守值 + 敏感性带
#   扫描为裁决口径(修法在带端点一致翻正才裁「分布级」);
# - Δ池 plane=2 条件化(键 form×round,每桶 n≥5)留 Phase 3 自动让位;
# - 四常数族单一注入点=本 dataclass(A/B 与敏感性扫描同通道)。
# 掉血分段带校准来源(`w193_p2sim/calibrate_truth.py` 复跑,真值=
# 生产 replay plane=2 未删失差分;hp_after==1 为败北地板删失样本弃):
# battle_r1 (14,28) 进场首战 / battle_early (4,16) r2-r3 /
# battle_late (15,25) r4+ / encounter (9,18) / boss (21,26)。
# 胜率:p0=0.11 语料边际保守下沿;β 方向由胜例 board 强制为正、量级
# 未定 → 保守 0.04,敏感性主扫参;γ 弱(轮梯度未识别)→ 0.02。
# 星级分量(`w230_star_form/`/ADR-0401):star_depth=上场件 Σ(star−1)
# (全量口径,同 ADR-0399);engines=1 桶内 sd=0 → 0/8 胜,sd∈{1,2}
# → 3/15(0.20)——方向为正;sd≥3 零胜但 n≤4 不可辨 → 保守 0.5
# (一颗 2★ 折半台引擎)+ 敏感性端点 0/0.25/1.0。
@dataclass(frozen=True)
class P2CombatCalib:
    """P2 段战斗存活层参数族(`w193_p2sim/`/ADR-0377;单一注入点,A/B 同通道)。

    ``calibrated=False`` = 逐位回 `w157_p2/`/ADR-0362 行为(Δ池 plane=2 桶
    优先 + ``P2_BATTLE_WIN_P`` 恒值回退档)——A/B 回退对照臂。
    """

    #: 总开关:True=参数化校准层辖 plane≥2 战斗类结算(绕过 Δ池
    #: plane=2 合并采样——该路径被防饥饿守卫抹平条件性,ADR-0362
    #: 已判「假条件化」;Phase 3 桶键 form×round 到量后让位池采样)
    calibrated: bool = True
    #: 基础胜率(语料边际保守下沿)
    p0: float = 0.11
    #: form(板面质量键)系数:每单位 form 的胜率增量(敏感性主扫参)
    beta: float = 0.04
    #: 轮次漂移系数:敌人强度随轮增长(每轮 γ)
    gamma: float = 0.02
    #: 胜率钳制带
    win_p_clip: tuple[float, float] = (0.0, 0.5)
    #: form 键的 level 折算权重(form = engines + w·(level−6);
    #: engines=deployed 口径 _settle_rung 同源,0-4)
    form_level_weight: float = 0.25
    #: form 键的星级深度折算权重(`w230_star_form/`/ADR-0401:star_depth=上场件
    #: Σ(star−1) 全量口径,同 ADR-0399 HandoffSnapshot;core2/board_tier
    #: 的星级维胜率因果通道)。保守 0.5,敏感性端点 0/0.25/1.0。
    form_star_weight: float = 0.5
    #: level 折算基准(P2 常见进场 level 6)
    form_level_base: int = 6
    #: 事件金双臂(W186 §3:K3 零样本——'p1'=复用 P1 表[打标未校准],
    #: 'zero'=P2 段事件金归零;敏感性双臂,rng 流两臂同耗保配对)
    event_gold: str = 'p1'
    #: 分段掉血带(败场;带内均匀采样)
    band_battle_r1: tuple[int, int] = (14, 28)
    band_battle_early: tuple[int, int] = (4, 16)
    band_battle_late: tuple[int, int] = (15, 25)
    band_encounter: tuple[int, int] = (9, 18)
    band_boss: tuple[int, int] = (21, 26)
    #: 胜场结算值(语料胜例 Δ=+2)
    win_delta: int = 2


#: 默认参数族(模块单一实例;敏感性/A/B 经 simulate_p1 的 p2_combat 注入)
P2_COMBAT_DEFAULT = P2CombatCalib()

# ===== Δ 池分桶守卫常数(单一源,期 0b 对齐:原 cw_sim._BUCKET_MIN_N 与
# cw_sim_checks._POOL_BUCKET_MIN_N 值同步维护(双源),收拢本表) =====

#: 板深分桶宽(桶键 = depth // 宽 × 宽;消费 = live_delta_for /
#: handoff 深度分桶 / 池指纹输入——改值=采样语义变,指纹随变)
DEPTH_BUCKET_W: int = 3
#: 防饥饿守卫门槛(ADR-0268 批③ F1:battle 桶6 n=1 恒 -11,把跨深度 6
#: 边界的策略臂系统性伪惩罚;命中的桶 n<门槛 → 邻桶合并降级采样)
BUCKET_MIN_N: int = 5
