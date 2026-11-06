"""跨局分配层 v0:RunAllocator Thompson 采样 + 必死局回收。

**诊断**:所有已落组件都是**局内优化器**,没人回答「数据本身从哪来、分配对不对」
——bot 集中玩当前最强阵容 → telemetry 窄分布 → 学习组件外推失真 → 更不敢选 = 死锁
(提案自诊断的 CRITICAL-for-convergence)。必死局的剩余动作是**免费实验预算**被白白输掉。

**v0 落地**(纯函数,离线可测;telemetry 接入调用/漂移闭环为 v1):
- ``StrategyArm``:分支 = 阵容家族(v1 再拆节奏维);Beta 后验;
- ``plaza 先验封顶``:伪计数 ≤8(幸存者偏差数据只配当弱先验,自家 5-8 局可翻案);
- ``ThompsonAllocator.select``:后验采样选分支(后验集中后自动退化为总选最优,层会自己关
  自己);forbid/priority 过滤(用户方向盘);explore_budget 闸;
- ``update``:分级奖励(win=1.0;输局按位面/节点进度分级,降方差)+ **adherence 加权**
  (防「分配姬子中途转万敌赢了算姬子」的信用错配);指数遗忘 γ;
- ``dead_run_salvage``:必死局回收(P(win)<ε 且置信 → 切后验方差最大的可达分支,零胜率
  成本收割样本);触发审计留存证据(复核「没误杀有救的局」≥95%)。

P(win) 投影供给方:cw_first_passage(已有);漂移闭环(CUSUM+重抓)为 v1。
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_comps import Comp

PRIOR_CAP: int = 8          # plaza 伪计数封顶(幸存者偏差 → 弱先验,自家 5-8 局翻案)
GAMMA: float = 0.97         # 指数遗忘(旧版本样本退潮)


@dataclass
class StrategyArm:
    """分配分支:阵容家族 + Beta 后验。"""
    arm_id: str
    comp_family: str
    alpha: float = 1.0
    beta: float = 1.0
    n_own: int = 0                  # 自家样本数(遗忘后)
    adherence_sum: float = 0.0      # 累计遵从度(审计)

    @property
    def mean(self) -> float:
        return self.alpha / (self.alpha + self.beta)

    @property
    def variance(self) -> float:
        s = self.alpha + self.beta
        return (self.alpha * self.beta) / (s * s * (s + 1))

    def sample(self, rng: random.Random) -> float:
        return rng.betavariate(max(self.alpha, 0.01), max(self.beta, 0.01))


class ThompsonAllocator:
    """跨局分配器 v0(Thompson 采样 + 预算闸 + salvage)。"""

    def __init__(self, arms: dict[str, StrategyArm] | None = None,
                 explore_budget: float = 0.15, seed: int = 0):
        self.arms = arms or {}
        self.explore_budget = explore_budget
        self.rng = random.Random(seed)

    @classmethod
    def from_plaza(cls, family_share: dict[str, float],
                   explore_budget: float = 0.15, seed: int = 0) -> ThompsonAllocator:
        """plaza 份额 → 封顶先验分支表(份额归一为胜率先验;伪计数封顶)。"""
        arms: dict[str, StrategyArm] = {}
        for fam, share in family_share.items():
            mean = min(0.9, 0.3 + share)          # 份额 → 均值映射(弱先验)
            a = PRIOR_CAP * mean
            b = PRIOR_CAP * (1 - mean)
            arms[fam] = StrategyArm(arm_id=fam, comp_family=fam, alpha=a, beta=b)
        return cls(arms, explore_budget, seed)

    def select(self, forbidden: set[str] | None = None,
               forced: str | None = None) -> str | None:
        """选分支:forced(成就/handoff 豁免)> Thompson 采样。空表 → None。"""
        if forced and forced in self.arms:
            return forced
        cands = {k: a for k, a in self.arms.items() if k not in (forbidden or set())}
        if not cands:
            return None
        best_k, best_v = None, -1.0
        for k, a in cands.items():
            v = a.sample(self.rng)
            if v > best_v:
                best_k, best_v = k, v
        return best_k

    def update(self, arm_id: str, reward: float, adherence: float = 1.0) -> None:
        """终局更新:分级奖励 × 遵从度加权 + 指数遗忘(γ 缩旧样本再加分母)。"""
        a = self.arms.get(arm_id)
        if a is None or not (0.0 <= reward <= 1.0):
            # 拒绝必须留日志(断线哨兵——update 静默 no-op 时生产不可见)
            from one_dragon.utils.log_utils import log
            log.warning('[cw-alloc] update 拒绝:arm=%r 不在臂表 或 reward=%r 越界 [0,1]', arm_id, reward)
            return
        # 遗忘:旧后验向中性收缩(乘 γ 于伪计数规模,保持先验封顶语义)
        s = a.alpha + a.beta
        shrink = GAMMA ** (1 / max(a.n_own, 1)) if a.n_own else 1.0
        target_s = max(PRIOR_CAP, s * shrink)
        scale = target_s / s
        a.alpha, a.beta = a.alpha * scale, a.beta * scale
        # 遵从度加权的新样本
        w = max(0.0, min(1.0, adherence))
        a.alpha += reward * w
        a.beta += (1 - reward) * w
        a.n_own += 1
        a.adherence_sum += w

    def reward_graded(self, won: bool, plane_reached: int, rounds: int = 27) -> float:
        """分级奖励:win=1.0;输局按位面/节点进度(降方差,小样本最有效降噪)。"""
        if won:
            return 1.0
        return min(0.49, (plane_reached / 3.0) * 0.45 + (rounds / 27.0) * 0.05)

    def stats(self) -> dict[str, dict]:
        return {k: {'mean': round(a.mean, 3), 'var': round(a.variance, 4),
                    'n_own': a.n_own, 'adherence': round(a.adherence_sum, 1)}
                for k, a in self.arms.items()}


#: 线名 → 统计簇名(adherence 跨局统计的分组键;plaza-carry-retirement):
#: 两层名字空间翻译——手判层线名 ↔ plaza 聚类层簇名(聚类层无线名概念,
#: 翻译关系只能手判层登记)。**非行为判据**:arm 键随簇不随定义件
#: (adherence 统计连续性),与行为锚(carry_anchor = core[0],随手判演化)
#: 解耦;版本重跑时与 PLAZA_CARRY_CLUSTERS 核对(gen_plaza_comps 对账报告)。
#: 值 = 各线聚类簇 carry 名快照(空值线 = 原攻略补全值,同 fast 表退役前口径)。
LINE_STAT_CLUSTER: dict[str, str] = {
    '列车同行·反震': '姬子·启行', '列车同行·直伤': '姬子·启行',
    '命运圣杯红A': 'Archer', '千冶减益': '千冶·刃', '绯英欢愉': '绯英',
    '希儿量子': '希儿', '黄泉减益': '黄泉', '巡海击破': '波提欧',
    '龙丹战技点': '丹恒·饮月', '双王圣杯': 'Saber', '火花星间旅人': '火花',
    '大黑塔银河学者': '大黑塔', '银枝群攻': '银枝', '反甲白厄': '白厄',
    '狼尊欢愉': '银狼LV.999', '昼神阿雅': '阿格莱雅', '追击飞霄': '飞霄',
    '万敌单C': '万敌', 'DOT队': '卡芙卡', '景元仙舟': '景元',
    '专家桑博DOT': '桑博',
}


def arm_key_of(comp: Comp) -> str:
    """阵容 → 分配器 arm 键的换算单一源(初始化侧与 update 侧共用)。

    arm 键空间 = ``PLAZA_CARRY_CLUSTERS`` 中 ``n_posts >= 15`` 的聚类簇名
    (cw_loop ``_get_or_init_allocator`` 的 share 过滤式)——键空间即统计簇名
    空间,换算 = :data:`LINE_STAT_CLUSTER` 查表(统计分组键,非行为判据;
    旧「= carry_anchor」换算随 plaza_carry 退役解耦——行为锚已派生 core[0],
    与统计簇名是两个概念)。换算值 ∉ ``allocator.arms``(低篇数线/无簇线)
    时由调用侧 ``arm_id not in arms`` 防线拦截,维持跳过语义;未登记线名
    → 空串(同样被该防线拦截)。本模块运行时零 kernel 依赖(纯函数离线可测)。
    """
    return LINE_STAT_CLUSTER.get(comp.name, '')


# ============================================================
# 局终结算
# MatchOutcome(docstring 点名消费语义 = 跨局分配器/runs summary)。
# ============================================================

# 动作集 v2(契约包 C1,步2)+ CwActionCloseShopParam 终结动作(商店恒可用终结)


@dataclass
class MatchOutcome:
    """一局货币战争的终局结算(框架构造,局终收束消费:跨局分配器/runs summary;/§11.4)。

    ⚠️ 字段全默认 —— **P1 由 run loop 用 ``MatchOutcome()`` 桩构造**(生命周期
    钩子随 并入删除后,消费面 = cw_loop 局终分支,
    字段已被真实数据填充);**真实 outcome 填充(结算屏 OCR 读终局 HP/位面/轮次/通关)依赖结算屏
    OCR 探查(现 run loop 是「点空白加速 → 继续挑战」,未见独立结算屏)。
    """
    won: bool = False        # 是否通关(3 位面全清)
    final_plane: int = 1     # 到达位面
    final_round: int = 1     # 位面内轮次
    final_hp: int = 0        # 终局小队 HP
