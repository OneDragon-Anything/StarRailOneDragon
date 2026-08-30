"""货币战争 装备环境感知变体:软弱无力/额外打击 → 穿满向 fill-to-3(决策层纯后处理)。

**机制真值(单一源 = ``data/affix_effects_data.AFFIX_EFFECTS``,游戏内词缀
效果原文实采)**:
- 「软弱无力」:「没有穿戴3件装备的角色及其忆灵,造成的伤害为原伤害的80%.」
  —— 判据是**角色级穿满数(3 件)**:同样 6 件装备,「3+3」全员合规,
  「2+2+2」三人全吃 80% 罚 → 分配的**集中度**(每人穿几件)成为决策变量;
- 「额外打击」:「我方队员每有1个空缺装备栏,受到敌人攻击后,额外受到本次
  攻击伤害8%的真实伤害。」—— 与软弱无力互为镜像(罚空栏承伤):
  受击频率高的位(前排/嘲讽)空栏最贵 → 凑 3 的优先对象=前排先于输出位。

两轴同指「提高单人穿满率」,合并为一个 fill-to-3 量变体(设计件
.debug/temp/currency_war/w880_equip_env_design/DESIGN.md §2/§3.1):
基分配 ``cw_comps.equip_allocation`` 语义不变(件给谁的 comp 意图),本模块
只在其产出后做**改派后处理**——把分配序列中非命脉散件改派给「差件凑满 3」
的角色,凑到阈值为止。

**环境判据(读取链,同 cw_junk_first.W861 语义)**:简报词缀 ∪ 位面详情随采
→ ``session.briefing_affixes`` → ``state.enemy_affixes``。读取点唯一 =
``build_equip_env_signals``(equip_all 决策调用处构造一次打包传递,变体
函数不再各自摸 state);**读不到(空/None)= 无环境,安全默认不启用**。

**防护线(设计 §3.1)**:
1. 只改派「非 key_equips 且非主线需求组件」的散件——key 凑件与主线凑件
   (``component_demand(key_equips)``)不可挪,语义同 junk_first「不碰主线凑件」;
2. 基础件改派过 ``cw_comps._pairing_guard_ok`` 防误合成守卫(穿着触发自动
   合成无确认,非预期配对不可逆消耗两件组件;守卫判定单源在 cw_comps);
3. 过渡期 hold(非生锈豁免态)不激活 fill——hold 语义(攒给成型核心)优先,
   调用侧以 ``hold_active`` 传入,变体内不重复判 hold。

**执行链零触碰**:本模块是纯决策层(排序器后处理),equip_all 的 drag/验穿
链(W849)零改动;开关关/环境不在场/hold 在场 → 分配序列逐位原样(零漂移锚)。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.data.cw_synthesis import component_demand

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_comps import Comp

# 环境词缀识别名(画面 OCR 原名;affix_effects_data 注册表同名;任一在场即激活)
EQUIP_ENV_FILL3_AFFIXES: tuple[str, str] = ('软弱无力', '额外打击')


@dataclass(frozen=True)
class EquipEnvSignals:
    """装备环境信号包(equip_all 决策调用处构造一次,变体共享;设计 §2.2)。

    ``enemy_affixes`` = state.enemy_affixes(简报∪随采;state 缺失=空集);
    ``plane``/``round_num`` = state 记账/窗口字段(预留:变宝为废位面记账与
    P1 hold 窗口判定迁入管道时消费;本批 fill3 变体不消费)。
    """
    enemy_affixes: frozenset[str]
    plane: int | None
    round_num: int | None


def build_equip_env_signals(state) -> EquipEnvSignals:
    """state → 信号包(唯一读取点;state 缺失/字段缺失 = 安全默认,不抛错)。

    ``state`` = ``session.last_state``(可为 None,离线/旧栈);字段经 getattr
    宽读,缺 = None / 空集。**不在变体内读 state**——所有环境信息经本函数
    一次性打包,变体保持纯函数(可离线锁)。
    """
    affixes = list(getattr(state, 'enemy_affixes', None) or []) if state is not None else []
    plane = getattr(state, 'plane', None) if state is not None else None
    round_num = getattr(state, 'round_num', None) if state is not None else None
    return EquipEnvSignals(
        enemy_affixes=frozenset(affixes),
        plane=int(plane) if plane is not None else None,
        round_num=int(round_num) if round_num is not None else None,
    )


def fill3_env_active(signals: EquipEnvSignals) -> bool:
    """fill-to-3 环境判据:软弱无力/额外打击任一在场(contains;读不到=无环境)。"""
    return any(a in signals.enemy_affixes for a in EQUIP_ENV_FILL3_AFFIXES)


def apply_fill3(alloc: list[tuple[str, str]],
                deployed: list,
                occupied: dict[tuple[str, int], list[str]] | None,
                comp: Comp | None,
                fill_target: int = 3,
                ) -> tuple[list[tuple[str, str]], int]:
    """fill-to-3 改派(纯函数;返回 (新分配, 改派件数))。

    语义(设计 §3.1 两轴):
    - **集中度轴(软弱无力)**:凑 3 目标按「已穿件数多者先」——把散件改派给
      最接近 3 件的角色(集中凑满),替代「均匀分散」;
    - **承伤序轴(额外打击)**:同分下前排(受击频率高位)先于后排,输出核心
      (``comp.core_chars``)先于非 core——前排空栏最贵,核心输出吃 80% 罚最实。

    改派对象 = alloc 内「非 key_equips 且非主线需求组件」的散件(原序遍历);
    目标容量 = fill_target −(已穿 + 本趟已改派);基础件过防误合成守卫。
    comp=None(无身份信息,无法判定保护集)→ 原样返回(保守降级)。
    成员无损(只改 (char, item) 的 char,不增删)。
    """
    from sr_od.application.currency_war.data.cw_synthesis import (
        RESERVED_COMPONENTS,
        recycle_qualified,
    )
    from sr_od.application.currency_war.kernel.cw_comps import (
        EQUIP_CAPACITY,
        _pairing_guard_ok,
    )
    if comp is None or not alloc:
        return list(alloc), 0
    target_n = max(0, min(int(fill_target), EQUIP_CAPACITY))
    occ = occupied or {}
    key_set = set(comp.key_equips)
    core_set = set(comp.core_chars)
    protected = key_set | set(component_demand(list(comp.key_equips)))
    _is_basic = RESERVED_COMPONENTS.__contains__
    rq = recycle_qualified(list(comp.key_equips))

    # 已穿投影(全件计数 + 基础件名单供配对守卫),判定域=角色名(同 equip_allocation)
    worn_count: dict[str, int] = {}
    worn_basics: dict[str, list[str]] = {}
    deploy_idx: dict[str, int] = {}
    for d in deployed:
        n = getattr(d, 'char_id', None)
        if not n:
            continue
        if n not in deploy_idx:
            deploy_idx[n] = len(deploy_idx)
        row = getattr(d, 'position_pref', '') or ''
        slot = int(getattr(d, 'slot', 0) or 0)
        items = occ.get((row, slot), [])
        worn_count[n] = worn_count.get(n, 0) + len(items)
        for w in items:
            if _is_basic(w):
                worn_basics.setdefault(n, []).append(w)

    # 凑 3 目标序:前排先(承伤序)→ core 先(输出侧)→ 已穿多者先(集中度)→ deployed 序
    def _target_key(n: str) -> tuple[int, int, int, int]:
        row = next(((getattr(d, 'position_pref', '') or '')
                    for d in deployed if getattr(d, 'char_id', None) == n), '')
        return (0 if row == 'front' else 1,
                0 if n in core_set else 1,
                -worn_count.get(n, 0),
                deploy_idx.get(n, len(deploy_idx)))

    targets = sorted((n for n, c in worn_count.items() if c < target_n),
                     key=_target_key)
    assigned: dict[str, int] = dict.fromkeys(targets, 0)
    out = list(alloc)
    moved = 0
    local_basics: dict[str, list[str]] = {k: list(v) for k, v in worn_basics.items()}
    for idx, (_char, item) in enumerate(alloc):
        if item in protected:
            continue
        for t in targets:
            if worn_count.get(t, 0) + assigned[t] >= target_n:
                continue
            if _is_basic(item) and not _pairing_guard_ok(
                    local_basics, t, item, key_set, core_set, set(rq)):
                if t in core_set:
                    # 可行性守卫 > 排序轴(ADR-0502 辖域优先链):core 首选被
                    # 守卫淘汰落次选属正常让位;debug 披露供实机挂账
                    # 「让位事件频次与差分代价」(是否值得为 core 破例的数据)。
                    log.debug('[cw-equip] fill3 pairing-guard yield: core=%s '
                              'item=%s falls to next candidate', t, item)
                continue    # 该改派会触发非预期合成 → 换目标/放弃本件
            out[idx] = (t, item)
            assigned[t] += 1
            moved += 1
            if _is_basic(item):
                local_basics.setdefault(t, []).append(item)
            break
    return out, moved


def fill3_allocation(registry,
                     comp: Comp | None,
                     deployed: list,
                     alloc: list[tuple[str, str]],
                     occupied: dict[tuple[str, int], list[str]] | None,
                     signals: EquipEnvSignals,
                     hold_active: bool,
                     ) -> tuple[list[tuple[str, str]], str]:
    """EquipAll 决策入口包装:fill-to-3 量变体(软弱无力+额外打击合并)。

    门序(全关 = 基分配原样,零漂移锚):
    - registry 开关关(默认,生命周期第 1 态)→ ``inactive``;
    - 环境不在场(两词缀均不在 enemy_affixes)→ ``inactive``;
    - hold 在场(过渡期 hold 且非生锈豁免,调用侧判定传入)→ ``hold_active``
      (hold 语义「攒给成型核心」优先于穿满向,防两套意图打架);
    - comp 缺失 / 无凑 3 空缺 / 无可改派散件 → ``no_gap``;
    - 发生改派 → ``filled:<n>``,打统一日志行
      ``[cw-equip] env-variant fill3 action=...``(判读锚点)。
    """
    enabled = bool(getattr(registry, 'equip_env_fill3_enabled', False))
    if not enabled:
        return list(alloc), 'inactive'
    if not fill3_env_active(signals):
        return list(alloc), 'inactive'
    if hold_active:
        return list(alloc), 'hold_active'
    fill_target = int(getattr(registry, 'equip_fill_target', 3))
    new_alloc, moved = apply_fill3(alloc, deployed, occupied, comp, fill_target)
    if moved <= 0:
        return list(alloc), 'no_gap'
    log.info('[cw-equip] env-variant fill3 action=filled:%d target=%d affixes=%s '
             '(机制真值=affix_effects_data:未穿满3件伤害80%%/每空栏承伤+8%%真伤)',
             moved, fill_target, sorted(signals.enemy_affixes))
    return new_alloc, f'filled:{moved}'


def apply_equip_env_variants(signals: EquipEnvSignals,
                             registry,
                             session,
                             comp: Comp | None,
                             deployed: list,
                             owned: list[str],
                             occupied: dict[tuple[str, int], list[str]] | None,
                             hold_active: bool,
                             ) -> tuple[list[tuple[str, str]], list[str]]:
    """装备环境变体管道统一入口(设计 §2.2 门/量/序;EquipAll 唯一调用点)。

    - 基分配 ``equip_allocation`` 只算一次;
    - ①门 = hold/生锈豁免:**不在本函数内改写分配**——门作用于 hold 过滤分支
      (equip_all 既有语义),经 ``hold_active`` 实参(已含生锈豁免组合)辖量变体;
    - ②量 = fill3(``fill3_allocation``,软弱无力/额外打击合并);
    - ③序 = 变宝为废牺牲合成(``junk_first_allocation``,行为不变迁移:改吃
      signals 派生的词缀名单 + 直收②的产出为基分配,位面记账/推迟预算零改动)。

    序依据(设计 §2.2):门先裁掉不该穿的范围,量在范围内决定「穿满给谁」,
    序最后决定「先合成哪个」——序变体依赖 alloc 的合成事件语义,必须最后;
    fill 改派件均非主线组件,不可能构成 key 高价值合成完成件,不扰序变体的
    推迟/牺牲判定。

    返回 (分配序列, 各变体动作记录 ``['fill3=<动作>']``);全开关默认关 =
    基分配原样(零漂移锚)。session 缺失(离线/旧栈)由序变体内部保守降级。
    """
    from sr_od.application.currency_war.kernel.cw_comps import equip_allocation
    from sr_od.application.currency_war.kernel.cw_junk_first import (
        junk_first_allocation,
    )
    actions: list[str] = []
    base = equip_allocation(comp, deployed, owned, occupied)
    alloc, fill_action = fill3_allocation(registry, comp, deployed, base,
                                          occupied, signals, hold_active)
    actions.append(f'fill3={fill_action}')
    alloc = junk_first_allocation(session, registry, comp, deployed, owned,
                                  occupied, sorted(signals.enemy_affixes),
                                  base_alloc=alloc)
    return alloc, actions
