"""认知主权层 v0(09 号提案;ADR-0167;2026-08-16):认知地图 + 主权混合。

**诊断(09 号)**:每个学习/估值组件都自带局部「低置信→回退」补丁(01 检索置信低回退手判/
02 超支撑集退先验/04 不可逆门/06 弱先验不入表/07 低置信回退静态表)——五处各自为政、二值
开关、阈值语义不同,与 04 号诊断的观察噪声补丁族同病(没人认领**模型无知**这支)。且手写
eval 从不被治理(它只是行为已知的兜底,不是无条件正确的兜底)。

**v0 落地**(纯函数 + 离线可测):
- ``CompetenceMap``:认知地图(comp 家族 × 阶段 × HP 档 × 装备到位度 四维粗格子约百格;
  密度 = plaza 先验 + 自家后验;残差 = 分桶估值误差);格子数与样本量挂钩(数据解锁细化);
- ``sovereignty(cell)``:连续主权权重(高密度 → 学习组件全权;低密度 → 混合回退手写/保守);
  **密度只降置信、不降估值**(未知 ≠ 差,只是不稳——幸存者偏差防线);
- ``irreversible_gate(advantage, cell, stakes)``:**认知安全边际**——不可逆动作在低密度格
  需要更大期望优势;显著优势任何格放行(边际内保守、显著优势放行,防全局僵死);
- ``exploration_bonus(cell, surplus)``:富余局面探索价(低覆盖且离当前线一步之遥 → 正偏置;
  stakes 高 → 负);
- ``off_map(cell)``:off-map 分诊标记([cw!] 日志独立维度;复盘新增「输在已知区还是未知区」轴)。

与 04 号正交:04 的门管「读得准不准」(感知置信),本层管「这类局面懂不懂」(覆盖置信);
与 05 号互补:死局收全价样本,本层活局富余边际收零头样本。
"""
from __future__ import annotations

from dataclasses import dataclass, field

# 格子四维(comp 家族 / 阶段 / HP 档 / 装备到位度档)的档定义
PHASE_BUCKETS: tuple[str, ...] = ('P1', 'P2', 'P3')
HP_BUCKETS: tuple[tuple[int, int], ...] = ((0, 30), (30, 60), (60, 101))
EQUIP_BUCKETS: tuple[str, ...] = ('裸装', '部分', '成型')

DENSITY_VALID: int = 5          # 每格 ≥N 样本才计有效密度
LOW_DENSITY: int = 10           # 低于此 → 主权连续混合
ADV_MARGIN: float = 1.5         # 不可逆动作安全边际:优势须 ≥ margin × (1 + 无知度)


def cell_id(comp_family: str, plane: int, hp: int, equip: str) -> str:
    """决策状态 → 格子 id(四维粗粒度;数据量解锁细化的锚)。"""
    ph = PHASE_BUCKETS[min(max(plane, 1), 3) - 1]
    hpb = next(f'{lo}-{hi}' for lo, hi in HP_BUCKETS if lo <= hp < hi)
    eq = equip if equip in EQUIP_BUCKETS else '部分'
    return f'{comp_family}|{ph}|{hpb}|{eq}'


@dataclass
class CellStat:
    """单格统计:密度(plaza 先验 + 自家后验)与分桶残差。"""
    prior_n: int = 0            # plaza 投影先验(784 篇三阶段)
    own_n: int = 0              # 自家 telemetry join 后验
    residual: float = 0.0       # 该格引擎估值误差均值(绝对值归一)

    @property
    def n(self) -> int:
        # 自家样本权重 2×(亲历 > 攻略先验);plaza 幸存者偏差 → 先验只算半权
        return self.own_n * 2 + self.prior_n


@dataclass
class CompetenceMap:
    """认知地图 + 主权分配(v0 纯函数;telemetry join 为 v1 数据灌入口)。"""

    cells: dict[str, CellStat] = field(default_factory=dict)

    def observe(self, cid: str, *, prior: bool = False, residual: float | None = None) -> None:
        c = self.cells.setdefault(cid, CellStat())
        if prior:
            c.prior_n += 1
        else:
            c.own_n += 1
        if residual is not None:
            # 滚动均值
            k = (c.own_n + c.prior_n)
            c.residual = (c.residual * (k - 1) + abs(residual)) / max(k, 1)

    def density(self, cid: str) -> int:
        c = self.cells.get(cid)
        return c.n if c else 0

    def sovereignty(self, cid: str) -> float:
        """学习组件主权权重 [0,1]:高密度 → 1(学习全权);低密度 → 连续混合回退。

        密度只降置信、不降估值(幸存者偏差防线:人类没走过的格子 ≠ 不可行)。
        残差恶化 → 同格降权(手写引擎同样被治理的入口)。
        """
        c = self.cells.get(cid)
        n = c.n if c else 0
        if n >= LOW_DENSITY * 3:
            w = 1.0
        elif n <= DENSITY_VALID:
            w = 0.2
        else:
            w = 0.2 + 0.8 * (n - DENSITY_VALID) / (LOW_DENSITY * 3 - DENSITY_VALID)
        if c is not None and c.residual > 0.3:   # 高残差格:引擎(含手写)让位保守
            w *= max(0.3, 1.0 - c.residual)
        return round(min(1.0, w), 3)

    def irreversible_gate(self, advantage: float, cid: str, stakes: str = 'normal') -> tuple[bool, str]:
        """不可逆动作认知安全边际:低密度格需更大优势;显著优势任何格放行。

        advantage = 期望优势(估值差,归一);stakes ∈ normal/low_hp/boss_pre。
        """
        n = self.density(cid)
        ignorance = max(0.0, 1.0 - n / (LOW_DENSITY * 3))
        stakes_mult = {'normal': 1.0, 'low_hp': 1.3, 'boss_pre': 1.2}.get(stakes, 1.0)
        need = ADV_MARGIN * (1 + ignorance) * stakes_mult
        if advantage >= 2.5:   # 显著优势放行(防全局僵死)
            return True, f'显著优势({advantage:.1f})放行'
        if advantage >= need:
            return True, f'优势 {advantage:.1f} ≥ 边际 {need:.1f}'
        return False, f'优势 {advantage:.1f} < 认知边际 {need:.1f}(低密度格 n={n},stakes={stakes})'

    def exploration_bonus(self, cid: str, surplus: bool) -> float:
        """富余探索价:低覆盖且富余 → +0.1~+0.3(买数据);stakes 高(surplus=False)→ 负。"""
        n = self.density(cid)
        if not surplus:
            return -0.1          # 低血/boss 前:探索项为负
        if n < LOW_DENSITY:
            return 0.3           # 低覆盖零头样本最值钱
        if n < LOW_DENSITY * 2:
            return 0.15
        return 0.0

    def off_map(self, cid: str) -> bool:
        """off-map 判定([cw!] 日志独立维度;复盘「已知区 vs 未知区」分诊轴)。"""
        return self.density(cid) < DENSITY_VALID
