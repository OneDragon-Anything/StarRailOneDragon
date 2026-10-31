"""统一部署搜索(评分制;部署判据件,策略层 mandate_v1)。

设计单一源 = changes/2026-10-30-roster-plane1-union/details/
unified-deploy-order.md(§1 评分函数 / §2 三段搜索 / §3 段 3 评分
取优)。总纲 §2.7 职责边界:场上去留 = 部署算法单属——本模块回答
「谁上场、去哪一排、选哪颗星」,输出 target_board(角色名 →
(排, 选定星));卖出/优先级面只消费定型结论(档 1 名集消费)。

三段搜索结构(§2):
- 段 0 枚举准备(build_deploy_panel 装配):唯一性键归一(开拓者各排
  形态互斥)、同键多副本取最高星(落场后形态:银狼 3★ 上场即 1★)、
  召唤物/系统件(cost=0)固定后台剔除、未知身份件保留现位不入枚举
  (禁挤)、窗口谓词与上场锁过滤(虚拟件 uid=None 名命中锁名单按
  fail-closed,D-8 事故复活路径封死);
- 段 1 圈人:候选族按窗口分域(P1 = 四体系两两组合 + 单体系渐进;
  P2+ 未锁 = 候选三线;锁定 = 锁定线羁绊骨架 ∪ P1 过渡家族照常
  枚举),骨架 = 档位形态集合(体系件前缀的档位截断点),全枚举,
  空骨架合法;
- 段 2 补人:候选生成器(近似,unified-deploy-order §2 段 2 近似
  申报——DP 候选生成 + 终评全量评分的正确性结构):线内件优先占席
  (D8-3)+ 分组单位序贪心 + 组取舍变体 + **分组背包 DP 联合分配**
  (跨组增益捕获:多组部分凑档形态贪心序与单组变体覆盖不到,DP 按
  组值增量背包取优;相位枚举 D7-3——锁定窗过渡组 ×4/×1 两相位
  各一套候选,段 3 终评按板面实测 L1 定相位);
- 段 3 评分取优:全候选板按 §1 评分函数**全量终评**(DP 组分只是
  候选生成内部度量,段 3 重算,单归属近似不影响终评正确性)→
  最高分组内排分配 → (站位分, 稳定键, 随机尾键) 定序取一。

评分层结构(§1,数值制):L1 主目标羁绊(10⁹ 域,f = 角色完成度 ×
档位完成度乘法合成)> L2 锁定非核心 sub_tiers(10⁶ 域,仅锁定窗)>
L3 普通(计数制,buff/debuff ×3 > 万金油 ×2 > 其他 ×1;过渡档
保板相位 ×4,锁定线第一档成型回落 ×1)。一键单归属、取当前评估
上下文最高层。金币维零交互(CW 部署免费——用户裁定 2026-10-30
三,核查过非漏项)。

rng = 局面哈希播种(§1 D3-7:同一容器状态 → 同一 rng 序,跨帧稳定
防并列板帧间翻转;同帧多次搜索共享同序 rng → 同帧判定确定)。
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import TYPE_CHECKING

from sr_od.application.currency_war.data.cw_factions import FACTIONS
from sr_od.application.currency_war.kernel.cw_bond_equips import (
    unit_bond_tags,
)
from sr_od.application.currency_war.kernel.cw_deploy_logic import (
    TRANSITION_TRAITS,
    _bonds_named,
    board_unique_key,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.criteria.priority import (
    CROSS_LINE_KEEP_NAMES,
    TIER7_BOND_NAMES,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.deploy_plan import (
    deploy_row_pref,
)

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_comps import Comp
    from sr_od.application.currency_war.kernel.cw_game_state import (
        GameState,
    )
    from sr_od.application.currency_war.kernel.cw_strategy_session import (
        StrategySession,
    )
    from sr_od.application.currency_war.strategies.impl.mandate_v1.mandate import (
        MandateFrame,
    )

# ===== 隔离常量(结构编码非标定:层间隔 10³ 数量级,语义 = 「高层任意
# ===== 正分 > 低层满分」,区间内变动行为零变——unified-deploy-order §1)=====
_L1_SCALE: float = 1_000_000_000.0    # L1 主目标羁绊满分域
_L2_SCALE: float = 1_000_000.0        # L2 锁定非核心满分域(仅锁定窗)
# L3 单位序(用户裁定 2026-10-30):buff/debuff(×3) > 万金油(×2) > 其他(×1)
_L3_BUFF_DEBUFF: int = 3
_L3_UNIVERSAL: int = 2
_L3_OTHER: int = 1
#: 保板相位过渡档系数(锁定窗 ∧ 锁定线 L1=0 期间,过渡体系已成档
#: ×4 临时压过 buff/debuff——锁定线第一档成型即回落 ×1,§1 分值表)
_L3_TRANSITION_KEEP: int = 4

#: 希儿系激活件数(单卡体系权重 = 激活所需件数:希儿 1 + 放大器 2
#: = 3,§1 层内聚合补定义)
_SEELE_ACTIVATION_PIECES: int = 3
_SEELE_SYSTEM_KEY: str = '希儿系'


@dataclass(frozen=True)
class SearchUnit:
    """枚举基本单位(段 0 产物;唯一性键归一)。

    [索引定义] ``origin`` = 'board'(现役场上,带现排)| 'bench';
    ``key`` = 唯一性键(开拓者各排形态归一;char_id 空 = None 未知件,
    段 0 已剔除不出现在 units);``star`` = 落场后形态星级(银狼 3★
    上场即 1★,§1 星级形态裁定)。
    """

    key: str
    char_id: str
    star: int
    origin: str
    row: str          # 现排('front'|'back';bench 件 '')
    uid: int | None   # 环境发放实例号(锁匹配;购入/观察件 None)
    equips: tuple[str, ...] = ()   # 羁绊标签装备贡献输入(unit_bond_tags)


@dataclass(frozen=True)
class DeploySearchPanel:
    """搜索输入面板(容器读口全列的鸭子面板,§1 虚拟面板字段域)。

    生产装配 = :func:`build_deploy_panel`;虚拟重算(获取让位评估 /
    can_deploy_single 快照+X)= 调用方替换 ``units``/``current_board``
    后自构同型面板。
    """

    units: tuple[SearchUnit, ...]
    """枚举单位全集(段 0 已过滤:窗口外/上场锁件不入此集——它们不
    参与任何候选板)。"""
    k_budget: int
    """真人可上场数 = max_units_of − 场上召唤物/系统件 − 场上未知件
    (召唤物占 K——用户确认 2026-10-30)。"""
    front_capacity: int
    back_capacity: int
    """排容量:front 恒 4;back = back_capacity_of − 后排召唤物/未知件
    占格(段 3 排分配扣减,§2 段 3 D2-8/D9-2)。"""
    locked: bool                       # 锁定窗(line_members_view.locked)
    locked_comp: Comp | None           # 锁定线(target_comp;锁定窗非空)
    candidate_comps: tuple[Comp, ...]  # 未锁窗 P2+ 候选族(候选三线)
    p1_pair: tuple[str, ...]           # P1 配方对(体系键;P2+ 恒空)
    plane1: bool                        # P1 窗(未进位面 2)
    current_board: dict[str, str]
    """现板面(名 → 现排;稳定键输入 = 与现板面一致数,名+排粒度)。"""


# ============================================================ 评分函数(§1)


def _fallback_tier_index(bond: str, head_count: int) -> int:
    """人数阈值 → 档序(FACTIONS.tiers 中 ≥ 人数的最小档序;1 基)。

    Comp.form_tiers/sub_tiers 值 = 人数阈值(字段契约「几人激活算
    成型」);档位完成度分母 = 该人数对应档序(D-3 显式选端:经注册
    表档序换算,禁读梯末)。"""
    tiers = FACTIONS[bond].tiers if bond in FACTIONS else ()
    for i, t in enumerate(tiers, start=1):
        if t >= head_count:
            return i
    return len(tiers) or 1


def _achieved_tiers(bond: str, count: int) -> int:
    """羁绊计数 → 已达档数(≥ tiers[i] 的最大 i;0 = 一档未成)。"""
    tiers = FACTIONS[bond].tiers if bond in FACTIONS else ()
    n = 0
    for t in tiers:
        if count >= t:
            n += 1
        else:
            break
    return n


def _tag_counts(units: list[SearchUnit],
                cache: dict[str, tuple[str, ...]] | None = None) \
        -> dict[str, int]:
    """板上单位的羁绊标签多集总和(计数单一源 = ``unit_bond_tags``:
    角色注册表出身 + 开拓者排形态归一 + 布洛妮娅选边单边化(peers =
    板上其余单位)+ 装备贡献四合一,§1 羁绊计数口径——用户确认
    2026-10-30 羁绊按角色数量和星徽)。

    ``cache`` = 板外预计算的单位标签缓存;选边型双羁绊角色(布洛
    娅,SIDE_PICK_DUAL_BONDS)tags 依赖板面 peers——恒现算不缓存。
    """
    from sr_od.application.currency_war.data.cw_chars import (
        SIDE_PICK_DUAL_BONDS,
    )
    counts: dict[str, int] = {}
    for u in units:
        if cache is not None and u.char_id in cache \
                and u.char_id not in SIDE_PICK_DUAL_BONDS:
            tags = cache[u.char_id]
        else:
            # peers = 同场其余单位对象(duck-type char_id;传名字字符串
            # 会使 unit_bond_tags 的选边基数提取得空 → 平局燃血,错账)。
            peers = [p for p in units if p.char_id != u.char_id]
            tags = unit_bond_tags(u, peers=peers)
            if cache is not None and u.char_id not in SIDE_PICK_DUAL_BONDS:
                cache[u.char_id] = tags
        for tag in tags:
            counts[tag] = counts.get(tag, 0) + 1
    return counts


def _line_form_tier_groups(comp: Comp | None) -> tuple[tuple[str, ...], ...]:
    """线的 L1 键组:form_tiers 键 + OR 承接组(or_reqs = **单组**
    [(键, 档)] 对列表——组内任一支达成即满,整组折一条虚拟羁绊族键,
    不逐支重复圈,§2 段 1)。"""
    if comp is None:
        return ()
    groups: list[tuple[str, ...]] = []
    or_keys: set[str] = set()
    if comp.or_reqs:
        keys = tuple(dict.fromkeys(k for k, _t in comp.or_reqs))
        groups.append(keys)
        or_keys.update(keys)
    for k in (comp.form_tiers or {}):
        if k not in or_keys:
            groups.append((k,))
    return tuple(groups)


def _or_group_target(comp: Comp, group: tuple[str, ...]) -> int:
    """OR 承接组目标人数(组内支目标 max——「圈人档位形态索引按
    最优支的档序」同构,§1 层内聚合)。"""
    or_map = dict(comp.or_reqs or ())
    best = 0
    for k in group:
        if k in or_map:
            best = max(best, int(or_map[k]))
        best = max(best, int((comp.form_tiers or {}).get(k, 0)))
    return best


def _or_keys_of(comp: Comp | None) -> frozenset[str]:
    """线的 OR 承接组键集(or_reqs = 单组 [(键,档)] 对列表)。"""
    if comp is None or not comp.or_reqs:
        return frozenset()
    return frozenset(k for k, _t in comp.or_reqs)


def _seele_formed(names: set[str],
                  counts: dict[str, int]) -> bool:
    """希儿系二元(希儿在场 ∧ 放大器 ≥2,量子同频 ∨ 贝洛伯格任一
    ——对齐现役 kernel seele_system_formed 同一判据)。"""
    return ('希儿' in names
            and (counts.get('量子同频', 0) >= 2
                 or counts.get('贝洛伯格', 0) >= 2))


def selection_score(panel: DeploySearchPanel,
                    units: list[SearchUnit],
                    line_comp: Comp | None,
                    line_keys: tuple[str, ...],
                    tag_cache: dict[str, tuple[str, ...]] | None = None,
                    ) -> tuple[float, float, int]:
    """选人分全量终评(§1 评分函数;段 3 对每个完整候选板重算——
    DP 组得分只是候选生成内部度量,本函数才是最终板面分,D7 补问 5)。

    返回 (L1, L2, L3) 三层分数(层间数量级隔离,调用方字典序承载):
    - L1 = 加权平均 of f(角色完成度 × 档位完成度)× 10⁹,权重 = 目标
      档激活人数;分族分支(单卡希儿系二元/过渡二元退化/空羁绊线
      core∪shared 口径/required 逐名折条)见函数体;
    - L2 = sub_tiers 档位完成度加权平均 × 10⁶(仅锁定窗;键集 = 仅
      ``Comp.sub_tiers``——flex_factions 恒 L3,D3-1);
    - L3 = 计数制单位序(羁绊键按已达档、万金油/希儿系按件/二元)。
    """
    counts = _tag_counts(units, tag_cache)
    names = {u.char_id for u in units}
    locked = panel.locked

    # ---- L1(主目标羁绊层)----
    l1_num = 0.0
    l1_den = 0
    comp: Comp | None = None
    groups: tuple[tuple[str, ...], ...] = ()
    if locked:
        comp = panel.locked_comp
        groups = _line_form_tier_groups(comp)
    elif line_keys:
        comp = line_comp
        if comp is not None:
            groups = _line_form_tier_groups(comp)
        else:
            groups = tuple((k,) for k in line_keys)   # 过渡体系单键组
    if comp is not None or groups:
        required = tuple(comp.required_deployed or ()) \
            if comp is not None else ()
        if required and not all(r in names for r in required):
            l1_den = 1   # required 逐名折条:缺名 → 该线 L1 = 0
        elif groups:
            for group in groups:
                # OR 承接组 = 组内取最优可达支(max)计完成度。
                best_f = 0.0
                best_w = 1
                for k in group:
                    if k == _SEELE_SYSTEM_KEY:
                        w = _SEELE_ACTIVATION_PIECES
                        formed = 1.0 if _seele_formed(names, counts) else 0.0
                        amp = (counts.get('量子同频', 0)
                               + counts.get('贝洛伯格', 0))
                        char_done = min(amp / 2.0, 1.0) \
                            if '希儿' in names else 0.0
                        f = formed * char_done
                    elif comp is not None and (
                            k in (comp.form_tiers or {})
                            or k in _or_keys_of(comp)):
                        head = _or_group_target(comp, group) \
                            if k in _or_keys_of(comp) \
                            else int((comp.form_tiers or {}).get(k, 1))
                        w = max(head, 1)
                        tier_target = _fallback_tier_index(k, head)
                        ach = _achieved_tiers(k, counts.get(k, 0))
                        tier_done = ach / max(tier_target, 1)
                        char_done = min(counts.get(k, 0) / max(head, 1), 1.0)
                        f = char_done * tier_done
                    else:
                        # 过渡体系(未锁窗 / P1 锁定窗过渡家族):档位
                        # 完成度 = 二元退化(体系激活 = 1.0/0,注册表
                        # 无「成型档」字段,§1 分族计分分支)。
                        threshold = dict(TRANSITION_TRAITS).get(k, 1)
                        head = max(threshold, 1)
                        w = head
                        tier_done = 1.0 if counts.get(k, 0) >= threshold \
                            else 0.0
                        char_done = min(counts.get(k, 0) / head, 1.0)
                        f = char_done * tier_done
                    if f * w > best_f * best_w:
                        best_f, best_w = f, w
                l1_num += best_f * best_w
                l1_den += best_w
        elif locked and comp is not None:
            # 空羁绊线(反甲流 form_tiers={} ∧ factions=[]):L1 由角色
            # 完成度单独承载(b≡1),分母 = core∪shared 总数、分子 =
            # 其在场数(D2-3 修订——羁绊族口径对该线无源,改阵容成员
            # 口径)。
            members = set(comp.core_chars) | set(comp.shared_chars or ())
            l1_den = max(len(members), 1)
            l1_num = float(len(members & names))
    l1 = (l1_num / l1_den) * _L1_SCALE if l1_den else 0.0

    # ---- L2(锁定线非核心羁绊层;键集 = 仅 Comp.sub_tiers,D3-1)----
    l2 = 0.0
    if locked and panel.locked_comp is not None:
        sub = dict(panel.locked_comp.sub_tiers or {})
        if sub:
            num = 0.0
            den = 0
            for k, v in sub.items():
                head = int(v[0]) if isinstance(v, tuple) else int(v)
                tier_target = _fallback_tier_index(k, head)
                ach = _achieved_tiers(k, counts.get(k, 0))
                w = max(head, 1)
                num += (ach / max(tier_target, 1)) * w
                den += w
            l2 = (num / den) * _L2_SCALE if den else 0.0

    # ---- L3(普通层计数制;一键单归属:更高层键 L3 计分抑制)----
    l1_key_set: set[str] = set()
    for g in groups:
        l1_key_set.update(g)
    l2_key_set: set[str] = set(
        (panel.locked_comp.sub_tiers or {}) if locked
        and panel.locked_comp is not None else ())
    board_l1_zero = l1 <= 0.0
    transition_keys = {k for k, _t in TRANSITION_TRAITS} | {_SEELE_SYSTEM_KEY}
    l3 = 0
    for bond, cnt in counts.items():
        if bond in l1_key_set or bond in l2_key_set:
            continue   # 单归属:L1/L2 键 L3 计分抑制
        ach = _achieved_tiers(bond, cnt)
        if ach <= 0:
            continue
        if bond in transition_keys:
            # 过渡羁绊档条件两态:锁定窗保板相位(锁定线 L1=0)×4 /
            # 成档回落 ×1;未锁窗按 TIER7 归属(不归零——注册表
            # 「参与完成度」语义辖锁定评估,未锁窗它就是普通羁绊)。
            if locked:
                coef = _L3_TRANSITION_KEEP if board_l1_zero else _L3_OTHER
            else:
                coef = (_L3_BUFF_DEBUFF if bond in TIER7_BOND_NAMES
                        else _L3_OTHER)
        elif bond in TIER7_BOND_NAMES:
            coef = _L3_BUFF_DEBUFF
        else:
            coef = _L3_OTHER
        l3 += ach * coef
    # 万金油按件计(DF-2:万金油组无档结构,按件 ×2)。
    for u in units:
        if u.char_id in CROSS_LINE_KEEP_NAMES:
            l3 += _L3_UNIVERSAL
    # 希儿系成型非 L1 键时按 1 档计(DF-2 二元;系数 = 同键态)。
    if _SEELE_SYSTEM_KEY not in l1_key_set \
            and _seele_formed(names, counts):
        l3 += (_L3_TRANSITION_KEEP if locked and board_l1_zero
               else _L3_OTHER)
    return l1, l2, l3


# ============================================================ 段 1/2/3


def _unit_sort_key(u: SearchUnit, comp_pos: Comp | None,
                   current_board: dict[str, str]) -> tuple:
    """组内/骨架内选件序:贡献量分档(卡带双计件贡献 2 > 普通件
    1,cw_bond_equips 双计口径 D9-4)→ 件级排偏好序(deploy_row_pref
    静态可算,D6-6)→ 稳定键(现板在场优先)→ 名字序。"""
    from sr_od.application.currency_war.kernel.cw_bond_equips import (
        equip_bond_grants,
    )
    contrib = 2 if any(equip_bond_grants(e) for e in u.equips) else 1
    pref = deploy_row_pref(u.char_id, comp_pos)
    stable = 0 if current_board.get(u.char_id) else 1
    return (-contrib, 0 if pref == 'front' else 1, stable, u.char_id)


def _prefix_cuts(pool: list[SearchUnit], keys: tuple[str, ...]) \
        -> list[int]:
    """骨架前缀截断点集合(档位形态集合:每键的各档激活人数 +
    全取——t=0 与 t=可达档各一套形态,§2 段 1 D-15;**空键集
    (空羁绊线)时全前缀**——无档位锚点,required/core 逐件渐进
    形态 = 池序前缀全枚举)。"""
    cuts: set[int] = {0, len(pool)}
    if not keys:
        cuts.update(range(len(pool) + 1))
    for k in keys:
        if k == _SEELE_SYSTEM_KEY:
            cuts.update({1, 2, 3})
            continue
        tiers = FACTIONS[k].tiers if k in FACTIONS else ()
        for t in tiers:
            if t <= len(pool):
                cuts.add(t)
    return sorted(c for c in cuts if c <= len(pool))


def _assign_rows(members: list[SearchUnit], panel: DeploySearchPanel,
                 comp_pos: Comp | None) -> dict[str, str] | None:
    """段 3 排分配(char_positions 强制 → 场上件**现排滞回** →
    deploy_row_pref → back 兜底 + 前排保证 + 前后排容量 + 开拓者形态
    排约束;溢出 = 站位分损失最小者让位〔row_pref 兜底级排序,§2 段 3
    牺牲序〕;不可解 → None(容量矛盾,由排分配容量约束排除)。

    现排滞回(§1 稳定键「与现板面一致数」的结构化承载,宽域):场上件
    的排偏好起点 = 现排——row_pref 符合度(pos)不压滞回,等分板上现
    板保持原排(结构化滞回);注册表强约束(char_positions)仍最高优先,
    容量溢出时按牺牲序让位。"""
    cp = (getattr(comp_pos, 'char_positions', None) or {})
    prefs: dict[str, str] = {}
    for u in members:
        hit = cp.get(u.char_id)
        if hit in ('front', 'back'):
            prefs[u.char_id] = hit
        elif u.origin == 'board' and u.row in ('front', 'back'):
            prefs[u.char_id] = u.row
        else:
            prefs[u.char_id] = deploy_row_pref(u.char_id, comp_pos)
    front = [u for u in members if prefs[u.char_id] == 'front']
    back = [u for u in members if prefs[u.char_id] == 'back']
    # 前排保证(出战硬要求前排有角色):前排空 → 牺牲序 = back 偏好
    # 最弱者转前排。
    if not front and members:
        sacrifice = min(back or members,
                        key=lambda u: u.char_id)
        front.append(sacrifice)
        if sacrifice in back:
            back.remove(sacrifice)
    # 容量溢出让位(无 char_positions 强制的软偏好件先让;迁移无条件
    # ——对侧空也迁,「and 对侧非空」旧前置会使纯单排偏好板卡死在
    # 溢出态返回 None)。两排全溢出 = K 超物理容(结构不可达,防御)。
    def _soft(u: SearchUnit, row: str) -> int:
        return 1 if cp.get(u.char_id) == row else 0
    guard = len(members) + 2
    while (len(front) > panel.front_capacity
           or len(back) > panel.back_capacity) and guard > 0:
        guard -= 1
        if len(front) > panel.front_capacity:
            mv = max(front, key=lambda u: (_soft(u, 'front'), u.char_id))
            front.remove(mv)
            back.append(mv)
        elif len(back) > panel.back_capacity:
            mv = max(back, key=lambda u: (_soft(u, 'back'), u.char_id))
            back.remove(mv)
            front.append(mv)
        else:
            break
    if len(front) > panel.front_capacity \
            or len(back) > panel.back_capacity:
        return None
    rows: dict[str, str] = {}
    for u in front:
        rows[u.char_id] = 'front'
    for u in back:
        rows[u.char_id] = 'back'
    return rows


def _position_score(members: list[SearchUnit], rows: dict[str, str],
                    comp_pos: Comp | None,
                    current_board: dict[str, str]) -> tuple[int, int]:
    """(站位分, 稳定键):站位分 = 分配排对**偏好起点**(char_positions
    强制 > 场上件现排滞回 > deploy_row_pref,与 :func:`_assign_rows`
    同一 prefs 序)的符合数;稳定键 = 与现板面一致数(名+排粒度,星维
    不进——星变更本就该动板,§1 D3-7)。"""
    cp = (getattr(comp_pos, 'char_positions', None) or {})
    pos = 0
    for u in members:
        hit = cp.get(u.char_id)
        if hit in ('front', 'back'):
            want = hit
        elif u.origin == 'board' and u.row in ('front', 'back'):
            want = u.row
        else:
            want = deploy_row_pref(u.char_id, comp_pos)
        if rows.get(u.char_id) == want:
            pos += 1
    stable = sum(
        1 for u in members
        if current_board.get(u.char_id) == rows.get(u.char_id))
    return pos, stable


def _situation_seed(panel: DeploySearchPanel) -> int:
    """局面哈希播种(§1 D3-7:同一容器状态 → 同一 rng 序,跨帧稳定;
    同帧多次搜索〔含 can_deploy_single 逐牌〕共享同序 rng)。

    哈希 = 稳定摘要(zlib.crc32)——禁裸 ``hash()``:Python 字符串哈希按
    进程随机化(PYTHONHASHSEED),sim 整局轨迹会随进程漂移(部署并列板
    的 rng 尾键逐进程不同 → 同 seed 不同局;某进程落进备战连败环实测,
    部署统一批戊批定位)。稳定摘要使同局面跨进程同 rng,sim 确定性
    契约(同 seed 同轨迹)恢复。"""
    import zlib
    material = ','.join(sorted(
        f'{u.char_id}:{u.star}:{u.origin}' for u in panel.units))
    material += f'|k{panel.k_budget}|f{panel.front_capacity}' \
                f'|b{panel.back_capacity}|lk{int(panel.locked)}' \
                f'|c{len(panel.candidate_comps)}'
    return zlib.crc32(material.encode('utf-8')) & 0xFFFFFFFF


def search_deploy_target(panel: DeploySearchPanel,
                         ) -> dict[str, tuple[str, int]]:
    """统一部署搜索主入口(三段;纯函数零 IO,§1 接口契约④)。

    返回 target_board = {角色名: (排, 选定星)}(接口契约②,载荷星维
    承载就位粒度名+排+星)。候选全不可排(容量矛盾,结构不可达防御)
    → 返回空 dict(消费端 fail-closed 按现板定型,申报)。
    """
    rng = random.Random(_situation_seed(panel))
    comp_pos = panel.locked_comp if panel.locked else None
    tag_cache: dict[str, tuple[str, ...]] = {}

    # ---- 段 1 圈人(骨架 = 档位形态集合)----
    def _pool_of(keys: tuple[str, ...],
                 member_names: frozenset[str]) -> list[SearchUnit]:
        """体系/线骨架件池:羁绊标签 ∩ 键系 ∪ 线名单成员,骨架内按
        选件序排序(**锁定线核心优先、逐档**,§2 段 1:required >
        core > shared > 标签件——骨架优先圈 engine_required 铁三角
        形态由成员序承载)。"""
        comp = panel.locked_comp if panel.locked else None
        req = tuple(comp.required_deployed or ()) if comp is not None else ()
        core = set(comp.core_chars) if comp is not None else set()
        pool = [u for u in panel.units
                if (_bonds_named(u.char_id) & set(keys)
                    or u.char_id in member_names)]

        def _line_rank(u: SearchUnit) -> int:
            if not panel.locked:
                return 2
            if u.char_id in req:
                return 0
            if u.char_id in core:
                return 1
            return 2

        pool.sort(key=lambda u: (
            _line_rank(u),
            *_unit_sort_key(u, comp_pos, panel.current_board)))
        return pool

    def _line_keys_of(comp: Comp | None) -> tuple[str, ...]:
        if comp is None:
            return ()
        return tuple(dict.fromkeys(
            k for g in _line_form_tier_groups(comp) for k in g))

    def _member_names_of(comp: Comp | None) -> frozenset[str]:
        if comp is None:
            return frozenset()
        return frozenset(set(comp.core_chars)
                         | set(comp.shared_chars or ()))

    #: 过渡体系成员名(标签命中三羁绊键;希儿系键 = 希儿 + 放大器
    #: 阵营成员,is_seele_system_member 单卡体系判据,§2 段 1)。
    def _transition_names(keys: tuple[str, ...]) -> frozenset[str]:
        from sr_od.application.currency_war.kernel.cw_deploy_logic import (
            is_seele_system_member,
        )
        bond_keys = set(keys) - {_SEELE_SYSTEM_KEY}
        names: set[str] = set()
        for u in panel.units:
            bonds = _bonds_named(u.char_id)
            if (bond_keys & bonds) or (
                    _SEELE_SYSTEM_KEY in keys
                    and is_seele_system_member(u.char_id, bonds)):
                names.add(u.char_id)
        return frozenset(names)

    skeletons: list[tuple[tuple[SearchUnit, ...], Comp | None,
                          tuple[str, ...]]] = []
    if panel.locked and panel.locked_comp is not None:
        comp = panel.locked_comp
        line_keys = _line_keys_of(comp)
        core_hand = {u.char_id for u in panel.units
                     if u.char_id in set(comp.core_chars)}
        if core_hand or not line_keys:
            pool = _pool_of(line_keys, _member_names_of(comp))
            for cut in _prefix_cuts(pool, line_keys):
                skeletons.append((tuple(pool[:cut]), comp, line_keys))
        if panel.plane1:
            # P1 锁定窗:过渡家族骨架照常枚举(按 L3 条件档计分——
            # 保证 L1=0 保板相位过渡板在候选空间内,五轮用户裁定)。
            for pair in _transition_pairs(panel):
                pool = _pool_of(pair, _transition_names(pair))
                for cut in _prefix_cuts(pool, pair):
                    skeletons.append((tuple(pool[:cut]), None, pair))
    elif panel.plane1:
        # P1 未锁:四体系两两组合 + 单体系渐进(|I∩Q|=1 第二席按
        # _progressive_second_seat 同款单体系骨架语义,二轮补问 3)。
        for pair in _transition_pairs(panel):
            pool = _pool_of(pair, _transition_names(pair))
            for cut in _prefix_cuts(pool, pair):
                skeletons.append((tuple(pool[:cut]), None, pair))
    else:
        # P2+ 未锁:候选三线。
        for comp in panel.candidate_comps:
            line_keys = _line_keys_of(comp)
            pool = _pool_of(line_keys, _member_names_of(comp))
            for cut in _prefix_cuts(pool, line_keys):
                skeletons.append((tuple(pool[:cut]), comp, line_keys))
    skeletons.append(((), None, ()))   # 空骨架合法(全 L3 散件板)

    # ---- 段 2 补人(候选生成器,近似)----
    l1_keys_all: set[str] = set()
    if panel.locked and panel.locked_comp is not None:
        l1_keys_all.update(_line_keys_of(panel.locked_comp))
    l2_keys_all: set[str] = set(
        (panel.locked_comp.sub_tiers or {}) if panel.locked
        and panel.locked_comp is not None else ())

    def _greedy_fill(skel: tuple[SearchUnit, ...],
                     line_keys: tuple[str, ...]) -> list[SearchUnit]:
        """线内件优先占席(D8-3)+ 分组单位序贪心补满:携带 L1/L2
        键标签的剩余件先取至 K 上限(超出按线内序截断),其余席位
        按组单位序(buff/debuff > 万金油 > 其他羁绊 > 无标签)贪心。"""
        skel_keys = {u.key for u in skel}
        rest = [u for u in panel.units if u.key not in skel_keys]
        budget = panel.k_budget - len(skel)
        if budget <= 0:
            return list(skel)
        taken: list[SearchUnit] = []
        inline = [u for u in rest
                  if _bonds_named(u.char_id)
                  & (l1_keys_all | l2_keys_all | set(line_keys))]
        inline.sort(key=lambda u: _unit_sort_key(u, comp_pos,
                                                 panel.current_board))
        taken.extend(inline[:budget])
        rest2 = [u for u in rest if u not in taken]
        rest2.sort(key=lambda u: _unit_sort_key(u, comp_pos,
                                                panel.current_board))
        for u in rest2:
            if len(taken) >= budget:
                break
            taken.append(u)
        return [*skel, *taken]

    def _group_variants(skel: tuple[SearchUnit, ...]) \
            -> list[list[SearchUnit]]:
        """组取舍变体(近似 DP 的组间枚举:骨架 + 单组取满的候选,
        补「贪心序压过小组凑档」的覆盖面)。"""
        skel_keys = {u.key for u in skel}
        rest = [u for u in panel.units if u.key not in skel_keys]
        out: list[list[SearchUnit]] = []
        groups: dict[str, list[SearchUnit]] = {}
        for u in rest:
            bonds = _bonds_named(u.char_id)
            g = sorted(bonds)[0] if bonds else ''
            groups.setdefault(g, []).append(u)
        for _g, grp in sorted(groups.items()):
            grp = grp[:max(panel.k_budget - len(skel), 0)]
            if grp:
                out.append([*skel, *grp])
        return out

    def _contrib_of(u: SearchUnit) -> int:
        """件贡献量(卡带双计件 2 / 普通件 1;cw_bond_equips 双计口径
        D9-4,与 _unit_sort_key 首键同源)。"""
        from sr_od.application.currency_war.kernel.cw_bond_equips import (
            equip_bond_grants,
        )
        return 2 if any(equip_bond_grants(e) for e in u.equips) else 1

    def _dp_fill(skel: tuple[SearchUnit, ...],
                 line_keys: tuple[str, ...]) -> list[list[SearchUnit]]:
        """分组背包 DP 补人候选(§2 段 2 设计基线的组间联合形态;unified-
        deploy-order §2 段 2——骨架 + 线内件优先占席(D8-3)后,剩余席位
        按「羁绊分组 + 万金油/希儿系特组」背包联合分配):补贪心序与单组
        变体都覆盖不到的**多组部分凑档**形态(跨组增益捕获——两组各差
        1-2 件成档时,贪心全局序可能交错取件致两组成档皆失,单组变体只
        保一组;DP 按组值增量联合取优)。

        近似口径(与设计 §2 段 2 近似申报同款,终评兜底):组值 = 组键
        已达档增量 × L3 系数(首标签归属单键计,件次标签贡献不可见——
        段 3 全量终评兜底);万金油组按件 ×2;希儿系二元不设特组——其
        成型板由段 1 骨架枚举承载(P1 过渡对含希儿系键),放大器件按
        阵营组归 DP,值差归段 3;相位枚举 D7-3——锁定窗过渡组 ×4/×1
        两相位各跑一遍,终评实测 L1 定相位。

        组内选件序 = _unit_sort_key(贡献量分档 → 排偏好 → 稳定键 →
        名字序,D9-4/D6-6);DP 取优后剩余席位按同序 value-中性垫满
        (板面满员形态与贪心候选一致,垫件价值归段 3 全量评分)。"""
        skel_keys = {u.key for u in skel}
        rest = [u for u in panel.units if u.key not in skel_keys]
        budget = panel.k_budget - len(skel)
        if budget <= 0 or not rest:
            return []

        def _srt(u: SearchUnit) -> tuple:
            return _unit_sort_key(u, comp_pos, panel.current_board)

        inline = [u for u in rest
                  if _bonds_named(u.char_id)
                  & (l1_keys_all | l2_keys_all | set(line_keys))]
        inline.sort(key=_srt)
        inline = inline[:budget]
        inline_keys = {u.key for u in inline}
        rest2 = [u for u in rest if u.key not in inline_keys]
        rest2.sort(key=_srt)
        rem_budget = budget - len(inline)
        if rem_budget <= 0:
            return []
        # 基线 = 骨架 ∪ 线内件(骨架基线全量计分口径 D8-2 的组值侧简化:
        # 组值只读组键计数,基线计数含骨架+线内件全部标签)。
        base_units = [*skel, *inline]
        base_counts = _tag_counts(base_units, tag_cache)
        # 分组(首羁绊标签归属;万金油特组按件;希儿系特组二元)。
        groups: dict[str, list[SearchUnit]] = {}
        for u in rest2:
            if u.char_id in CROSS_LINE_KEEP_NAMES:
                groups.setdefault('\0universal', []).append(u)
                continue
            bonds = _bonds_named(u.char_id)
            if bonds:
                groups.setdefault(sorted(bonds)[0], []).append(u)
        transition_keys = {k for k, _t in TRANSITION_TRAITS} \
            | {_SEELE_SYSTEM_KEY}

        def _l3_coef(bond: str, trans_keep: bool) -> int:
            if bond in transition_keys:
                return _L3_TRANSITION_KEEP if trans_keep else _L3_OTHER
            return (_L3_BUFF_DEBUFF if bond in TIER7_BOND_NAMES
                    else _L3_OTHER)

        def _group_values(trans_keep: bool) -> dict[str, list[int]]:
            """每组各取件数 0..len 的组值(增量口径)。"""
            vals: dict[str, list[int]] = {}
            for g, grp in groups.items():
                vs = [0]
                if g == '\0universal':
                    for k in range(1, len(grp) + 1):
                        vs.append(_L3_UNIVERSAL * k)
                else:
                    base = base_counts.get(g, 0)
                    for k in range(1, len(grp) + 1):
                        k_eff = sum(_contrib_of(u) for u in grp[:k])
                        delta = (_achieved_tiers(g, base + k_eff)
                                 - _achieved_tiers(g, base))
                        vs.append(delta * _l3_coef(g, trans_keep))
                vals[g] = vs
            return vals

        def _knapsack(vals: dict[str, list[int]],
                      ) -> dict[str, int]:
            """分组背包取件数(最大化 Σ组值,Σ件数 ≤ rem_budget;
            同值取更多件——满员优先,垫满语义的取优侧承载)。"""
            gnames = sorted(vals)
            # dp[b] = (最优值, 回溯取件数字典);b = 已用席位。
            dp: list[tuple[int, dict[str, int]]] = [
                (0, {}) for _ in range(rem_budget + 1)]
            for g in gnames:
                vs = vals[g]
                cap = len(vs) - 1
                ndp: list[tuple[int, dict[str, int]]] = [
                    (0, {}) for _ in range(rem_budget + 1)]
                for b in range(rem_budget + 1):
                    best = dp[b]
                    for k in range(0, min(cap, b) + 1):
                        cand_v = dp[b - k][0] + vs[k]
                        # 同值取更多件(贪心满员形态对齐;组序字典序
                        # 平局确定性)。
                        cand = (cand_v, dp[b - k][1] | {g: k})
                        if cand_v > best[0] or (cand_v == best[0]
                                                and k > best[1].get(g, 0)):
                            best = cand
                    ndp[b] = best
                dp = ndp
            # 全预算行 = 最优(dp 值对席位占用单调不减,组内同值取更多件)。
            return dp[rem_budget][1]

        out_boards: list[list[SearchUnit]] = []
        # 相位枚举(D7-3):锁定窗过渡组 ×4/×1 两相位各一套候选,段 3
        # 终评按板面实测 L1 定相位。
        phases = [True, False] if panel.locked else [False]
        seen_mix: set[tuple] = set()
        for trans_keep in phases:
            take = _knapsack(_group_values(trans_keep))
            chosen = [*inline]
            for g in sorted(take):
                for u in groups[g][:take[g]]:
                    chosen.append(u)
            # value-中性垫满(剩余席位按组单位序补满,形态与贪心一致)。
            chosen_keys = {u.key for u in chosen}
            for u in rest2:
                if len(chosen) >= budget:
                    break
                if u.key not in chosen_keys:
                    chosen.append(u)
            mix = tuple(sorted(u.key for u in chosen))
            if mix not in seen_mix and len(chosen) <= budget:
                seen_mix.add(mix)
                out_boards.append([*skel, *chosen])
        return out_boards

    candidates: list[tuple[tuple[SearchUnit, ...], Comp | None,
                           tuple[str, ...]]] = []
    for skel, comp, keys in skeletons:
        if len(skel) > panel.k_budget:
            continue
        full = _greedy_fill(skel, keys)
        candidates.append((tuple(full), comp, keys))
        if skel:
            candidates.append((skel, comp, keys))   # 仅骨架变体
        for variant in _group_variants(skel):
            candidates.append((tuple(variant), comp, keys))
        for variant in _dp_fill(skel, keys):
            candidates.append((tuple(variant), comp, keys))

    # 同板去重(成员键集 + 评估上下文)。
    dedup: dict[tuple, tuple[tuple[SearchUnit, ...], Comp | None,
                             tuple[str, ...]]] = {}
    for members, comp, keys in candidates:
        mk = tuple(sorted({u.key for u in members}))
        ctx = comp.name if comp is not None else keys
        dedup.setdefault((mk, ctx), (members, comp, keys))

    # ---- 段 3 评分取优(全量终评 + 排分配 + 字典序)----
    best_key: tuple | None = None
    best_out: tuple[tuple[SearchUnit, ...], dict[str, str]] | None = None
    for members, comp, keys in dedup.values():
        l1, l2, l3 = selection_score(panel, list(members), comp, keys,
                                     tag_cache)
        rows = _assign_rows(list(members), panel, comp_pos)
        if rows is None:
            continue
        pos, stable = _position_score(list(members), rows, comp_pos,
                                      panel.current_board)
        rng_tail = rng.random()
        key = (l1, l2, l3, pos, stable, rng_tail)
        if best_key is None or key > best_key:
            best_key = key
            best_out = (members, rows)
    if best_out is None:
        return {}
    members, rows = best_out
    return {u.char_id: (rows[u.char_id], u.star) for u in members}


def _transition_pairs(panel: DeploySearchPanel) -> list[tuple[str, ...]]:
    """P1 过渡体系组合键(两两组合 + 单体系;在任配方对优先枚举——
    p1_pair = 当前配方锁,组合空间含其在任形态)。"""
    systems = (*tuple(k for k, _t in TRANSITION_TRAITS), _SEELE_SYSTEM_KEY)
    pairs: list[tuple[str, ...]] = []
    if panel.p1_pair:
        pairs.append(tuple(panel.p1_pair))
    for i in range(len(systems)):
        pairs.append((systems[i],))
        for j in range(i + 1, len(systems)):
            pair = (systems[i], systems[j])
            if pair not in pairs:
                pairs.append(pair)
    return pairs


# ============================================================ 生产装配(段 0)


def build_deploy_panel(session: StrategySession, gs: GameState,
                       frame: MandateFrame | None = None,
                       ) -> DeploySearchPanel:
    """搜索面板生产装配(容器读口全列一次现取;§1 虚拟面板字段域)。

    段 0 过滤在此执行:窗口谓词(entry._deploy_window_blocked 现役
    谓词本体保留为唯一源)/上场锁(uid 命中记录;虚拟件 uid=None 名
    命中锁名单即视为锁,fail-closed)/召唤物系统件(cost=0,固定后台
    末位剔除)/未知身份件不入枚举但占 K 占格(§2 段 0 D3-13/D5-6)。
    """
    from sr_od.application.currency_war.data.cw_chars import CHARACTERS
    from sr_od.application.currency_war.kernel.cw_comps import get_comp
    from sr_od.application.currency_war.kernel.cw_economy import (
        effective_cost,
    )
    from sr_od.application.currency_war.kernel.cw_exec_state import (
        bench_slot_unit,
    )
    from sr_od.application.currency_war.kernel.cw_game_state import (
        back_capacity_of,
        bench_entries_of,
        deployed_rows_of,
        max_units_of,
    )
    from sr_od.application.currency_war.strategies.impl.mandate_v1 import (
        entry,
        session_scope,
    )
    from sr_od.application.currency_war.strategies.impl.mandate_v1.line_select import (
        compute_candidates,
        held_invest_names_of,
    )
    from sr_od.application.currency_war.strategies.impl.mandate_v1.mandate_state import (
        state_of,
    )

    st = state_of(session)
    # 锁定窗直读调用方 session 的策略状态(line_members_view 的
    # state_of(gs) 依赖 gs.strategy_state 接线,虚拟路径调用方
    # (shop 评估/sell_candidates 传 gs 当 session)不保证接线——
    # 统一走 session 槽,判据 = target_comp 非空即锁定,与
    # line_members_view 同判不同宿主)。
    locked = getattr(st, 'target_comp', None) is not None
    locked_comp = getattr(st, 'target_comp', None) if locked else None
    plane1 = not session_scope.plane2_started_of(gs)
    _ist = getattr(st, 'v3_intention', None)
    p1_pair = tuple(getattr(_ist, 'p1_pair', ()) or ()) if plane1 else ()
    candidate_comps: tuple = ()
    if not locked and not plane1:
        held: set[str] = set()
        for u in _all_units(gs):
            if u.char_id:
                held.add(str(u.char_id))
        cand_names = compute_candidates(frozenset(held),
                                        held_invest_names_of(gs))
        candidate_comps = tuple(c for c in
                                (get_comp(n) for n in cand_names)
                                if c is not None)

    front, back = deployed_rows_of(gs)
    locks = tuple(gs.env_grant_deploy_locks.value or ())
    lock_uids = frozenset(uid for _c, uid, _u in locks)
    lock_names = frozenset(c for c, _uid, _u in locks)

    units: list[SearchUnit] = []
    system_on_board = 0
    unknown_on_board = 0
    back_cap_total = back_capacity_of(gs)
    system_in_back = 0
    unknown_in_back = 0
    lv999_tier = effective_cost(gs, '银狼LV.999')

    def _mk(cid: str, star: int, origin: str, row: str, uid: int | None,
            equips: tuple[str, ...]) -> SearchUnit:
        # 银狼落场后形态(§1:3★ 上场即下档 1★——现档 = 5 费封顶时
        # 恒等搬运,与上报层同一变换纯函数口径对齐)。
        eff_star = star
        if cid == '银狼LV.999' and star >= 3 and lv999_tier < 5:
            eff_star = 1
        from types import SimpleNamespace
        return SearchUnit(
            key=board_unique_key(SimpleNamespace(char_id=cid)) or cid,
            char_id=cid, star=eff_star, origin=origin, row=row, uid=uid,
            equips=equips)

    for row, seq in (('front', front), ('back', back)):
        for u in seq:
            if u is None:
                continue
            cid = str(u.char_id or '')
            if not cid:
                unknown_on_board += 1
                if row == 'back':
                    unknown_in_back += 1
                continue
            ch = CHARACTERS.get(cid)
            if ch is not None and not ch.cost:
                # 召唤物/系统件(cost=0,狸小虎族):固定后台,剔除出
                # 枚举,占 K 占格(判定 = predicates.is_unsellable_
                # system_unit 同一 cost=0 口径,单一源对齐)。
                system_on_board += 1
                if row == 'back':
                    system_in_back += 1
                continue
            if (getattr(u, 'uid', None) in lock_uids
                    and getattr(u, 'uid', None) is not None) \
                    or cid in lock_names:
                continue
            # 窗口谓词只辖**新上场**(§3.9:场上件上场时已过谓词,窗口
            # 单调(只开不关)恒满足——已就位件不重新过滤,违例形态归
            # 观察侧 fail-closed 换下留证)。
            units.append(_mk(cid, int(u.star or 1), 'board', row,
                             getattr(u, 'uid', None),
                             tuple(getattr(u, 'equips', None) or ())))
    for b in bench_entries_of(gs):
        u = bench_slot_unit(b)
        if u is None or not (u.char_id or ''):
            continue
        cid = str(u.char_id)
        uid = getattr(u, 'uid', None)
        if (uid is not None and uid in lock_uids) or cid in lock_names:
            continue
        if entry._deploy_window_blocked(session, gs, cid):
            continue
        units.append(_mk(cid, int(u.star or 1), 'bench', '', uid,
                         tuple(getattr(u, 'equips', None) or ())))

    # 同键多副本取最高星(落场后形态比较;板上的低星副本自然落败)。
    by_key: dict[str, SearchUnit] = {}
    for u in units:
        cur = by_key.get(u.key)
        if cur is None or u.star > cur.star \
                or (u.star == cur.star and u.origin == 'board'):
            by_key[u.key] = u
    units = sorted(by_key.values(), key=lambda u: u.char_id)

    current_board = {
        str(u.char_id): row
        for row, seq in (('front', front), ('back', back))
        for u in seq if u is not None and u.char_id}
    return DeploySearchPanel(
        units=tuple(units),
        k_budget=max(max_units_of(gs) - system_on_board
                     - unknown_on_board, 0),
        front_capacity=4,
        back_capacity=max(back_cap_total - system_in_back
                          - unknown_in_back, 0),
        locked=locked,
        locked_comp=locked_comp,
        candidate_comps=candidate_comps,
        p1_pair=p1_pair,
        plane1=plane1,
        current_board=current_board,
    )


def _all_units(gs: GameState) -> list:
    """全持牌域(bench ∪ deployed)单位(候选线持有的证据输入)。"""
    from sr_od.application.currency_war.kernel.cw_exec_state import (
        bench_slot_unit,
    )
    from sr_od.application.currency_war.kernel.cw_game_state import (
        bench_entries_of,
        deployed_rows_of,
    )
    front, back = deployed_rows_of(gs)
    out = [u for u in (*front, *back) if u is not None]
    for b in bench_entries_of(gs):
        u = bench_slot_unit(b)
        if u is not None:
            out.append(u)
    return out


def panel_from_virtual(session: StrategySession, gs: GameState,
                       bench_slots: list, field_units: list,
                       ) -> DeploySearchPanel:
    """虚拟路径面板(获取让位评估步 3 / can_deploy_single 快照+X:
    生产面板容器读口 + 虚拟 bench/场上单位替换,§1 接口契约③)。

    ``bench_slots`` = 虚拟 bench 槽位条目列表(升星连锁模拟产物,
    SimAcquisition.bench 的 BenchSlot 半);``field_units`` = 虚拟场
    上单位(紧缩序,排映射 = 现板同名保持原排、新上者 back 兜底)。
    窗口谓词/锁/容量过滤与生产装配同核(段 0 同一过滤管道)。
    """
    panel = build_deploy_panel(session, gs)
    from sr_od.application.currency_war.kernel.cw_economy import (
        effective_cost,
    )
    from sr_od.application.currency_war.kernel.cw_exec_state import (
        bench_slot_unit,
    )
    locks = tuple(gs.env_grant_deploy_locks.value or ())
    lock_uids = frozenset(uid for _c, uid, _u in locks)
    lock_names = frozenset(c for c, _uid, _u in locks)
    lv999_tier = effective_cost(gs, '银狼LV.999')

    def _mk(cid, star, origin, row, uid, equips):
        eff_star = star
        if cid == '银狼LV.999' and star >= 3 and lv999_tier < 5:
            eff_star = 1
        from types import SimpleNamespace
        return SearchUnit(
            key=board_unique_key(SimpleNamespace(char_id=cid)) or cid,
            char_id=cid, star=eff_star, origin=origin, row=row, uid=uid,
            equips=equips)

    from sr_od.application.currency_war.strategies.impl.mandate_v1 import (
        entry,
    )
    units: list[SearchUnit] = []
    for u in field_units:
        if u is None or not (u.char_id or ''):
            continue
        cid = str(u.char_id)
        uid = getattr(u, 'uid', None)
        if (uid is not None and uid in lock_uids) or cid in lock_names:
            continue
        # 窗口谓词只辖新上场(§3.9 场上件恒满足)。
        units.append(_mk(cid, int(u.star or 1), 'board',
                         panel.current_board.get(cid, 'back'), uid,
                         tuple(getattr(u, 'equips', None) or ())))
    for b in bench_slots:
        u = bench_slot_unit(b) if b is not None else None
        if u is None or not (u.char_id or ''):
            continue
        cid = str(u.char_id)
        uid = getattr(u, 'uid', None)
        if (uid is not None and uid in lock_uids) or cid in lock_names:
            continue
        if entry._deploy_window_blocked(session, gs, cid):
            continue
        units.append(_mk(cid, int(u.star or 1), 'bench', '', uid,
                         tuple(getattr(u, 'equips', None) or ())))
    by_key: dict[str, SearchUnit] = {}
    for u in units:
        cur = by_key.get(u.key)
        if cur is None or u.star > cur.star \
                or (u.star == cur.star and u.origin == 'board'):
            by_key[u.key] = u
    units = sorted(by_key.values(), key=lambda u: u.char_id)
    return DeploySearchPanel(
        units=tuple(units),
        k_budget=panel.k_budget, front_capacity=panel.front_capacity,
        back_capacity=panel.back_capacity, locked=panel.locked,
        locked_comp=panel.locked_comp,
        candidate_comps=panel.candidate_comps, p1_pair=panel.p1_pair,
        plane1=panel.plane1,
        current_board={
            str(u.char_id): panel.current_board.get(str(u.char_id), 'back')
            for u in field_units if u is not None and u.char_id})
