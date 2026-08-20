"""货币战争 · 战力表判断层(redesign §4.1;Phase A Day 1)。

**判断层,手维护**(数据层 cw_power_table_data.py 由生成器产出勿手编——
两层架构同 gen_plaza_comps.py ADR-0150 模式)。

职责(redesign §4.1 Phase A 范围):
  1. 三级回退查询:精确(羁绊+人口)→ 降人口维(同羁绊任意人口)→
     降位面粒度仍由调用侧(位面内节点不查表——Phase A 查询语义
     降级:redesign §11,只在位面边界 boss 节点权威判定);
  2. 分层保守系数(r216 实证标定):reactive ×2.0 / burst ×1.2 /
     action ×0.8(等风险反推;Step 0 精标前的初值);
  3. 证据等级:强(精确命中)/粗(降维)/miss。

边界(诚实声明,同 redesign):
  - 词条维未入;核心在场/星级维 Phase A 未用(旧遥测几乎无覆盖,
    r214);
  - 幸存者偏差单向;保守系数吸收作者-试用练度差;
  - 版本过滤 4.4(生成器侧)。

常量名(附录 A):CONSERVATIVE_FACTOR_*(分驱动型三档)/
POWER_EXACT_MIN(精确阈值)/POWER_COARSE_MIN(降维阈值)。"""
from __future__ import annotations

from sr_od.application.currency_war.cw_power_table_data import POWER_ENTRIES

# ===== 分层保守系数(r216 等风险反推;判断层常量,Step 0 精标) =====
CONSERVATIVE_FACTOR_REACTIVE: float = 2.0   # 受击流:假阳 14.6% 最高
CONSERVATIVE_FACTOR_BURST: float = 1.2      # 大招流:8.8%
CONSERVATIVE_FACTOR_ACTION: float = 0.8     # 行动流:4.2%(下限守卫)

# ===== 阈值(篇数;乘保守系数后判「过」) =====
POWER_EXACT_MIN: int = 5    # 精确命中的最小验证篇数
POWER_COARSE_MIN: int = 8   # 降维命中的最小(更高——粗证据要求更多)

#: 驱动型 → 保守系数(判断层映射;调用侧传 drive_type)
_DRIVE_FACTOR: dict[str, float] = {
    'reactive': CONSERVATIVE_FACTOR_REACTIVE,
    'burst': CONSERVATIVE_FACTOR_BURST,
    'action': CONSERVATIVE_FACTOR_ACTION,
    # 未知驱动型取最保守(不因数据缺而放松——同 action 下限精神)
    'unknown': CONSERVATIVE_FACTOR_REACTIVE,
}

#: 证据等级(查询返回)
STRONG = 'strong'    # 精确命中且过阈
COARSE = 'coarse'    # 降维命中且过阈(粗证据)
MISS = 'miss'        # 无证据/未过阈


def check(bonds: str, pop: int, phase: str,
          drive_type: str = 'unknown') -> tuple[str, int, int]:
    """战力查询(三级回退的前两级;位面内降级由调用侧控制)。

    Args:
        bonds: 羁绊组合键(与生成器同口径:≥2 档,人数降序+名字序)
        pop: 人口(前后排合计)
        phase: P1/P2/P3
        drive_type: reactive/burst/action/unknown(选保守系数)

    Returns:
        (证据等级, 命中篇数, 命中人口):等级 STRONG/COARSE/MISS;
        STRONG 时命中人口=pop;COARSE 时=取到最强证据的人口
        (消费方据此判断人口距离——pop=1 吃到 pop=9 的证据属
        「距离大」的粗证据,建议 |pop-matched_pop|<=2 才信任);
        MISS 时命中人口=-1。
    """
    factor = _DRIVE_FACTOR.get(drive_type,
                               CONSERVATIVE_FACTOR_REACTIVE)
    # 级1: 精确(羁绊+人口)
    n = POWER_ENTRIES.get((bonds, pop, phase), 0)
    if n >= POWER_EXACT_MIN * factor:
        return STRONG, n, pop
    # 级2: 降人口维:同羁绊同位面任意人口的最大篇数(乐观侧
    # 聚合——S4 修正注释;人口距离的收紧由消费方按 matched_pop 做)
    best, best_pop = 0, -1
    for (b, p, ph), v in POWER_ENTRIES.items():
        if b == bonds and ph == phase and v > best:
            best, best_pop = v, p
    if best >= POWER_COARSE_MIN * factor:
        return COARSE, best, best_pop
    return MISS, n, -1


def bonds_key(trait_counts: dict[str, int]) -> str:
    """羁绊计数 dict → 规范键(与生成器/回放脚本同口径)。

    判断层也提供这个构造函数,消费方(决策循环)不必各自实现——
    键构造单源(第四轮对抗 F4 同族纪律)。
    """
    items = [(k, v) for k, v in trait_counts.items() if v >= 2]
    items.sort(key=lambda kv: (-kv[1], kv[0]))
    return '+'.join(f'{k}{v}' for k, v in items)
