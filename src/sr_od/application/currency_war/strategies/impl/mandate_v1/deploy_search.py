"""统一部署搜索(评分制;部署判据件,策略层 mandate_v1)。

设计单一源 = 策略面正本 strategy-docs/24_deploy_segment.md
(下称「正本」;§1.1 评分函数 / §1.2 三段搜索)。职责边界(正本 §1):
场上去留 = 部署算法单属——本模块回答
「谁上场、去哪一排、选哪颗星」,输出 target_board(角色名 →
(排, 选定星));卖出/优先级面只消费定型结论(档 1 名集消费)。

三段搜索结构(正本 §1.2):
- 段 0 枚举准备(build_deploy_panel 装配):唯一性键归一(开拓者各排
  形态互斥)、同键多副本取最高星(落场后形态:银狼 3★ 上场即 1★)、
  召唤物/系统件(cost=0)固定后台剔除、未知身份件保留现位不入枚举
  (禁挤)、上场锁过滤(虚拟件 uid=None 名命中锁名单按
  fail-closed,D-8 事故复活路径封死;无上阵窗口硬约束——entry_signals
  整体退役,上场时机 = 骨架/L1 完成度自适应);
- 段 1 圈人:候选族按窗口分域(未终局锁定帧任意位面 = 过渡层组合条目
  骨架 ∪ 终局候选三线,条目域单一源 = transition_active_entries,
  锁定条目在前;锁定 = 锁定线羁绊骨架,档 0 每键一组,过渡层退役
  恒空),骨架 = 档位形态集合(键档激活人数的前缀截断点),全枚举,
  空骨架合法;
- 段 2 补人:候选生成器(近似,正本 §1.2 段 2 近似
  申报——DP 候选生成 + 终评全量评分的正确性结构):线内件优先占席
  (D8-3)+ 分组单位序贪心 + 组取舍变体 + **分组背包 DP 联合分配**
  (跨组增益捕获:多组部分凑档形态贪心序与单组变体覆盖不到,DP 按
  组值增量背包取优);
- 段 3 评分取优:全候选板按正本 §1.1 评分函数**全量终评**(DP 组分只是
  候选生成内部度量,段 3 重算,单归属近似不影响终评正确性)→
  最高分组内排分配 → (站位分, 稳定键, 随机尾键) 定序取一。

评分层结构(正本 §1.1,数值制):L1 主目标羁绊(10⁹ 域,f = 角色完成度 ×
档位完成度乘法合成)> L2 锁定非核心加分层(bonus_faction_reqs,10⁶ 域,仅锁定窗)>
L3 普通(计数制,buff/debuff ×3 > 万金油 ×2 > 其他 ×1)。一键单归属、取当前评估
上下文最高层。金币维零交互(CW 部署免费——用户裁定 2026-10-30
三,核查过非漏项)。

rng = 局面哈希播种(正本 §1.1 rng 播种:同一状态容器状态 → 同一 rng 序,跨帧稳定
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
from sr_od.application.currency_war.kernel.cw_comps import (
    carry_anchor,
    named_units,
    parse_char_position,
)
from sr_od.application.currency_war.kernel.cw_deploy_logic import (
    _bonds_named,
    board_unique_key,
)
from sr_od.application.currency_war.kernel.cw_intention import (
    transition_active_entries,
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
# ===== 正分 > 低层满分」,区间内变动行为零变——正本 §1.1)=====
# L1 两层支配编码(原 required_deployed 灭零特判的防形态,正本 §1.1):named 层
# (点名件在场率)×10⁹ 严格支配档位层 ×10⁸——层间 10 倍域差承载「任何
# 满点名件板恒压任何缺点名件板」(原 required 灭零的防形态,跨线 argmax
# 等价),L1 域顶随之 = 1.1×10⁹(named 满 + 档位满)。层间严格性的数据
# 边界 = 过渡 core 规模 m ≤ 9(建库断言钉住)。
_L1_NAMED_SCALE: float = 1_000_000_000.0   # L1 named 层(点名件在场率)满分域
_L1_TIER_SCALE: float = 100_000_000.0      # L1 档位层(羁绊完成度)满分域
_L1_SCALE: float = 1_000_000_000.0         # L1 空羁绊线 members 承载支满分域(仅锁定窗,同 10⁹ 数值不同语义)
_L2_SCALE: float = 1_000_000.0        # L2 锁定非核心满分域(仅锁定窗)
# L3 单位序(用户裁定 2026-10-30):buff/debuff(×3) > 万金油(×2) > 其他(×1)
_L3_BUFF_DEBUFF: int = 3
_L3_UNIVERSAL: int = 2
_L3_OTHER: int = 1


@dataclass(frozen=True)
class SearchUnit:
    """枚举基本单位(段 0 产物;唯一性键归一)。

    [索引定义] ``origin`` = 'board'(现役场上,带现排)| 'bench';
    ``key`` = 唯一性键(开拓者各排形态归一;char_id 空 = None 未知件,
    段 0 已剔除不出现在 units);``star`` = 落场后形态星级(银狼 3★
    上场即 1★,正本 §1.1 星级形态)。
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
    """搜索输入面板(状态容器读口全列的鸭子类型(duck typing)面板,正本 §1.1 虚拟面板字段域)。

    生产装配 = :func:`build_deploy_panel`;虚拟重算(获取让位评估 /
    can_deploy_single 快照+X)= 调用方替换 ``units``/``current_board``
    后自构同型面板。
    """

    units: tuple[SearchUnit, ...]
    """枚举单位全集(段 0 已过滤:上场锁件不入此集——它们不
    参与任何候选板)。"""
    k_budget: int
    """真人可上场数 = max_units_of − 场上召唤物/系统件 − 场上未知件
    (召唤物占 K——用户确认 2026-10-30)。"""
    front_capacity: int
    back_capacity: int
    """排容量:front 恒 4;back = back_capacity_of − 后排召唤物/未知件
    占格(段 3 排分配扣减,正本 §1.2 段 3 D2-8/D9-2)。"""
    locked: bool                       # 锁定窗(line_members_view.locked)
    locked_comp: Comp | None           # 锁定线(target_comp;锁定窗非空)
    candidate_comps: tuple[Comp, ...]  # 未终局锁定帧终局候选族(候选三线)
    transition_comps: tuple[Comp, ...]
    """未终局锁定帧过渡层条目族(锁定条目在前,候选序跟随;
    cw_intention.transition_active_entries 单一源——终局锁定帧
    过渡层退役恒空元组)。"""
    current_board: dict[str, str]
    """现板面(名 → 现排;稳定键输入 = 与现板面一致数,名+排粒度)。"""


# ============================================================ 评分函数(正本 §1.1)


def _fallback_tier_index(bond: str, head_count: int) -> int:
    """人数阈值 → 档序(FACTIONS.tiers 中 ≥ 人数的最小档序;1 基)。

    Comp.faction_reqs 各档值 = 人数阈值(字段契约「几人激活算
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
    板上其余单位)+ 装备贡献四合一,正本 §1.1 羁绊计数口径——用户确认
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
    """线的 L1 键组:档 0 每键一组(终局候选/终局锁定/过渡条目同构,
    正本 §1.2 段 1)。"""
    if comp is None:
        return ()
    return tuple((k,) for k in comp.core_faction_reqs)


def selection_score(panel: DeploySearchPanel,
                    units: list[SearchUnit],
                    line_comp: Comp | None,
                    line_keys: tuple[str, ...],
                    tag_cache: dict[str, tuple[str, ...]] | None = None,
                    ) -> tuple[float, float, int]:
    """选人分全量终评(正本 §1.1 评分函数;段 3 对每个完整候选板重算——
    DP 组得分只是候选生成内部度量,本函数才是最终板面分,D7 补问 5)。

    返回 (L1, L2, L3) 三层分数(层间数量级隔离,调用方字典序承载):
    - L1 = 两层支配编码:named 层(点名件在场率,统一表达式 = 定义件/core,
      与 form_progress 同式)× 10⁹ + 档位层(加权平均 of f(角色完成度 ×
      档位完成度),权重 = 目标档激活人数)× 10⁸——层间域差保证任何满
      点名件板恒压任何缺点名件板;分族分支(空羁绊线 core∪shared
      口径,保持 10⁹ 归一域)见函数体;
    - L2 = 加分层档位完成度加权平均 × 10⁶(仅锁定窗;键集 = 仅
      ``bonus_faction_reqs``——flex_factions 恒 L3,D3-1);
    - L3 = 计数制单位序(羁绊键按已达档、万金油按件)。
    """
    counts = _tag_counts(units, tag_cache)
    names = {u.char_id for u in units}
    locked = panel.locked

    # ---- L1(主目标羁绊层;两层支配编码:named 层 ×10⁹ 严格支配档位
    # ---- 层 ×10⁸——原 required 灭零特判的防形态「缺点名件板不得
    # ---- 赢满点名件板」由层间域差承载,层内各留连续比较面)----
    l1 = 0.0
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
            # 裸键组(无 Comp 上下文;生产不再产裸键——过渡条目
            # 与终局线均以 Comp 入枚举)。
            groups = tuple((k,) for k in line_keys)
    if groups:
        l1_num = 0.0
        l1_den = 0
        for group in groups:
            best_f = 0.0
            best_w = 1
            for k in group:
                if comp is not None and k in comp.core_faction_reqs:
                    # Comp 条目键(终局候选/终局锁定/过渡条目同构:
                    # 档位完成度经注册表档序)。
                    head = int(comp.core_faction_reqs.get(k, 1))
                    w = max(head, 1)
                    tier_target = _fallback_tier_index(k, head)
                    ach = _achieved_tiers(k, counts.get(k, 0))
                    tier_done = ach / max(tier_target, 1)
                    char_done = min(counts.get(k, 0) / max(head, 1), 1.0)
                    f = char_done * tier_done
                if f * w > best_f * best_w:
                    best_f, best_w = f, w
            l1_num += best_f * best_w
            l1_den += best_w
        tier_rate = (l1_num / l1_den) if l1_den else 0.0
        # named 层(点名件在场率;独立分子分母,不进档位层加权平均
        # ——named_units 统一表达式单一源(cw_comps,与 form_progress 折条
        # 共用):终局单定义件 = core[0] / 过渡 core 全员;裸键组无 Comp 上下文
        # → 无点名件,named_rate = 0)。
        named = named_units(comp)
        named_rate = (sum(1 for n_ in named if n_ in names)
                      / len(named)) if named else 0.0
        l1 = named_rate * _L1_NAMED_SCALE + tier_rate * _L1_TIER_SCALE
    elif locked and comp is not None:
        # 空羁绊线(反甲流档 0 空 ∧ factions=[]):L1 由角色
        # 完成度单独承载(b≡1),分母 = core∪shared 总数、分子 =
        # 其在场数(D2-3 修订——羁绊族口径对该线无源,改阵容成员
        # 口径)。保持 10⁹ 归一域原样(锁定窗单线无跨线比较面,
        # 免动 margin 遥测/快照域);不挂 named 层——members 分子
        # 已含定义件(定义件 ∈ members,建库断言③),挂则双计。
        members = set(comp.members)
        l1_den = max(len(members), 1)
        l1_num = float(len(members & names))
        l1 = (l1_num / l1_den) * _L1_SCALE

    # ---- L2(锁定线非核心羁绊层;键集 = 仅 faction_reqs 档 ≥1 合并
    # ---- (bonus_faction_reqs),D3-1)----
    l2 = 0.0
    if locked and panel.locked_comp is not None:
        sub = panel.locked_comp.bonus_faction_reqs
        if sub:
            num = 0.0
            den = 0
            for k, v in sub.items():
                head = int(v)   # 建库校验⑤钉死正整数
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
        panel.locked_comp.bonus_faction_reqs if locked
        and panel.locked_comp is not None else ())
    l3 = 0
    for bond, cnt in counts.items():
        if bond in l1_key_set or bond in l2_key_set:
            continue   # 单归属:L1/L2 键 L3 计分抑制
        ach = _achieved_tiers(bond, cnt)
        if ach <= 0:
            continue
        # (过渡羁绊档条件两态系数随 TRANSITION_TRAITS 消费分支删除
        #  —— 过渡羁绊按普通羁绊归属。)
        coef = (_L3_BUFF_DEBUFF if bond in TIER7_BOND_NAMES
                else _L3_OTHER)
        l3 += ach * coef
    # 万金油按件计(DF-2:万金油组无档结构,按件 ×2)。
    for u in units:
        if u.char_id in CROSS_LINE_KEEP_NAMES:
            l3 += _L3_UNIVERSAL
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
    全取——t=0 与 t=可达档各一套形态,正本 §1.2 段 1 D-15;**空键集
    (空羁绊线)时全前缀**——无档位基准点,required/core 逐件渐进
    形态 = 池序前缀全枚举)。"""
    cuts: set[int] = {0, len(pool)}
    if not keys:
        cuts.update(range(len(pool) + 1))
    for k in keys:
        tiers = FACTIONS[k].tiers if k in FACTIONS else ()
        for t in tiers:
            if t <= len(pool):
                cuts.add(t)
    return sorted(c for c in cuts if c <= len(pool))


def _assign_rows(members: list[SearchUnit], panel: DeploySearchPanel,
                 comp_pos: Comp | None) -> dict[str, str] | None:
    """段 3 排分配(char_positions 强制 → 场上件**现排滞回** →
    deploy_row_pref → back 兜底 + 前排保证 + 前后排容量 + 开拓者形态
    排约束;溢出 = 站位分损失最小者让位〔row_pref 兜底级排序,正本 §1.2 段 3
    牺牲序〕;不可解 → None(容量矛盾,由排分配容量约束排除)。

    现排滞回(正本 §1.1 稳定键「与现板面一致数」的结构化承载,宽域):场上件
    的排偏好起点 = 现排——row_pref 符合度(pos)不压滞回,等分板上现
    板保持原排(结构化滞回);注册表强约束(char_positions)仍最高优先,
    容量溢出时按牺牲序让位。"""
    cp = (getattr(comp_pos, 'char_positions', None) or {})
    prefs: dict[str, str] = {}
    for u in members:
        hit = cp.get(u.char_id)
        if hit is not None:
            # 槽位级值('front@0' 类)经 parse 取排——排分配只消费排维,
            # 槽位维在 target 第三元承载(diff 执行层落位)
            prefs[u.char_id] = parse_char_position(hit)[0]
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
        hit = cp.get(u.char_id)
        return 1 if (hit is not None
                     and parse_char_position(hit)[0] == row) else 0
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
    不进——星变更本就该动板,正本 §1.1 rng 播种)。"""
    cp = (getattr(comp_pos, 'char_positions', None) or {})
    pos = 0
    for u in members:
        hit = cp.get(u.char_id)
        if hit is not None:
            want = parse_char_position(hit)[0]
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
    """局面哈希播种(正本 §1.1 rng 播种:同一状态容器状态 → 同一 rng 序,跨帧稳定;
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
                         margin_out: dict | None = None,
                         ) -> dict[str, tuple[str, int]]:
    """统一部署搜索主入口(三段;纯函数零 IO,接口契约见正本 §1.4)。

    返回 target_board = {角色名: (排, 选定星, 槽位或 None)}(接口契约②,
    载荷星维承载就位粒度名+排+星;槽位维 = char_positions 槽位级登记
    的排内 1 基槽号,None = diff 执行层自适应落位)。候选全不可排
    (容量矛盾,结构不可达防御)→ 返回空 dict(消费端 fail-closed
    按现板定型,申报)。

    ``margin_out`` = 可选次名分量收集出参(挑边差距遥测的私有槽通道;
    遥测正本 = strategy-docs/strategy-telemetry.md ``deploy_margin`` 行:
    段 3 并行收集,纯函数零状态写——传入非 None dict
    且搜索成功时填次名键形;缺省 None = 不收集,虚拟定型调用点
    不传即零开销零写入;搜索返 {} 时保持空 = 调用方据此不落值)。
    """
    rng = random.Random(_situation_seed(panel))
    comp_pos = panel.locked_comp if panel.locked else None
    tag_cache: dict[str, tuple[str, ...]] = {}

    # ---- 段 1 圈人(骨架 = 档位形态集合)----
    def _pool_of(keys: tuple[str, ...],
                 member_names: frozenset[str]) -> list[SearchUnit]:
        """体系/线骨架件池:羁绊标签 ∩ 键系 ∪ 线名单成员,骨架内按
        选件序排序(**锁定线核心优先、逐档**,正本 §1.2 段 1:定义件 >
        core > shared > 标签件——骨架优先圈定义件(engine carry)形态
        由成员序承载;定义件层可达性由建库断言③钉住)。"""
        comp = panel.locked_comp if panel.locked else None
        anchor = carry_anchor(comp) if comp is not None else ''
        core = set(comp.core_chars) if comp is not None else set()
        pool = [u for u in panel.units
                if (_bonds_named(u.char_id) & set(keys)
                    or u.char_id in member_names)]

        def _line_rank(u: SearchUnit) -> int:
            # 圈人分层仅锁定窗生效(未锁定窗恒 2——定义件/core 取自
            # locked_comp,未锁定帧无锁定线承载;定义件空不命中——
            # 合法 char_id 恒非空串)。
            if not panel.locked:
                return 2
            if u.char_id == anchor:
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
        return frozenset(comp.members)


    skeletons: list[tuple[tuple[SearchUnit, ...], Comp | None,
                          tuple[str, ...]]] = []
    if panel.locked and panel.locked_comp is not None:
        # 终局锁定窗(换轴:旧 P1 锁定窗过渡家族骨架枚举随过渡层
        # 「终局锁定即退役」删除——锁定帧过渡层恒空)。
        comp = panel.locked_comp
        line_keys = _line_keys_of(comp)
        core_hand = {u.char_id for u in panel.units
                     if u.char_id in set(comp.core_chars)}
        if core_hand or not line_keys:
            pool = _pool_of(line_keys, _member_names_of(comp))
            for cut in _prefix_cuts(pool, line_keys):
                skeletons.append((tuple(pool[:cut]), comp, line_keys))
    else:
        # 未终局锁定:过渡层条目骨架(与终局锁定窗同构——条目 Comp
        # 喂 comp 半边,档位完成度经注册表档序;锁定条目在前)∪
        # 终局候选三线(换轴:原 P2+ 位面门废除,未终局锁定帧同枚举)。
        for comp in panel.transition_comps:
            keys = _line_keys_of(comp)
            pool = _pool_of(keys, _member_names_of(comp))
            for cut in _prefix_cuts(pool, keys):
                skeletons.append((tuple(pool[:cut]), comp, keys))
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
        panel.locked_comp.bonus_faction_reqs if panel.locked
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
        """分组背包 DP 补人候选(正本 §1.2 段 2 设计基线的组间联合形态;
        骨架 + 线内件优先占席(D8-3)后,剩余席位
        按「羁绊分组 + 万金油特组」背包联合分配):补贪心序与单组
        变体都覆盖不到的**多组部分凑档**形态(跨组增益捕获——两组各差
        1-2 件成档时,贪心全局序可能交错取件致两组成档皆失,单组变体只
        保一组;DP 按组值增量联合取优)。

        近似口径(与正本 §1.2 段 2 近似申报同款,终评兜底):组值 = 组键
        已达档增量 × L3 系数(首标签归属单键计,件次标签贡献不可见——
        段 3 全量终评兜底);万金油组按件 ×2。

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
        # 分组(首羁绊标签归属;万金油特组按件)。
        groups: dict[str, list[SearchUnit]] = {}
        for u in rest2:
            if u.char_id in CROSS_LINE_KEEP_NAMES:
                groups.setdefault('\0universal', []).append(u)
                continue
            bonds = _bonds_named(u.char_id)
            if bonds:
                groups.setdefault(sorted(bonds)[0], []).append(u)

        # (过渡羁绊组值系数 facet 随 TRANSITION_TRAITS 消费分支删除:
        #  过渡条目骨架已进段 1 枚举,组值按普通羁绊归属。)
        def _l3_coef(bond: str) -> int:
            return (_L3_BUFF_DEBUFF if bond in TIER7_BOND_NAMES
                    else _L3_OTHER)

        def _group_values() -> dict[str, list[int]]:
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
                        vs.append(delta * _l3_coef(g))
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
        # (相位枚举〔锁定窗过渡组 ×4/×1 两相位〕随过渡组系数 facet
        #  删除收敛为单相位——两相位组值恒同。)
        seen_mix: set[tuple] = set()
        for _phase in (False,):
            take = _knapsack(_group_values())
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
    # 次名分量并行收集(纯观测,挑边差距遥测的私有槽通道;条目 = (全键,
    # 成员键集, 三层分, 排序板签名)——收集面只加变量,评分/比较/取优
    # 逻辑逐行不动;margin_out None 时零收集零开销)。
    _scored: list[tuple[tuple, frozenset[str], tuple[float, float, int],
                        list[str]]] = []
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
        if margin_out is not None:
            _scored.append((key, frozenset(u.key for u in members),
                            (l1, l2, l3),
                            sorted(u.char_id for u in members)))
        if best_key is None or key > best_key:
            best_key = key
            best_out = (members, rows)
    if best_out is None:
        return {}
    if margin_out is not None:
        # 挑战者 = 成员集与胜者不同的最高板(排序键 = 段 3 全键同款,
        # 禁另立排序;dedup 键含评估上下文 → 同成员集
        # 不同 comp/keys 的板不算挑战者)。无挑战者 → 三键 null 形态
        # (与尾键决胜的 0/0 区分);三层全同(尾键决胜)→ 首异层 0/层差 0。
        _winner = max(_scored, key=lambda t: t[0])
        _chal = max((t for t in _scored if t[1] != _winner[1]),
                    key=lambda t: t[0], default=None)
        if _chal is None:
            margin_out.update(runner_up=None, first_diff_layer=None,
                              layer_gap=None)
        else:
            _layer, _gap = 0, 0
            for _i in range(3):
                if _winner[2][_i] != _chal[2][_i]:
                    _layer, _gap = _i + 1, _winner[2][_i] - _chal[2][_i]
                    break
            # layer_gap 数值语义(required-deployed-retirement 后):首异层
            # 为 L1 时 = named 层(×10⁹)与档位层(×10⁸)的混合差——数值
            # 落 10⁹ 段 = 点名件在场率差,10⁸ 段 = 档位完成度差(同
            # named_rate 板间),遥测判读按段拆语义。
            margin_out.update(runner_up=_chal[3], first_diff_layer=_layer,
                              layer_gap=_gap)
    members, rows = best_out
    # target 第三元 = 槽位级登记的排内 1 基槽号(char_positions 经
    # parse_char_position;无登记/排级 = None → diff 执行层自适应落位)。
    # 槽位不进站位分/排分配(搜索只定排与成员,槽位是执行层落位约束)
    _cp = (getattr(comp_pos, 'char_positions', None) or {}) \
        if comp_pos is not None else {}
    _slots = {
        n: parse_char_position(v)[1] for n, v in _cp.items()}
    return {u.char_id: (rows[u.char_id], u.star,
                        _slots.get(u.char_id)) for u in members}



# ============================================================ 生产装配(段 0)


def build_deploy_panel(session: StrategySession, gs: GameState,
                       frame: MandateFrame | None = None,
                       ) -> DeploySearchPanel:
    """搜索面板生产装配(状态容器读口全列一次现取;正本 §1.1 虚拟面板字段域)。

    段 0 过滤在此执行:上场锁(uid 命中记录;虚拟件 uid=None 名
    命中锁名单即视为锁,fail-closed)/召唤物系统件(cost=0,固定后台
    末位剔除)/未知身份件不入枚举但占 K 占格(正本 §1.2 段 0)。
    **无窗口硬约束**(entry_signals 整体退役,2026-11 用户终裁):上场
    时机 = 骨架/L1 完成度自适应(终局件在未成型面板自然被 L1 递减挤出)。
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
    from sr_od.application.currency_war.strategies.impl.mandate_v1.line_select import (
        compute_candidates,
        opening_ctx_of,
    )
    from sr_od.application.currency_war.strategies.impl.mandate_v1.mandate_state import (
        state_of,
    )

    st = state_of(session)
    # 锁定窗直读调用方 session 的策略状态(line_members_view 的
    # state_of(gs) 依赖 gs.strategy_state 接入调用,虚拟路径调用方
    # (shop 评估/sell_candidates 传 gs 当 session)不保证接入调用——
    # 统一走 session 槽,判据 = target_comp 非空即锁定,与
    # line_members_view 同判不同宿主)。
    locked = getattr(st, 'target_comp', None) is not None
    locked_comp = getattr(st, 'target_comp', None) if locked else None
    # 过渡层条目族(换轴:窗口 = 未终局锁定,任意位面;终局锁定帧
    # 过渡层退役恒空——条目域单一源 = transition_active_entries)。
    transition_comps = () if locked else transition_active_entries(st)
    candidate_comps: tuple = ()
    if not locked:
        held: set[str] = set()
        for u in _all_units(gs):
            if u.char_id:
                held.add(str(u.char_id))
        cand_names = compute_candidates(frozenset(held),
                                        opening_ctx_of(gs))
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
        # 银狼落场后形态(正本 §1.1:3★ 上场即下档 1★——现档 = 5 费封顶时
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
        transition_comps=transition_comps,
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
    生产面板状态容器读口 + 虚拟 bench/场上单位替换,正本 §1.4 虚拟路径契约)。

    ``bench_slots`` = 虚拟 bench 槽位条目列表(升星连锁模拟产物,
    SimAcquisition.bench 的 BenchSlot 半);``field_units`` = 虚拟场
    上单位(紧缩序,排映射 = 现板同名保持原排、新上者 back 兜底)。
    锁/容量过滤与生产装配同核(段 0 同一过滤管道)。
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

    units: list[SearchUnit] = []
    for u in field_units:
        if u is None or not (u.char_id or ''):
            continue
        cid = str(u.char_id)
        uid = getattr(u, 'uid', None)
        if (uid is not None and uid in lock_uids) or cid in lock_names:
            continue
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
        candidate_comps=panel.candidate_comps,
        transition_comps=panel.transition_comps,
        current_board={
            str(u.char_id): panel.current_board.get(str(u.char_id), 'back')
            for u in field_units if u is not None and u.char_id})
