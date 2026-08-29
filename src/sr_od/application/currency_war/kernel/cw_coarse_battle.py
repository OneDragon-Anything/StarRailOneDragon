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
  时以 ``BOSS_CLAMP_P_LOW`` 归 1,>该值不钳(冻结语料 0/33:敌伤
  上限 ≈36 够不着高 HP)。禁止与 hp_before 无关的独立抽签形态
  (会与地板公式叠加成双重钳制,期望钳制率恒超目标,已在原型
  回测中实证废弃)。

**位面维(P1 先行)**:三张常数表 + 钳制参数按位面键化
(``{节点: {位面: <结构>}}``),plane 1 = 冻结语料拟合现值逐档原样,
plane 2 = :data:`_P2_ALIAS` 显式别名指向 plane 1(不拷贝数据——
P2 未采样,别名即已知偏差的机器可读声明;量化边界见别名注释)。
P1 数值未变仅结构变,结构版本见 :data:`COARSE_CALIB_VERSION`
(进 sim 台账 manifest 披露)。结算入口 :func:`sample_battle_delta`
的 ``plane`` 参数默认 1,旧调用零漂移。

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

# ── 胜率查找表(节点×位面×rung;n=遥测样本数,p_data=遥测平滑胜率)──
# rung0/1 遥测样本充足,不注入(份额 0);rung≥2 由 injected_win_p
# 做 Beta 收缩。冲突裁决:先验与遥测冲突 → 遥测赢(p_prior 只给
# 平坦存在性下限,不外推抬高位——语料实证胜率沿 rung 非单调)。
# 位面维(P1 先行):plane 1 = 冻结语料拟合现值(P1 主导语料,
# sim-实机三方一致载体);plane 2 = _P2_ALIAS 显式别名指向 plane 1
# ——P2 未采样,别名即已知偏差的机器可读声明,不拷贝数据。
_WIN_TABLE: dict[str, dict[int, dict[int, tuple[int, float]]]] = {
    'battle': {1: {0: (106, 0.009), 1: (116, 0.356),
                   2: (47, 0.306), 3: (9, 0.273)}},
    'encounter': {1: {0: (24, 0.038), 1: (36, 0.026),
                      2: (15, 0.235), 3: (2, 0.25)}},
    'boss': {1: {0: (11, 0.077), 1: (35, 0.027),
                 2: (13, 0.133), 3: (3, 0.2)}},
}

# ── 败局伤害直方(节点级离散值;钳制行伤害被截断观测,不入直方)──
# 位面维同 _WIN_TABLE(P1=现值逐档,P2=别名;含 battle 灾难档 84/88
# 与负值档,交付口径原样保留)。
_LOSS_HIST: dict[str, dict[int, dict[int, int]]] = {
    'battle': {1: {-64: 1, -43: 1, -42: 1, 1: 7, 3: 3, 4: 9, 5: 10, 6: 5,
                   7: 2, 8: 19, 9: 11, 10: 6, 11: 18, 12: 6, 13: 74, 14: 1,
                   15: 9, 17: 3, 18: 3, 19: 4, 20: 2, 21: 4, 23: 2, 46: 1,
                   84: 1, 88: 1}},
    'encounter': {1: {4: 1, 5: 1, 6: 4, 7: 1, 8: 4, 9: 7, 10: 10, 15: 1,
                      17: 1, 18: 1, 22: 1, 24: 11, 26: 7, 28: 15, 45: 2,
                      83: 2}},
    'boss': {1: {3: 1, 11: 2, 12: 1, 13: 2, 14: 4, 30: 1, 32: 5, 34: 11,
                 36: 8}},
}

# 败局伤害 rung 线性拟合(聚类稳健):伤害 = intercept + slope·rung;
# 均值匹配偏移 = fit(rung) − 直方池均值(boss 斜率 CI 含 0 退常数,
# 不做均值匹配,直方原样采样)。(intercept, slope, pooled_mean)
# 位面维同上(P1=现值,P2=别名)。
_LOSS_FIT: dict[str, dict[int, tuple[float, float, float]]] = {
    'battle': {1: (11.32, -0.37, 11.07)},
    'encounter': {1: (24.32, -4.53, 20.71)},
}

# P2 层别名声明:P2 未采样 → 全节点显式指向 plane 1 同表(单一取表
# 入口 _node_table 消费)。已知偏差量化边界(继承的现状,非本结构
# 引入):W357 regate(池锚 7af81977)——boss 事件均损 +4.57 hp、
# boss 钳制率 P2 段 −38.81 pp、encounter 钳制率 P2 段 −6.19 pp;
# 未来 P2 语料积累后逐节点换入 plane 2 槽位即收口,不触 P1。
_P2_ALIAS: dict[str, int] = {'battle': 1, 'encounter': 1, 'boss': 1}


def _node_table(table: dict, node: str, plane: int) -> dict:
    """位面取表单一入口:plane 直查,未声明位面按别名链落到 plane 1。

    :param table: 三张常数表之一({节点: {位面: <现结构>}})
    :param node: 'battle' | 'encounter' | 'boss'
    :param plane: 位面段(1=P1;2=P2 走别名;其余未声明位面同 P2 兜底)
    """
    planes = table[node]
    return planes.get(int(plane)) or planes[_P2_ALIAS[node]]


def _win_cell(node: str, rung: int, plane: int) -> tuple[int, float]:
    """胜率表单元取值(含 rung 钳位;injected_win_p/prior_share 共用)。"""
    cell = _node_table(_WIN_TABLE, node, plane).get(int(rung))
    if cell is None:
        cell = _node_table(_WIN_TABLE, node, plane)[min(max(int(rung), 0), 3)]
    return cell


# boss 败局钳制(按 hp_before 条件化;机制见模块 docstring)
# 位面维:P1 = 现值;P2 = 别名同值(声明:P2 落入可钳区事件率本身
# 有 W357 G6-boss 已知偏差,钳制参数层暂随 P1 外推)。
BOSS_CLAMP_HP_CUT: float = 35.0
BOSS_CLAMP_P_LOW: float = 0.929


def _boss_clamp_params(plane: int) -> tuple[float, float]:
    """钳制参数位面入口:P2 未采样,别名 plane 1 现值。"""
    _ = int(plane)   # 位面槽位就位:未来 P2 换参在此分派
    return (BOSS_CLAMP_HP_CUT, BOSS_CLAMP_P_LOW)


# 校准结构版本(DESIGN §验证):P1 数值不变的纯结构位面化即置 2;
# 进 sim 台账 manifest(runner.write_batch_ledger)披露,回归批脚本
# 头部按本常量断言,防跨版本对比污染。数值重校准(任一 P1 层真值
# 变动)必须再递增。
COARSE_CALIB_VERSION: int = 2


def injected_win_p(node: str, rung: int, plane: int = 1) -> float:
    """单元胜率交付口径:遥测平滑值 + 高位单元 plaza Beta 收缩。

    机制(主从写死:遥测主源,plaza 只进 rung≥2 薄弱区):
    ``p ← (α·0.35 + n·p_data) / (α + n)``,
    ``α = min(ALPHA_CAP, n·PLAZA_SHARE_MAX/(1−PLAZA_SHARE_MAX))``
    → 先验份额 α/(α+n) 恒 ≤25%,任何单元不允许先验主导;
    rung<2 或无样本单元原样返回 p_data(份额 0)。
    :param plane: 位面段(默认 1 保旧调用零漂移;P2 走别名)
    """
    n, p_data = _win_cell(node, rung, plane)
    if int(rung) < 2 or n <= 0:
        return p_data
    alpha = min(ALPHA_CAP, n * PLAZA_SHARE_MAX / (1 - PLAZA_SHARE_MAX))
    # 交付口径 = 拟合产物同精度(三位小数):运行时重算值与拟合
    # 交付值逐单元全等(契约锁的单一数值源,不留双精度漂移)。
    return round((alpha * P_PRIOR_HIGH_RUNG + n * p_data) / (alpha + n), 3)


def prior_share(node: str, rung: int, plane: int = 1) -> float:
    """单元先验份额(α/(α+n);披露/测试锁用,rung<2 恒 0)。

    :param plane: 位面段(默认 1 保旧调用零漂移;P2 走别名)
    """
    n = _win_cell(node, min(max(int(rung), 0), 3), plane)[0]
    if int(rung) < 2 or n <= 0:
        return 0.0
    alpha = min(ALPHA_CAP, n * PLAZA_SHARE_MAX / (1 - PLAZA_SHARE_MAX))
    return alpha / (alpha + n)


def sample_battle_delta(node: str, rung: int, hp_before: int,
                        rng: random.Random, *,
                        difficulty: int | None = None,
                        plane: int = 1) -> int:
    """战斗类节点单次结算:返回 hp_after − hp_before(两态采样)。

    :param node: 'battle' | 'encounter' | 'boss'(reward/supply 不辖)
    :param rung: 结算时点成型度(单一源 = cw_battle_calib._settle_rung)
    :param hp_before: 结算前 HP(钳制/地板的条件量)
    :param difficulty: 敌方难度数值(乘子默认关闭,见模块头;None=未读)
    :param plane: 位面段(默认 1 = 旧调用零漂移;P2 段结算点透传
        st.plane,P1 数值/P2 别名两层取表见模块头位面维说明)
    """
    r = min(max(int(rung), 0), 3)
    if rng.random() < injected_win_p(node, r, plane):
        return WIN_CAP
    raw_hist = _node_table(_LOSS_HIST, node, plane)
    dmg = float(rng.choices(list(raw_hist.keys()),
                            weights=list(raw_hist.values()), k=1)[0])
    if node == 'boss':
        # 钳制按 hp_before 条件化:低 HP 才会被敌伤越过得归吸收态;
        # 高 HP 行不钳(语料 0/33)。钳制路径不经难度乘子(吸收态
        # 非伤害档)。
        clamp_cut, clamp_p = _boss_clamp_params(plane)
        if hp_before <= clamp_cut and rng.random() < clamp_p:
            return CLAMP_HP - hp_before
    else:
        i, s, pooled = _node_table(_LOSS_FIT, node, plane)
        # rung 线性均值匹配:直方采样 + (fit(rung) − 池均值),取整,
        # 伤害地板 1(直方含负值档 = 语料挑战/增益行,交付口径原样保留)
        dmg = max(1, round(dmg + (i + s * r) - pooled))
    if DIFFICULTY_MULT_ENABLED and difficulty is not None \
            and int(difficulty) != DIFFICULTY_REF:
        dmg = max(1, round(dmg * DIFFICULTY_MULT_PER_POINT
                           ** (int(difficulty) - DIFFICULTY_REF)))
    return max(CLAMP_HP, hp_before - int(dmg)) - hp_before
