"""装备组合规划器 v0(07 号提案;ADR-0164;2026-08-16)。

**诊断(07 号)**:装备感知端全建(read_equips/合成图 K7 闭合),决策端是全系统最薄层——
四接缝全是**当帧静态排序**(equip_fit 比例分/decide_supply 固定优先级/箱选卡 _material_value
静态表/穿戴槽序),共同盲区:**没有任何一处持有装备库存的序贯视角**(不看剩余渠道/不看存活
comp/不看合成不可逆/不看装备在 comp 间可迁移性)。而 plaza 把装备定为 A8 最高杠杆。

**v0 落地**(三维先行:获取选卡/合成时机/转型壁垒;分配维保守化待 live 验回收机制):
- ``EquipPlanner.value_of_take(item, ...)``:组件期权价值 = 对存活 comp 候选集与剩余渠道的
  期望边际(同一组件随局面变:已持 2 轮滑鞋+阿雅 target=皮靴临门;target 未定=期权全开);
- ``should_exercise(a, b, ...)``:合成行权判断(立即战力需求 vs 期权保留 —— 「风暴潮前不合
  小件」「2 鞋+阿雅 → 立即合皮靴」的 plaza 行为锚从求解产生,非手写序列);
- ``equip_overlap_matrix()``:comp×comp 装备重叠(转型物理壁垒,转型成本 += 沉没的不可共享
  装备价值;派生量,从 COMP_LIBRARY 算出不手写)。

接缝:全部现有接缝零新建入口;planner 异常 → 回退现状静态规则(同 03 降级模式)。
纯函数 + 离线可测;expectimax v1 升级位注释标留。
"""
from __future__ import annotations

from sr_od.application.currency_war.cw_comps import COMP_LIBRARY
from sr_od.application.currency_war.cw_synthesis import (
    CROSS_RECIPES,
    SELF_RECIPES,
    cross_components,
    self_advance,
    synthesize_target,
)

# 组件通用性先验(配方引用数,_material_value 同源;期权价值的收缩先验)
_BASE_VERSATILITY: dict[str, int] = dict.fromkeys(set(SELF_RECIPES.values()), 0)
for _adv, (x, y) in CROSS_RECIPES.items():
    _BASE_VERSATILITY[x] = _BASE_VERSATILITY.get(x, 0) + 1
    _BASE_VERSATILITY[y] = _BASE_VERSATILITY.get(y, 0) + 1
for _b in SELF_RECIPES.values():
    _BASE_VERSATILITY[_b] = _BASE_VERSATILITY.get(_b, 0) + 1


class EquipPlanner:
    """装备序贯规划器 v0(期权价值/行权判断/转型壁垒)。"""

    def __init__(self, candidates: list[str] | None = None):
        """candidates = 存活 comp 名列表(None = 全库)。target 已锁 → 单元素列表。"""
        self.candidates = [c for c in COMP_LIBRARY if c.name in (candidates or [c.name])]

    # --- 主张 1.1:组件期权价值 ---
    def value_of_take(self, item: str, owned: dict[str, int],
                      channels_left: int = 3) -> float:
        """基础件/进阶件的获取期望边际(v0 语义,序贯期望的静态近似)。

        - target 单锁(comp 候选 1 个):价值 = 该 comp 的 key_equips 覆盖度提升 × 紧急度
          (缺口大 × 渠道少 → 高;target 已齐 → ≈0);
        - 候选多元:价值 = 对各 comp 的边际期望 + 通用期权(versatility 先验 × 未锁度);
        - 进阶件直接按 key_equips 命中计。
        channels_left:剩余获取渠道数(supply 节点/箱/球;渠道少 → 稀缺加成)。
        """
        if not self.candidates:
            return _BASE_VERSATILITY.get(item, 0) * 0.1
        k = len(self.candidates)
        total = 0.0
        scarcity = 1.0 + max(0, (3 - channels_left)) * 0.2   # 渠道少 → 每次机会更值钱
        for comp in self.candidates:
            keys = list(comp.key_equips)
            if item in keys:
                need = keys.count(item)
                have = owned.get(item, 0)
                gap = max(0, need - have)
                total += (gap / max(need, 1)) * 1.0
                continue
            # 基础件:能否作为该 comp key_equips 的组件
            for adv in keys:
                cc = cross_components(adv)
                if cc and item in cc:
                    total += 0.5 * max(0, 1 - owned.get(adv, 0))
                    break
                sb = self_advance(adv)
                if sb == item:
                    total += 0.5 * max(0, 1 - owned.get(adv, 0))
                    break
        # 未锁度:候选越多,通用期权权重越高(组件通往多条路)
        unlock = min(1.0, (k - 1) / 4.0)
        total /= max(1, min(k, 5))
        total += unlock * _BASE_VERSATILITY.get(item, 0) * 0.08
        return total * scarcity

    # --- 主张 1.2:合成行权判断 ---
    def should_exercise(self, a: str, b: str, owned: dict[str, int],
                        urgent_power: bool = False) -> tuple[bool, str]:
        """两基础件是否合成(行权)v0 规则:

        - 产物是某存活 comp 的 key_equips 命脉件且该 comp 缺它 → **行权**(立即战力/进度);
        - 产物不在任何候选 key 集(通用件)且 urgent_power(掉血压力)→ 行权;
        - 组件本身是另一高价值路的临门组件(如 2 轮滑鞋+皮靴候选在)→ **持有**
          (「风暴潮前不合小件」的行为锚);
        - 其余 → 持有(期权保留)。
        返回 (行权?, 理由)。
        """
        target = synthesize_target(a, b)
        if target is None:
            return False, '无可合成配方'
        for comp in self.candidates:
            if target in comp.key_equips and owned.get(target, 0) < list(comp.key_equips).count(target):
                return True, f'{target} 是 {comp.name} 命脉件且缺口'
        if urgent_power:
            in_any = any(target in c.key_equips for c in self.candidates)
            if not in_any:
                return True, f'{target} 通用件+战力紧急'
        # 持有检查:组件是否其他命脉路的临门件
        for comp in self.candidates:
            for adv in comp.key_equips:
                cc = cross_components(adv)
                if cc and a in cc and b not in cc and owned.get(a, 0) <= 1:
                    return False, f'{a} 是 {comp.name}·{adv} 的组件,持有保留期权'
                sb = self_advance(adv)
                if sb in (a, b) and owned.get(sb, 0) <= 2:
                    return False, f'{sb} 是 {comp.name}·{adv} 的自配组件,持有'
        return False, '行权价值不足,持有(期权保留)'


def equip_overlap_matrix() -> dict[tuple[str, str], float]:
    """comp×comp 装备重叠(主张 1.3:转型物理壁垒;派生量,从 COMP_LIBRARY 算)。

    重叠 = 共享 key_equips 的价值加权 Jaccard(交集/并集, multiplicities 计)。
    消费:maybe_pivot 转型成本 += 沉没的不可共享装备价值。
    """
    names = [c.name for c in COMP_LIBRARY]
    out: dict[tuple[str, str], float] = {}
    by_comp = {c.name: list(c.key_equips) for c in COMP_LIBRARY}
    for i, x in enumerate(names):
        for y in names[i + 1:]:
            sx, sy = by_comp[x], by_comp[y]
            inter = sum(min(sx.count(e), sy.count(e)) for e in set(sx) | set(sy))
            union = len(sx) + len(sy)
            ov = inter / union if union else 0.0
            out[(x, y)] = round(ov, 3)
    return out


def pivot_equip_cost(from_comp: str, to_comp: str,
                     owned_advanced: list[str]) -> float:
    """转型装备沉没成本:已合成进阶件中,不可带到 to_comp 的比例(0..1)。

    owned_advanced = 已持有进阶件名列表;消费端乘金当量(与 formation_cost 同货币)。
    """
    to_keys = set()
    for c in COMP_LIBRARY:
        if c.name == to_comp:
            to_keys = set(c.key_equips)
    if not owned_advanced:
        return 0.0
    sunk = sum(1 for e in owned_advanced if e not in to_keys)
    return sunk / len(owned_advanced)
