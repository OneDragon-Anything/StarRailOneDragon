"""货币战争 变宝为废·牺牲合成先行(装备合成排序器,决策层)。

**机制真值(单一源 = ``data/affix_effects_data.AFFIX_EFFECTS['变宝为废']``,
游戏内词缀效果原文实采)**:「每个位面开始时,首次合成的进阶装备会有 50% 的
概率变成垃圾袋」——粒度 = **每位面各一次**(P1/P2/P3 的首次进阶合成各自
承担 50% 垃圾化风险),产物 = 垃圾袋。对策(用户建议)= 牺牲合成先行:
每位面的首次进阶合成之前,先用次要合成对(回收合格 1★ 死库存对,不碰
主线凑件)做一次牺牲合成,把该位面的垃圾化判定消耗掉。

**环境判据(读取链)**:简报词缀(StartCurrencyWarMatch / battle_loop 位面
简报分支 → ``ctx.cw_briefing_affixes``)∪ 位面详情词缀横条随采
(CollectPlaneIntel)→ ``session.briefing_affixes`` → ``state.enemy_affixes``。
本模块只消费 ``enemy_affixes`` 名单做 contains 判定;**读不到(空/None)=
无该环境**,安全默认不启用。

**架构落点**:``cw_comps.equip_allocation``(M7 装备分配,「穿着即合成」的
唯一决策排序点)产出分配序列后,本模块做**纯后处理重排/推迟**:
- 有牺牲对 → 牺牲对两条分配移到队首(拖拽序 = 合成事件序,牺牲合成先完成);
- 无牺牲对 → 高价值合成的完成件本帧不出分配(件留 owned,等死库存对到场;
  推迟一帧上限,防无限等)。
执行层(operations/prep/equip_all.py 的 drag/验穿链)零改动。

**位面消耗语义**:某位面的首次合成判定一旦消耗(本排序器发射牺牲合成,
或该位面推迟预算用尽后放行),本位面内不再重排/推迟
(``session.junk_first_done_plane`` 记录,与 ``state.plane`` 对账;位面
读不到时退化为整局一次,保守侧)。残余边界:排序器视野外的合成事件
(如 C6 转移拖拽凑齐配方)会提前消耗位面判定而未被记账——代价仅为
多保守一帧,不产生错误合成。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.data.cw_synthesis import (
    RESERVED_COMPONENTS,
    recycle_qualified,
    self_advance,
    synthesize_target,
)

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_comps import Comp

# 环境词缀识别名(画面 OCR 原名;affix_effects_data 注册表同名)
JUNK_FIRST_AFFIX: str = '变宝为废'

# 推迟一帧上限(每位面;依据=机制真值 50% 垃圾化损失 ≫ 一帧推迟成本,
# 且推迟只在「无牺牲对」时发生;上限防死库存永不到场时无限推迟)
JUNK_FIRST_DEFER_BUDGET: int = 1

# session=None(离线/旧栈)的「位面已消耗」哨兵:只重排不推迟(保守降级)
_CONSUMED_UNKNOWN: int = -1


def junk_first_env_active(enemy_affixes: list[str] | None) -> bool:
    """「变宝为废」在场判据(state.enemy_affixes 名单 contains;读不到=无环境)。"""
    return JUNK_FIRST_AFFIX in set(enemy_affixes or [])


def _is_basic(name: str) -> bool:
    """基础件判定(单一源 = RESERVED_COMPONENTS,全 8 件含光能电池)。"""
    return name in RESERVED_COMPONENTS


def _pair_product(a: str, b: str) -> str | None:
    """两基础件的合成产物(交叉 + 自配;非基础件/不成对 → None)。"""
    if a == b:
        return self_advance(a)
    return synthesize_target(a, b)


def worn_basics_by_char(deployed: list,
                        occupied: dict[tuple[str, int], list[str]] | None,
                        ) -> dict[str, list[str]]:
    """(row,slot) 占用 + deployed 身份 → 角色名 → 已穿基础件名单。

    与 cw_comps.equip_allocation 内部 worn_basics 投影同构(ADR-0391 判定域
    =角色名);本模块只读消费,不改分配器(分配器语义由其自身测试锁辖)。
    """
    occ = occupied or {}
    worn: dict[str, list[str]] = {}
    for d in deployed:
        n = getattr(d, 'char_id', None)
        if not n:
            continue
        key = (getattr(d, 'position_pref', '') or '',
               int(getattr(d, 'slot', 0) or 0))
        for w in occ.get(key, []):
            if _is_basic(w):
                worn.setdefault(n, []).append(w)
    return worn


def find_high_value_completions(alloc: list[tuple[str, str]],
                                worn: dict[str, list[str]],
                                comp: Comp) -> list[int]:
    """分配序列中会**完成一次高价值合成**的下标(按执行序,可重复模拟)。

    高价值 = 例外①配对(ADR-0391 同判):穿者 ∈ core_chars 且产物 ∈
    key_equips——正是变宝为废环境下最不该被垃圾化的合成。判定沿 alloc
    顺序推进 worn 副本(画面已穿基础件 + 本趟已分配),某条分配使该角色
    身上首次凑齐 key 配对 → 记完成下标。纯函数,不 mutate 输入。
    """
    key_set = set(comp.key_equips) if comp is not None else set()
    core_set = set(comp.core_chars) if comp is not None else set()
    local: dict[str, list[str]] = {k: list(v) for k, v in worn.items()}
    completions: list[int] = []
    for idx, (char, item) in enumerate(alloc):
        if not _is_basic(item) or char not in core_set:
            continue
        for b2 in local.get(char, ()):
            y = _pair_product(item, b2)
            if y is not None and y in key_set:
                completions.append(idx)
                break
        local.setdefault(char, []).append(item)
    return completions


def find_sacrifice_pair(alloc: list[tuple[str, str]],
                        worn: dict[str, list[str]],
                        comp: Comp) -> tuple[str, str, str] | None:
    """牺牲合成对:非 core 角色「已穿基础件 ∪ 本趟分配基础件」中的
    回收合格配方对。

    判据(不碰主线凑件,P14 定理 3 单一源):两件都 ∈ ``recycle_qualified``
    (不是任何目标进阶的组件)且互为配方(产物必然 ∉ key_equips,P14 定理 3
    反证)且穿者非 core(回收线例外②同域)。 worn = 角色已穿基础件
    (``worn_basics_by_char`` 投影)——对的两件可一件已穿(前帧)+ 一件本趟
    分配,或两件同趟共位。返回 (角色, 件a, 件b) 或 None;件a/件b 至少一件
    在本趟 alloc 内(否则本帧无事可做,不返回)。
    """
    rq = recycle_qualified(list(comp.key_equips) if comp is not None else None)
    core_set = set(comp.core_chars) if comp is not None else set()
    by_char: dict[str, list[str]] = {}
    for char, item in alloc:
        if _is_basic(item) and char not in core_set:
            by_char.setdefault(char, []).append(item)
    for char in list(by_char):
        worn_items = [w for w in worn.get(char, ()) if w in rq]
        by_char[char] = worn_items + by_char[char]
    for char, items in by_char.items():
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                a, b = items[i], items[j]
                if a in rq and b in rq and _pair_product(a, b) is not None:
                    alloc_items = {e for c, e in alloc if c == char}
                    if a in alloc_items or b in alloc_items:
                        return char, a, b
    return None


def apply_junk_first(alloc: list[tuple[str, str]],
                     worn: dict[str, list[str]],
                     comp: Comp,
                     env_active: bool,
                     defer_budget: int) -> tuple[list[tuple[str, str]], str]:
    """牺牲合成先行重排/推迟(纯后处理;返回 (新分配, 动作))。

    动作域:
    - ``inactive``:环境不在场 / 无 comp / 无 key_equips → 原样返回;
    - ``no_high_value``:本趟分配不会完成任何高价值合成 → 原样返回
      (没有要保的合成,牺牲无意义);
    - ``sacrifice_first``:存在牺牲对 → 该对两条分配移到队首(其余保序
      稳定后移)——拖拽序 = 合成事件序,牺牲合成先消耗垃圾化;
    - ``deferred``:无牺牲对且有预算 → 逐个移除高价值合成的完成件直至
      无完成(件留 owned,等死库存对到场;移除一个后重模拟,防同角色
      多对连环完成);
    - ``budget_exhausted``:无牺牲对且无预算 → 原样返回(接受该位面 50%
      垃圾化风险;预算上限防死库存永不到场时无限推迟)。
    """
    if not env_active or comp is None or not comp.key_equips:
        return list(alloc), 'inactive'
    if not find_high_value_completions(alloc, worn, comp):
        return list(alloc), 'no_high_value'
    sp = find_sacrifice_pair(alloc, worn, comp)
    if sp is not None:
        char_s, a, b = sp
        front: list[tuple[str, str]] = []
        rest: list[tuple[str, str]] = []
        for c, e in alloc:
            if c == char_s and e in (a, b) and len(front) < 2:
                front.append((c, e))
                continue
            rest.append((c, e))
        return front + rest, 'sacrifice_first'
    if defer_budget <= 0:
        return list(alloc), 'budget_exhausted'
    new_alloc = list(alloc)
    local = {k: list(v) for k, v in worn.items()}
    while True:
        idx_list = find_high_value_completions(new_alloc, local, comp)
        if not idx_list:
            break
        new_alloc.pop(idx_list[0])
    return new_alloc, 'deferred'


def junk_first_allocation(session,
                          registry,
                          comp: Comp | None,
                          deployed: list,
                          owned: list[str],
                          occupied: dict[tuple[str, int], list[str]] | None,
                          enemy_affixes: list[str] | None,
                          base_alloc: list[tuple[str, str]] | None = None,
                          ) -> list[tuple[str, str]]:
    """EquipAll 决策入口包装:基分配(语义不变)→ 变宝为废后处理。

    ``base_alloc``:装备环境管道接入(设计 §2.2 量→序)——调用方已算好基分配
    (可经 fill3 量变体改派后)时直传,本函数不再重复计算 equip_allocation;
    None(缺省,含既有测试/旧调用)→ 内部自算,行为逐位不变。

    - registry 开关关(默认)→ 基分配原样返回(**零漂移锚**);
    - 环境不在场 → 同上;
    - **位面消耗**:机制 = 每位面首次合成各判定一次(affix_effects_data
      真值);当前位面已消耗(session.junk_first_done_plane == state.plane)
      → 基分配原样。发射牺牲合成或发生推迟后记账当前位面;位面读不到
      → 退化为整局一次(保守侧,防每帧重复消耗/无限推迟)。
    session/registry 缺失(旧栈/离线)→ 基分配原样(保守降级:
    session=None 时预算按耗尽计,只重排不推迟)。
    """
    from sr_od.application.currency_war.kernel.cw_comps import equip_allocation
    base = (base_alloc if base_alloc is not None
            else equip_allocation(comp, deployed, owned, occupied))
    enabled = bool(getattr(registry, 'junk_first_sacrifice_enabled', False))
    if not enabled or comp is None:
        return base
    env = junk_first_env_active(enemy_affixes)
    if not env:
        return base
    worn = worn_basics_by_char(deployed, occupied)
    plane = (getattr(getattr(session, 'last_state', None), 'plane', None)
             if session is not None else None)
    done = (getattr(session, 'junk_first_done_plane', None)
            if session is not None else _CONSUMED_UNKNOWN)
    if done == _CONSUMED_UNKNOWN:
        consumed = True    # 位面不可读态下已消耗过 → 整局一次(防无限推迟)
    elif done is None:
        consumed = False
    elif plane is None:
        consumed = False   # 位面不可读:按新位面保护(防漏保护;消耗后记哨兵)
    else:
        consumed = (done == plane)
    budget = 0 if (session is None or consumed) else JUNK_FIRST_DEFER_BUDGET
    new_alloc, action = apply_junk_first(base, worn, comp, env, budget)
    if action in ('sacrifice_first', 'deferred') and session is not None:
        session.junk_first_done_plane = (plane if plane is not None
                                         else _CONSUMED_UNKNOWN)
    if action not in ('inactive', 'no_high_value'):
        log.info('[cw-equip] 变宝为废牺牲合成: action=%s plane=%s alloc=%d→%d '
                 '(机制真值=affix_effects_data:每位面首次进阶合成 50%% 变垃圾袋)',
                 action, plane, len(base), len(new_alloc))
    return new_alloc
