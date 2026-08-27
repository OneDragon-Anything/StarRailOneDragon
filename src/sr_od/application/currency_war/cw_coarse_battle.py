"""战斗结果粗参数两态模型(sim 校准层;胜负感知,禁高斯)。

**模型形态**:战斗类节点(battle/encounter/boss)的 HP 变化不再是
Δ池经验分布采样,而是两态离散采样:

- **胜态**(killed=True):小回血 ``WIN_CAP``(+2,池语料主型);
  P(win) 按 节点×rung 查找表取(Laplace 平滑 α=1;高位 rung 单元
  经 plaza 先验 Beta 收缩,见 :func:`injected_win_p`);
- **败态**:伤害从节点级离散值直方采样(保留 Δ值谱的离散/双峰
  结构),battle/encounter 按 rung 线性均值匹配偏移取整;终态
  ``hp_after = max(1, hp_before − damage)``(吸收态地板);
- **boss 败局钳制**:按 hp_before 条件化——≤``BOSS_CLAMP_HP_CUT``
  时以 ``BOSS_CLAMP_P_LOW`` 归 1,>该值不钳(冻结语料 0/36:敌伤
  上限 ≈36 够不着高 HP)。禁止与 hp_before 无关的独立抽签形态
  (会与地板公式叠加成双重钳制,期望钳制率恒超目标,已在原型
  回测中实证废弃)。

**参数来源**(禁来源混写,逐项标注;全部出自生产 replay 冻结语料
417 条战斗类差分的聚类稳健拟合与经验分布,机器可读版 = 拟合产物
``fit_results.json`` 的 ``two_state_model``/``win_rate_table_injected``,
拟合脚本与冻结语料同目录存档):

- 败局伤害直方/均值系数/boss 钳制参数/胜率 rung0-1 = 纯遥测;
- 胜率 rung2-3 的 ``p_data`` = 遥测平滑值,交付口径 = plaza 先验
  Beta 收缩后的 ``p_injected``(:func:`injected_win_p` 运行时重算,
  机制锁 = 本函数,值锁 = 测试仓粗模型锁);
- ``P_PRIOR_HIGH_RUNG``(0.35,存在性下限)= plaza(V4.4 高难帖
  结构统计,防记忆化:只取成型档统计量不含名单);
- ``DIFFICULTY_MULT_*`` = 机制先验(旧口径估算,未核):实现但
  默认关闭——未核先验禁用,跨难度判断在核验前不得引用本模型
  难度维;A8 基准内乘子恒 1。

**引擎开关**(:data:`BATTLE_ENGINE_MODE`):``'coarse'``(默认,
战斗类节点走本模型)/ ``'delta'``(Δ池经验分布,保留作对照臂——
粗模型转正需先过验证批:与 Δ池基线三率对拍)。reward/supply
节点不在本模型范围,两模式下均仍走 Δ池(实现批裁决保留)。
"""
from __future__ import annotations

import random

# ── 引擎开关 ────────────────────────────────────────────────────
#: 'coarse'=本模型(默认);'delta'=Δ池经验分布(对照臂,验证批用)。
#: monkeypatch 本属性可切臂;切换只影响 battle/encounter/boss。
BATTLE_ENGINE_MODE: str = 'coarse'

# ── 常量(设计写死)────────────────────────────────────────────
WIN_CAP: int = 2            # 胜态小回血封顶(池语料主型)
CLAMP_HP: int = 1           # 败局 HP 吸收态(语料 hp_after==1 簇)
SMOOTH_ALPHA: float = 1.0   # 胜率表 Laplace 平滑(已并入 p_data 交付值)
P_PRIOR_HIGH_RUNG: float = 0.35   # plaza 先验:存在性下限,不随 rung 递增
PLAZA_SHARE_MAX: float = 0.25     # 先验在单元后验的份额上限(硬顶)
ALPHA_CAP: float = 12.0           # 先验等效样本数绝对上限(硬顶)

# 难度乘子(未核先验,默认关闭——开关进本模块,核验后才允许置 True)
DIFFICULTY_MULT_ENABLED: bool = False
DIFFICULTY_MULT_PER_POINT: float = 1.052   # 旧口径估算,未核
DIFFICULTY_REF: int = 108                  # A8 基准(语料 95% 行恒此值)

# ── 胜率查找表(节点×rung;n=遥测样本数,p_data=遥测平滑胜率)──
# rung0/1 遥测样本充足,不注入(份额 0);rung≥2 由 injected_win_p
# 做 Beta 收缩。冲突裁决:先验与遥测冲突 → 遥测赢(p_prior 只给
# 平坦存在性下限,不外推抬高位——语料实证胜率沿 rung 非单调)。
_WIN_TABLE: dict[str, dict[int, tuple[int, float]]] = {
    'battle': {0: (106, 0.009), 1: (116, 0.356),
               2: (47, 0.306), 3: (9, 0.273)},
    'encounter': {0: (24, 0.038), 1: (36, 0.026),
                  2: (15, 0.235), 3: (2, 0.25)},
    'boss': {0: (11, 0.077), 1: (35, 0.027),
             2: (13, 0.133), 3: (3, 0.2)},
}

# ── 败局伤害直方(节点级离散值;钳制行伤害被截断观测,不入直方)──
_LOSS_HIST: dict[str, dict[int, int]] = {
    'battle': {-64: 1, -43: 1, -42: 1, 1: 7, 3: 3, 4: 9, 5: 10, 6: 5,
               7: 2, 8: 19, 9: 11, 10: 6, 11: 18, 12: 6, 13: 74, 14: 1,
               15: 9, 17: 3, 18: 3, 19: 4, 20: 2, 21: 4, 23: 2, 46: 1,
               84: 1, 88: 1},
    'encounter': {4: 1, 5: 1, 6: 4, 7: 1, 8: 4, 9: 7, 10: 10, 15: 1,
                  17: 1, 18: 1, 22: 1, 24: 11, 26: 7, 28: 15, 45: 2,
                  83: 2},
    'boss': {3: 1, 11: 2, 12: 1, 13: 2, 14: 4, 30: 1, 32: 5, 34: 11,
             36: 8},
}

# 败局伤害 rung 线性拟合(聚类稳健):伤害 = intercept + slope·rung;
# 均值匹配偏移 = fit(rung) − 直方池均值(boss 斜率 CI 含 0 退常数,
# 不做均值匹配,直方原样采样)。(intercept, slope, pooled_mean)
_LOSS_FIT: dict[str, tuple[float, float, float]] = {
    'battle': (11.32, -0.37, 11.07),
    'encounter': (24.32, -4.53, 20.71),
}

# boss 败局钳制(按 hp_before 条件化;机制见模块 docstring)
BOSS_CLAMP_HP_CUT: float = 35.0
BOSS_CLAMP_P_LOW: float = 0.929


def injected_win_p(node: str, rung: int) -> float:
    """单元胜率交付口径:遥测平滑值 + 高位单元 plaza Beta 收缩。

    机制(主从写死:遥测主源,plaza 只进 rung≥2 薄弱区):
    ``p ← (α·0.35 + n·p_data) / (α + n)``,
    ``α = min(ALPHA_CAP, n·PLAZA_SHARE_MAX/(1−PLAZA_SHARE_MAX))``
    → 先验份额 α/(α+n) 恒 ≤25%,任何单元不允许先验主导;
    rung<2 或无样本单元原样返回 p_data(份额 0)。
    """
    cell = _WIN_TABLE[node].get(int(rung))
    if cell is None:
        cell = _WIN_TABLE[node][min(max(int(rung), 0), 3)]
    n, p_data = cell
    if int(rung) < 2 or n <= 0:
        return p_data
    alpha = min(ALPHA_CAP, n * PLAZA_SHARE_MAX / (1 - PLAZA_SHARE_MAX))
    # 交付口径 = 拟合产物同精度(三位小数):运行时重算值与拟合
    # 交付值逐单元全等(契约锁的单一数值源,不留双精度漂移)。
    return round((alpha * P_PRIOR_HIGH_RUNG + n * p_data) / (alpha + n), 3)


def prior_share(node: str, rung: int) -> float:
    """单元先验份额(α/(α+n);披露/测试锁用,rung<2 恒 0)。"""
    n = _WIN_TABLE[node].get(min(max(int(rung), 0), 3), (0, 0.0))[0]
    if int(rung) < 2 or n <= 0:
        return 0.0
    alpha = min(ALPHA_CAP, n * PLAZA_SHARE_MAX / (1 - PLAZA_SHARE_MAX))
    return alpha / (alpha + n)


def sample_battle_delta(node: str, rung: int, hp_before: int,
                        rng: random.Random, *,
                        difficulty: int | None = None) -> int:
    """战斗类节点单次结算:返回 hp_after − hp_before(两态采样)。

    :param node: 'battle' | 'encounter' | 'boss'(reward/supply 不辖)
    :param rung: 结算时点成型度(单一源 = cw_sim._settle_rung)
    :param hp_before: 结算前 HP(钳制/地板的条件量)
    :param difficulty: 敌方难度数值(乘子默认关闭,见模块头;None=未读)
    """
    r = min(max(int(rung), 0), 3)
    if rng.random() < injected_win_p(node, r):
        return WIN_CAP
    raw_hist = _LOSS_HIST[node]
    dmg = float(rng.choices(list(raw_hist.keys()),
                            weights=list(raw_hist.values()), k=1)[0])
    if node == 'boss':
        # 钳制按 hp_before 条件化:低 HP 才会被敌伤越过得归吸收态;
        # 高 HP 行不钳(语料 0/36)。钳制路径不经难度乘子(吸收态
        # 非伤害档)。
        if hp_before <= BOSS_CLAMP_HP_CUT and rng.random() < BOSS_CLAMP_P_LOW:
            return CLAMP_HP - hp_before
    else:
        i, s, pooled = _LOSS_FIT[node]
        # rung 线性均值匹配:直方采样 + (fit(rung) − 池均值),取整,
        # 伤害地板 1(直方含负值档 = 语料挑战/增益行,交付口径原样保留)
        dmg = max(1, round(dmg + (i + s * r) - pooled))
    if DIFFICULTY_MULT_ENABLED and difficulty is not None \
            and int(difficulty) != DIFFICULTY_REF:
        dmg = max(1, round(dmg * DIFFICULTY_MULT_PER_POINT
                           ** (int(difficulty) - DIFFICULTY_REF)))
    return max(CLAMP_HP, hp_before - int(dmg)) - hp_before
