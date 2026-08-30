"""货币战争 变宝为废·牺牲合成先行(装备合成排序器,决策层)。

**机制单一源** = ``docs/game/currency_war/research/变宝为废-首次合成垃圾化.md``
(用户口述:词缀「变宝为废」生效时,**第一次装备合成**有几率垃圾化产物;
先消耗掉任意一次合成,后续合成不再触发)。对策 = 用户建议「牺牲合成先行」:
高价值合成(核心件进阶)之前,先用场上次要合成对(回收合格 1★ 死库存对,
不碰主线凑件)做一次牺牲合成,把垃圾化概率消耗掉。

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

**缺数据项(挂账,禁拍死)**:垃圾化概率值、「第一次」判定粒度(每局/每位面/
每装备槽)、垃圾化表现形态——均待实机样本(见机制单一源文档挂账节)。本模块
不引入任何概率常数;推迟上限取口述「推迟一帧」(JUNK_FIRST_DEFER_BUDGET=1)。
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

# 推迟一帧上限(整局累计;出处=机制单一源文档对策节「推迟一帧上限,防无限等」)
JUNK_FIRST_DEFER_BUDGET: int = 1


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
    - ``budget_exhausted``:无牺牲对且无预算 → 原样返回(接受垃圾化风险;
      口述对策反向约束「推迟成本 vs 垃圾化损失未量化」,预算上限防无限等)。
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
                          ) -> list[tuple[str, str]]:
    """EquipAll 决策入口包装:基分配(语义不变)→ 变宝为废后处理。

    - registry 开关关(默认)→ 基分配原样返回(**零漂移锚**);
    - 环境不在场 → 同上;
    - 推迟计数宿主 = ``session.junk_first_defers_used``(整局累计,上限
      JUNK_FIRST_DEFER_BUDGET);实际发生推迟才 +1。
    session/registry 缺失(旧栈/离线)→ 基分配原样(保守降级:
    session=None 时预算按耗尽计,只重排不推迟)。
    """
    from sr_od.application.currency_war.kernel.cw_comps import equip_allocation
    base = equip_allocation(comp, deployed, owned, occupied)
    enabled = bool(getattr(registry, 'junk_first_sacrifice_enabled', False))
    if not enabled or comp is None:
        return base
    env = junk_first_env_active(enemy_affixes)
    if not env:
        return base
    worn = worn_basics_by_char(deployed, occupied)
    if session is not None:
        used = int(getattr(session, 'junk_first_defers_used', 0) or 0)
    else:
        used = JUNK_FIRST_DEFER_BUDGET
    new_alloc, action = apply_junk_first(base, worn, comp, env,
                                         JUNK_FIRST_DEFER_BUDGET - used)
    if action == 'deferred' and session is not None:
        session.junk_first_defers_used = used + 1
    if action not in ('inactive', 'no_high_value'):
        log.info('[cw-equip] 变宝为废牺牲合成: action=%s alloc=%d→%d '
                 '(缺数据挂账:垃圾化概率/判定粒度未量化,见 research/'
                 '变宝为废-首次合成垃圾化.md)', action, len(base), len(new_alloc))
    return new_alloc
