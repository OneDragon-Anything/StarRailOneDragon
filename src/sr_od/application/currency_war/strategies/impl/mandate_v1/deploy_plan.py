"""部署计划策略层单一源(mandate_v1;落位决策权归策略实现)。

设计依据 = docs/develop/sr_od/application/currency_war/changes/
2026-09-20-benchchar-retirement/design.md §2.2(落位决策权归策略层):
**谁上场、去哪一排、落哪个槽,全部由策略实现决定;框架在落位上零决定**
——kernel 版 ``select_deployments``/``select_deployments_reasoned``/
``assign_deploy_slots``/``empty_deploy_slots`` 随本模块接管而退役。

- 选人(:func:`select_deployments`,自 kernel 原样迁入):围栏/成对/点火序/
  核心桶/必需件首桶/cap/同名去重/配方底线门/板空保底全套语义,禁第二套;
- 排路由(:func:`deploy_row_pref`,三级):comp 站位覆盖(``Comp.char_
  positions`` 字段契约「comp 特定站位要求,覆盖命途默认」)> 注册表
  ``get_char(char_id).position_pref()`` 派生 > back 兜底——旧链路备战
  候选恒按后排、注册表偏好被丢弃的行为变化申报项(design §2.2 申报 1)
  在此落地;
- 前排保证(kernel 规则随迁):pref=back ∧ 前排全空(出战硬要求前排有
  角色)时队列后方真 front 候选先提,无 front 候选才强转当前件;
- 槽位选择(:func:`deploy_slot_plans`):策略遍历容器行列现值自定,后排
  上限 = ``back_layout`` 现值(:func:`back_capacity_of` 单一源)——消除
  「发射空槽可指扩展槽而执行面按基线 6 槽」的静默分歧(P2 遗留);
- 出战链计划单一源(:func:`deploy_plan_moves`):mandate 发射位
  (mandate._emit_deploy_moves)与 cw_loop 出战链
  (:func:`battle_chain_deploy_params`,恢复局同步步/达标臂共用)共用,
  禁各写一套计划装配。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from sr_od.application.currency_war.data.cw_chars import get_char
from sr_od.application.currency_war.kernel.cw_deploy_logic import (
    DEPLOY_FENCE,
    _bonds_of,
    cap_roomy_of,
    deploy_target_sets,
    deployed_bond_counts,
    ignition_gain,
    recipe_floor_holds,
    tier_completes,
    xianzhou_supply_exists,
)
from sr_od.application.currency_war.kernel.cw_exec_state import (
    DEPLOYED_FRONT_CAPACITY,
)
from sr_od.application.currency_war.kernel.cw_line_defs import (
    RECIPE_BASE,
    RECIPE_FACTIONS,
)
from sr_od.application.currency_war.strategies.impl.mandate_v1.mandate_state import (
    state_of,
)

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_game_state import (
        BenchSlot,
        GameState,
    )
    from sr_od.application.currency_war.strategies.impl.cw_strategy import (
        StrategySession,
    )
    from sr_od.application.currency_war.strategies.impl.mandate_v1.mandate import (
        MandateFrame,
    )


def _slot_cid(b) -> str:
    """占席条目 → 身份名(单位 = 内嵌 Unit.char_id;占位件 = '';
    P4 容器形,解包单一源 = kernel ``bench_slot_unit``)。"""
    from sr_od.application.currency_war.kernel.cw_exec_state import (
        bench_slot_unit,
    )
    u = bench_slot_unit(b)
    return (getattr(u, 'char_id', '') or '') if u is not None else ''


def _is_item_slot(b) -> bool:
    """占席条目 → 占位件判定(§2.4 字段映射:is_item_slot=True →
    kind ∈ tome/bookcard/supply_box)。"""
    return getattr(b, 'kind', 'unit') in ('tome', 'bookcard', 'supply_box')


def _slot_no_of(b) -> int:
    """占席条目 → 槽号信息位(单位 = 内嵌 Unit.slot,1 基物理槽)。"""
    from sr_od.application.currency_war.kernel.cw_exec_state import (
        bench_slot_unit,
    )
    u = bench_slot_unit(b)
    return int(getattr(u, 'slot', 0) or 0) if u is not None else 0

#: 部署计划容器槽位表不健康显影分键(计划级 fail-closed 时 +1)。键名保留
#: 现役 ``deploy_chain_slot_table_unhealthy``(跨局遥测对照可比性优先;
#: 发射点已统一为本函数 = 原出战链局部键的同语义继承,mandate 发射位与
#: 出战链共用;键名与消费面语义的命名失配归 P8 正本更新一并申报再议)。
DEPLOY_PLAN_SLOT_TABLE_UNHEALTHY_KEY: str = 'deploy_chain_slot_table_unhealthy'


def _deploy_plan_inputs(frame: MandateFrame, session: StrategySession,
                        state: GameState) -> dict:
    """select_deployments 同参装配(计划侧装配单一源,自 mandate 迁居;
    原子发射位(R2)与放行判定谓词共用同一份输入,禁双源)。键集 =
    ``select_deployments_reasoned`` 形参(围栏/去重/cap/配方底线语义全在
    选人函数内)。"""
    from sr_od.application.currency_war.kernel.cw_game_state import (
        max_units_of,
    )
    from sr_od.application.currency_war.kernel.cw_intention import (
        locked_faction_scope,
    )
    _comp = getattr(state_of(session), 'target_comp', None)
    _tgt, _fw_carry = deploy_target_sets(
        _comp, getattr(state_of(session), 'transition_framework', '') or '')
    _cids = {d.char_id for d in frame.deployed if d.char_id}
    _ist = getattr(state_of(session), 'v3_intention', None)
    return {
        'bench': frame.bench,
        'deployed_cids': _cids,
        'deployed_fac': deployed_bond_counts(_cids),
        'board': dict(state.board.value or {}),
        # cap 单一源 = max_units_of 容器派生链(迭代 2026-09-18-prep-obs-
        # retirement 阶段 3.1;无限回退分支已退役——max_units_of 恒 ≥1 有值)。
        'cap': max_units_of(state),
        'target_factions': _tgt,
        'target_cores': set(getattr(_comp, 'core_chars', None) or ()),
        'fw_carry': _fw_carry,
        'locked_factions': (locked_faction_scope(_ist) or frozenset()),
        # 判据必需件首桶(单一源 = 目标 comp required_deployed;发射⇔执行
        # 同吃本装配,序语义见 select_deployments 注)。
        'required_names': frozenset(
            getattr(_comp, 'required_deployed', ()) or ()),
    }


def select_deployments(
    bench: list[BenchSlot],
    deployed_cids: set[str],
    deployed_fac: dict[str, int],
    board: dict[str, int],
    cap: int,
    front_total: int = 4,
    back_total: int = 6,
    target_factions: frozenset[str] | set[str] = frozenset(),
    target_cores: frozenset[str] | set[str] = frozenset(),
    fw_carry: frozenset[str] | set[str] = frozenset(),
    locked_factions: frozenset[str] | set[str] = frozenset(),
    recipe_floor_lock_exempt: bool = False,
    reasons_out: dict[int, str] | None = None,
    required_names: frozenset[str] | set[str] = frozenset(),
) -> tuple[list[int], list[int]]:
    """围栏判定(选人策略本体,自 kernel/cw_deploy_logic 迁入;body 语义
    逐位不变):返回 (上场 bench 下标序, 留 bench 下标)。

    语义 = 散牌围栏/补档序/引擎对优先/cap 富余填空/点火首键+桶序/配方
    底线门/板空保底(ADR-0130 系);唯一省略:SIFT 未识别(char_id 空)
    照旧上——调用方传空 char_id 即走该分支。
    cap 语义 = 已 deployed 数 + 本轮上场数 ≤ cap。

    ADR-0360 件3(deploy 围栏锁定键放行):``locked_factions`` = 锁定帧
    体系键并入围栏放行集。

    ADR-0564 配方底线门锁定线语境豁免:``recipe_floor_lock_exempt`` =
    豁免武装位(单源 = ``cw_intention.locked_line_recipe_floor_conflict``);
    缺省 False = 门判定逐位同旧。

    **held 拒因返回(N2 规格单一源)**:传 ``reasons_out`` dict 时,held
    下标 → 拒因('scatter_fence'/'rest_capacity'/'cap'/'name_dup'/
    'recipe_floor'/'item_slot')逐项写入;带 reason 消费走
    :func:`select_deployments_reasoned`。

    ``required_names``(判据必需件首桶):目标 comp 的 required_deployed
    成员名集,进选人序首桶,先于核心桶/cap 竞争(推导出处 =
    ``Comp.required_deployed`` 字段契约 + user_playstyle [31]② 必需件
    特化)。缺省空集 = 序逐位同旧。**分轨边界显式申报**:预检位
    (shop can_deploy_single 调用点、cw_launch_admission 注入)不穿本参
    ——预检语义 = 单候选可入性,序无关。
    """
    reasons: dict[int, str] = {}
    vacancy = front_total + back_total - len(deployed_cids)
    vacancy = max(vacancy, 0)

    tgt_idx: list[int] = []
    rest: list[int] = []
    bench_fac: dict[int, str] = {}
    pair_counts: dict[str, int] = dict(board)
    for i, bc in enumerate(bench):
        cid = _slot_cid(bc)
        ch = get_char(cid) if cid else None
        bonds: set[str] = set()
        if ch is not None:
            bonds = set(ch.factions) | set(ch.flows)
            if ch.factions:
                bench_fac[i] = ch.factions[0]
                pair_counts[ch.factions[0]] = pair_counts.get(ch.factions[0], 0) + 1
        is_tgt = bool(bonds & set(target_factions)) or cid in target_cores \
            or cid in fw_carry
        (tgt_idx if is_tgt else rest).append(i)
    # tgt 初始序也按点火首键(围栏前的序影响 cap 竞争时
    # 谁先上)
    tgt_idx.sort(key=lambda i: (
        -ignition_gain(_bonds_of(bench[i]), deployed_fac),
        -tier_completes(_bonds_of(bench[i]), deployed_fac)))

    held: list[int] = []
    fill_mode = vacancy > 2
    board_recipe = sum(v for k, v in board.items() if k in RECIPE_FACTIONS)
    recipe_starved = board_recipe < RECIPE_BASE
    must_up = len(tgt_idx) + sum(
        1 for i in rest
        if bench_fac.get(i) is not None
        and pair_counts.get(bench_fac[i], 0) >= 2)
    roomy = cap_roomy_of(vacancy, 0, must_up)
    # 占槽物品恒 held(部署伪槽修复批 ②,防线):占位件候选从 tgt/rest 全部
    # 桶剔除、恒 held,先于一切围栏/点火/cap 判定被拒——防未来第三处装配
    # 点再漏伪槽。拒因 'item_slot' 进闭集;char_id='' 不触发本防线
    # (「照旧上」fail-open 语义保留)。
    _item_idx = {k for k in range(len(bench))
                 if _is_item_slot(bench[k])}
    if _item_idx:
        tgt_idx = [k for k in tgt_idx if k not in _item_idx]
        rest = [k for k in rest if k not in _item_idx]
        for k in sorted(_item_idx):
            held.append(k)
            reasons[k] = 'item_slot'
    for i in list(rest):
        cid = _slot_cid(bench[i])
        if not cid:
            continue    # 未识别:照旧上(围栏无法判)
        f = bench_fac.get(i)
        # 凑档降级(部署侧;ADR-0288):无目标件可上(tgt 空)时,
        # 凑档件——board∪bench 主阵营计数 ≥2(含自身 = board 已有
        # ≥1,入后凑 2 档)——不被配方围栏拦:降级上场「有总比没有
        # 厉害」;tgt 非空时围栏照旧(降级件不挤目标件)。
        _bond_paired = f is not None and pair_counts.get(f, 0) >= 2
        # ADR-0360 件3:锁定帧体系键按**全羁绊**匹配放行;未传锁定帧时
        # 围栏行为与旧版逐位一致
        if f is not None and f not in DEPLOY_FENCE \
                and not (_bonds_of(bench[i]) & set(locked_factions)) \
                and recipe_starved and not roomy \
                and not (not tgt_idx and _bond_paired):
            rest.remove(i)
            held.append(i)
            reasons[i] = 'scatter_fence'
            continue
        if f is not None and pair_counts.get(f, 0) >= 2:
            continue    # 成对:上
        if fill_mode:
            continue    # 人口扩展期:散牌填位
        rest.remove(i)
        held.append(i)
        reasons[i] = 'rest_capacity'
    board_empty = len(deployed_cids) == 0
    # 板空保底只救「规则留置」件;占位件恒拒不参与保底(伪槽禁止因
    # 保底被推上板——保底救的是真角色)。
    _rescuable = [k for k in held if reasons.get(k) != 'item_slot']
    if board_empty and not tgt_idx and not rest and _rescuable:
        first = _rescuable[0]
        held.remove(first)
        reasons.pop(first, None)   # 板空保底:上 1 个(拒因随之消除)
        rest.append(first)
    # 点火增量首键——「恰好让某体系凑满 tier 的那张」
    # 排最前(冗余件/无关件让位)。引擎身份键降为次键
    # (探针实证:vacancy=1 时冗余第4仙舟曾挤掉点火列车2)。
    _ENGINE = {'仙舟', '列车同行', '持续伤害'}
    rest.sort(key=lambda i: (
        -ignition_gain(_bonds_of(bench[i]), deployed_fac),
        0 if (bench_fac.get(i) in _ENGINE or
              _bonds_of(bench[i]) & _ENGINE) else 1))
    # 桶序修正——tgt 全体压 rest 的旧序会让「冗余 tgt 件」
    # 挤掉「点火 rest 件」(探针④:第4仙舟压点火三月七)。点火增量
    # >0 的 rest 件先于 ignition=0 的 tgt 件上场(点火=四体系成型
    # 的关键跳变,语义高于 target 身份;tgt 内部序已按点火排)。
    ignite_rest = [i for i in rest
                   if ignition_gain(_bonds_of(bench[i]), deployed_fac) > 0]
    plain_rest = [i for i in rest if i not in ignite_rest]
    # 锁定线核心优先桶(ADR-0323):意向锁定的线核心优先于过渡填充件。
    # 非锁定局 target_cores 空 → 本桶恒空,序不变;「点火 >
    # 冗余 target」语义保留。
    _core_set = set(target_cores)
    core_tgt = [i for i in tgt_idx
                if _slot_cid(bench[i]) in _core_set]
    other_tgt = [i for i in tgt_idx if i not in core_tgt]
    # 判据必需件首桶(required_names = 目标 comp 的 required_deployed 成员):
    # 判据以「该件在板」为必要条件——缺它该体系永远无法成型,普通成员
    # 可替换而必需件不可;cap 竞争时空位让给普通成员 = 弱占优劣化。
    # 空集 = 逐位同旧序。
    _req_set = set(required_names)
    req_tgt = [i for i in core_tgt
               if _slot_cid(bench[i]) in _req_set]
    core_tgt = [i for i in core_tgt if i not in req_tgt]
    order = req_tgt + core_tgt + ignite_rest + other_tgt + plain_rest
    # cap 截断(动态停语义:超 cap 的留 bench)
    # 同名去重(5.1.7 不变量:同角色在场只 1)扩到
    # **本轮已上名单**——传入 deployed_cids 在实机=开局
    # 一次读取/sim=恒空集,只查它拦不住本轮内第二张同名
    # (cid 不在 deployed_cids)。3合1 素材留 bench(囤件语义不受影响)。
    up: list[int] = []
    _up_names: set[str] = set()
    # 配方底线门(ADR-0261 裁决选项3 + ADR-0564 锁定线语境豁免;判定
    # 单一源 = ``recipe_floor_holds``):列车≥RECIPE_FLOOR_TRAIN_CAP 且
    # 仙舟<RECIPE_FLOOR_XZ_BASE → 列车件让位留 bench。锁定线语境
    # 豁免:豁免武装帧 ∧ 本帧无有效仙舟供给 → 门让位;
    # 供给保留条款不变。循环内逐件增量维护 ``_fac_run``
    # (ADR-0261 裁决:每上一件按全羁绊口径 +1,不得用入参初始快照)。
    # 供给惰性:豁免武装帧才现算(供给谓词);``_up_names`` 随循环推进
    # → 同名拷贝本帧先上后不再计作供给(与去重语义一致)。
    _fac_run = dict(deployed_fac)
    for i in order:
        if len(deployed_cids) + len(up) >= cap:
            held.append(i)
            reasons[i] = 'cap'
            continue
        cid = _slot_cid(bench[i])
        if cid and (cid in deployed_cids or cid in _up_names):
            held.append(i)   # 去重(5.1.7,含本轮已上):留 bench
            reasons[i] = 'name_dup'
            continue
        if recipe_floor_holds(
                bench_fac.get(i, ''),
                _fac_run.get('列车同行', 0),
                _fac_run.get('仙舟', 0),
                recipe_floor_lock_exempt,
                xianzhou_supply_exists(bench, deployed_cids | _up_names)
                if recipe_floor_lock_exempt else False):
            held.append(i)   # 配方底线门(锁定线豁免见 ADR-0564)
            reasons[i] = 'recipe_floor'
            continue
        up.append(i)
        if cid:
            _up_names.add(cid)
        for f in _bonds_of(bench[i]):
            _fac_run[f] = _fac_run.get(f, 0) + 1
    if reasons_out is not None:
        reasons_out.update(reasons)
    return up, held


def select_deployments_reasoned(
    bench: list[BenchSlot],
    deployed_cids: set[str],
    deployed_fac: dict[str, int],
    board: dict[str, int],
    cap: int,
    front_total: int = 4,
    back_total: int = 6,
    target_factions: frozenset[str] | set[str] = frozenset(),
    target_cores: frozenset[str] | set[str] = frozenset(),
    fw_carry: frozenset[str] | set[str] = frozenset(),
    locked_factions: frozenset[str] | set[str] = frozenset(),
    recipe_floor_lock_exempt: bool = False,
    required_names: frozenset[str] | set[str] = frozenset(),
) -> tuple[list[int], list[int], dict[int, str]]:
    """select_deployments 的带拒因形态(单一源同函数路径;自 kernel 迁入)。

    返回 ``(up, held, reasons)``——reasons = held 下标 → 拒因
    ('scatter_fence'/'rest_capacity'/'cap'/'name_dup'/'recipe_floor'/
    'item_slot')。
    消费面 = 出口③围栏预检(shop can_deploy_single)、发射侧闭环分键
    (mandate._record_deploy_emit_held)、出战链计划
    (:func:`deploy_plan_moves`)与 select_swap_plan 卖后上序(注入
    ``select_up``);预检/分键禁第二套围栏语义。
    """
    reasons: dict[int, str] = {}
    up, held = select_deployments(
        bench, deployed_cids=deployed_cids, deployed_fac=deployed_fac,
        board=board, cap=cap, front_total=front_total,
        back_total=back_total, target_factions=target_factions,
        target_cores=target_cores, fw_carry=fw_carry,
        locked_factions=locked_factions,
        recipe_floor_lock_exempt=recipe_floor_lock_exempt,
        reasons_out=reasons,
        required_names=required_names)
    return up, held, reasons


def has_deployable(
    bench: list[BenchSlot],
    deployed_cids: set[str],
    deployed_fac: dict[str, int],
    board: dict[str, int],
    cap: int,
    front_total: int = 4,
    back_total: int = 6,
    target_factions: frozenset[str] | set[str] = frozenset(),
    target_cores: frozenset[str] | set[str] = frozenset(),
    fw_carry: frozenset[str] | set[str] = frozenset(),
    locked_factions: frozenset[str] | set[str] = frozenset(),
    recipe_floor_lock_exempt: bool = False,
    required_names: frozenset[str] | set[str] = frozenset(),
) -> bool:
    """「是否存在可部署件」的单一源谓词(发射×执行契约;自 kernel 迁入)。

    = ``has_deployable_reasoned(...)[0]``(委托,判空语义不变)——发射方
    (决策核准备战段)与达标臂质量闸(kernel cw_launch_admission 经注入
    消费,依赖倒置契约同 line_members)共用同一份围栏/去重/cap/配方
    底线语义判「还有没有部署可做」。背景(run 20260904_28xx 局11
    停机形态):发射方判「bench 有货该部署」、执行方按配方底线规则把该件
    留 bench → 空计划被包装成成功 → 零推进环停机。修后发射方在计划为空时
    不提案(bench=1 是合法稳态)。

    语义口径与 ``select_deployments`` 完全一致(含 SIFT 未识别 char_id=''
    「照旧上」的 fail-open:身份不可判时恒 True,不做激进留 bench)。
    ``recipe_floor_lock_exempt``/``required_names`` 透传。
    """
    return has_deployable_reasoned(
        bench, deployed_cids=deployed_cids, deployed_fac=deployed_fac,
        board=board, cap=cap, front_total=front_total, back_total=back_total,
        target_factions=target_factions, target_cores=target_cores,
        fw_carry=fw_carry, locked_factions=locked_factions,
        recipe_floor_lock_exempt=recipe_floor_lock_exempt,
        required_names=required_names)[0]


def has_deployable_reasoned(
    bench: list[BenchSlot],
    deployed_cids: set[str],
    deployed_fac: dict[str, int],
    board: dict[str, int],
    cap: int,
    front_total: int = 4,
    back_total: int = 6,
    target_factions: frozenset[str] | set[str] = frozenset(),
    target_cores: frozenset[str] | set[str] = frozenset(),
    fw_carry: frozenset[str] | set[str] = frozenset(),
    locked_factions: frozenset[str] | set[str] = frozenset(),
    recipe_floor_lock_exempt: bool = False,
    required_names: frozenset[str] | set[str] = frozenset(),
) -> tuple[bool, dict[int, str]]:
    """「是否存在可部署件」的带拒因形态(发射侧遥测载体;ADR-0564)。

    = ``select_deployments_reasoned`` 的薄包装:返回 ``(bool(up),
    reasons)``——判空语义与 ``has_deployable`` 完全一致,reasons =
    held 下标 → 拒因闭集(scatter_fence/rest_capacity/cap/name_dup/
    recipe_floor/item_slot)。消费面 = mandate._deployable(部署放行判定:
    ``deploy_emit_held_<reason>`` 发射侧分键的唯一拒因源)与本模块
    ``has_deployable``(委托)。禁第二套围栏语义(单一源同函数路径)。
    """
    up, _held, reasons = select_deployments_reasoned(
        bench, deployed_cids=deployed_cids, deployed_fac=deployed_fac,
        board=board, cap=cap, front_total=front_total, back_total=back_total,
        target_factions=target_factions, target_cores=target_cores,
        fw_carry=fw_carry, locked_factions=locked_factions,
        recipe_floor_lock_exempt=recipe_floor_lock_exempt,
        required_names=required_names)
    return bool(up), reasons


def can_deploy_single(
    candidate: BenchSlot,
    bench: list[BenchSlot],
    deployed_cids: set[str],
    deployed_fac: dict[str, int],
    board: dict[str, int],
    cap: int,
    front_total: int = 4,
    back_total: int = 6,
    target_factions: frozenset[str] | set[str] = frozenset(),
    target_cores: frozenset[str] | set[str] = frozenset(),
    fw_carry: frozenset[str] | set[str] = frozenset(),
    locked_factions: frozenset[str] | set[str] = frozenset(),
    recipe_floor_lock_exempt: bool = False,
    required_names: frozenset[str] | set[str] = frozenset(),
) -> tuple[bool, str]:
    """单件假想查询(N2 规格②;自 kernel 迁入)。

    输入 = 候选件 + 假想 bench/板面快照(现有 bench 追加 candidate,
    其余量传当前真实快照),输出 = (可落板, 拒因);拒因口径 =
    ``select_deployments_reasoned``(scatter_fence/rest_capacity/cap/
    name_dup/recipe_floor)。出口③围栏放行预检**只消费本 API**,
    禁发射面自算第二套围栏语义。查询不可得(快照缺失/语义冲突)由
    调用方按 ``precheck_unavailable`` 分键处理(与围栏拒 'fenced' 禁
    混键)。``recipe_floor_lock_exempt``/``required_names`` 透传。
    """
    bench2 = list(bench) + [candidate]
    idx = len(bench2) - 1
    up, _held, reasons = select_deployments_reasoned(
        bench2, deployed_cids=deployed_cids, deployed_fac=deployed_fac,
        board=board, cap=cap, front_total=front_total,
        back_total=back_total, target_factions=target_factions,
        target_cores=target_cores, fw_carry=fw_carry,
        locked_factions=locked_factions,
        recipe_floor_lock_exempt=recipe_floor_lock_exempt,
        required_names=required_names)
    if idx in up:
        return True, ''
    # 缺省 'unannotated' 显影(策略审查二十三跳必改项):候选 held 而拒因
    # 字典无标注 = 未来新增 hold 路径漏标拒因的缺口形态——不冒名 'cap',
    # 显影回炉标注(既有五拒因调用面零变化)。
    return False, reasons.get(idx, 'unannotated')


def deploy_row_pref(char_id: str, comp: object | None) -> str:
    """落位排路由(策略三级;design §2.2「每人的排全部由策略实现决定」)。

    ① comp 站位覆盖:``Comp.char_positions``(字段契约「comp 特定站位
       要求(角色→front/back),覆盖命途 position_pref 默认」;在册实例
       = 爻光必后台/万敌独前排/知更鸟前台,攻略实证);
    ② 注册表派生:``get_char(char_id).position_pref()``(design §2.1
       「position_pref 不入形状,消费点经注册表按 char_id 派生;禁全局
       get_role_position」——旧链路备战候选恒按后排、注册表偏好恒被
       丢弃的行为变化申报项在此生效);
    ③ back 兜底:comp 未覆盖 ∧ 注册表未登记(未识别名)→ 后排。

    返回 'front' | 'back'。
    """
    cp = getattr(comp, 'char_positions', None) or {}
    hit = cp.get(char_id)
    if hit in ('front', 'back'):
        return hit
    ch = get_char(char_id) if char_id else None
    if ch is not None:
        return ch.position_pref()
    return 'back'


def deploy_slot_plans(bench: list[BenchSlot], up_idx: list[int],
                      comp: object | None, state: GameState,
                      ) -> list[tuple[int, str, int]]:
    """落位策略(排路由 + 前排保证 + 槽位选择;P3 落位决策权归策略本体)。

    - 排 = :func:`deploy_row_pref` 三级路由;
    - **前排保证**(kernel 规则随迁,2026-08-16 M47 修正口径):pref=back
      ∧ 前排全空(出战硬要求前排有角色)时队列后方真 front 候选提到
      当前位,无 front 候选才强转当前 back 件;
    - 槽位 = 策略遍历容器行列现值自定:front_row/back_row 的 Unit 槽位
      信息位(排内 1 基)取占用集,首选排取最低空槽、首选排满 fallback
      另一排,两排全满截断(调用侧 cap 门先行,防御停);
    - 后排上限 = ``back_layout`` 现值(back_capacity_of 单一源,值域 6-9)
      ——发射空槽集合按实值派生,扩展局(宝钻 7/8/9)才可能指到扩展槽,
      基线 6 槽局不再出现越界槽号(P2 遗留分歧消除)。

    返回 ``[(bench 下标, row, 排内 1 基槽号)]``(发射序 = 执行序;
    落位意图完整入载荷 (bench_idx, to_row, to_slot),执行/写侧按载荷
    直落,framework 零落位决定)。
    """
    from sr_od.application.currency_war.kernel.cw_game_state import (
        back_capacity_of,
    )
    front_units = list(state.front_row.value or [])
    back_units = list(state.back_row.value or [])
    front_occ = {int(getattr(u, 'slot', 0) or 0) for u in front_units}
    back_occ = {int(getattr(u, 'slot', 0) or 0) for u in back_units}
    back_total = back_capacity_of(state)
    fe = [s for s in range(1, DEPLOYED_FRONT_CAPACITY + 1)
          if s not in front_occ]
    be = [s for s in range(1, back_total + 1) if s not in back_occ]
    pending = list(up_idx)
    out: list[tuple[int, str, int]] = []
    oi = 0
    while oi < len(pending):
        bi = pending[oi]
        pref = deploy_row_pref(_slot_cid(bench[bi]), comp)
        if pref == 'back' and len(fe) == DEPLOYED_FRONT_CAPACITY and fe:
            # 前排保证(重排):队列后方有真 front 候选提到当前位
            _later = next(
                (j for j in pending[oi + 1:]
                 if deploy_row_pref(
                     _slot_cid(bench[j]),
                     comp) == 'front'), None)
            if _later is not None:
                pending.remove(_later)
                pending.insert(oi, _later)
                continue   # 原地重处理当前位(现为真 front)
            pref = 'front'   # 无 front 候选 → 强转前排
        if pref == 'front':
            row, chosen, fallback = 'front', fe, be
        else:
            row, chosen, fallback = 'back', be, fe
        if chosen:
            slot = chosen.pop(0)
        elif fallback:
            row = 'front' if row == 'back' else 'back'
            slot = fallback.pop(0)
        else:
            break   # 两排全满(防御停;cap 门先行时不可达)
        out.append((bi, row, slot))
        oi += 1
    return out


def deploy_plan_moves(frame: MandateFrame, session: StrategySession,
                      state: GameState) -> list[tuple[int, str, int, str]]:
    """部署计划单一源(选人 + 落位 + 容器对位;mandate 发射位与出战链
    共用,禁各写一套计划装配)。

    管线 = ``_deploy_plan_inputs`` 同参装配 → :func:`select_deployments_
    reasoned` 选人 → :func:`deploy_slot_plans` 落位 → bench 容器槽位表
    对位(slot 信息位 ↔ 容器下标,换算收口)。对位防线(T-266):容器
    槽位表存在重复/越界槽号时 ``{slot: 下标}`` 字典对位语义未定义
    (静默保留后值 = 拖错人出场的通道),判据单一源 =
    ``bench_slots_healthy``;不健康 → 整份计划 fail-closed 不出 +
    :data:`DEPLOY_PLAN_SLOT_TABLE_UNHEALTHY_KEY` 分键显影防静默降级。
    逐 move 对位失配(陈旧帧)= fail-closed 跳过该 move。

    返回 ``[(bench 容器下标, row, 排内 1 基槽号, faction)]``;计划空 =
    []。faction = 容器槽位表角色对象现取(design §2.6 字段裁定,sim
    board 计数消费)。
    """
    from one_dragon.utils.log_utils import log
    from sr_od.application.currency_war.data.cw_chars import char_first_faction
    from sr_od.application.currency_war.kernel.cw_exec_state import (
        bench_slot_unit,
        bench_slots_healthy,
    )
    from sr_od.application.currency_war.kernel.cw_strategy_session import (
        strategy_state_of,
    )
    _inputs = _deploy_plan_inputs(frame, session, state)
    up, _held, _reasons = select_deployments_reasoned(**_inputs)
    if not up:
        return []
    # comp 读口 = kernel None-safe 访问函数(禁 mandate_state.state_of:
    # 其对异型状态惰性冷建并写回 session——出战链只读计划,禁带状态
    # 重建副作用;test 桩态亦不被替换)。
    _comp = getattr(strategy_state_of(session), 'target_comp', None)
    plans = deploy_slot_plans(frame.bench, up, _comp, state)
    view = state.bench.value
    bench_slots = list(view.slots) if view is not None else []
    # 槽号信息位集 = 单位槽内嵌 Unit.slot(P4 容器形;与观察写端按槽落位
    # 构造同源,健康门语义不变:唯一 ∧ 1..9)
    if not bench_slots_healthy([
            int(getattr(u, 'slot', 0) or 0)
            for s in bench_slots
            if s is not None and (u := bench_slot_unit(s)) is not None]):
        _bcd_counters = getattr(strategy_state_of(session), 'cw4_counters',
                                None)
        if isinstance(_bcd_counters, dict):
            _bcd_counters[DEPLOY_PLAN_SLOT_TABLE_UNHEALTHY_KEY] = \
                _bcd_counters.get(DEPLOY_PLAN_SLOT_TABLE_UNHEALTHY_KEY, 0) + 1
        log.warning('[cw!][deploy-plan] 部署计划弃算:容器槽位表槽号不健康'
                    '(重复/越界,%s)→ {slot:下标} 对位 fail-closed,'
                    '本帧零部署 move', bench_slots)
        return []
    _cidx_of = {}
    for i, s in enumerate(bench_slots):
        if s is None:
            continue
        u = bench_slot_unit(s)
        if u is not None:
            _cidx_of[int(getattr(u, 'slot', 0) or 0)] = i
    out: list[tuple[int, str, int, str]] = []
    for bi, row, slot in plans:
        _slot_no = _slot_no_of(frame.bench[bi])
        _bi = _cidx_of.get(_slot_no)
        if _bi is None:
            continue   # 对位失配(陈旧帧)= fail-closed 跳过该 move
        # 发射载荷 faction = 主阵营注册表派生单一源(char_first_faction,
        # §2.1 faction 类1:部署装配;未注册名 = '?')
        out.append((int(_bi), row, int(slot),
                    char_first_faction(_slot_cid(frame.bench[bi]))))
    return out


def battle_chain_deploy_params(session: StrategySession) -> list:
    """出战链部署计划(CwActionDeployMoveParam 序;恢复局同步步/达标臂
    共用,计划单一源 = :func:`deploy_plan_moves`)。

    frame 装配 = 容器现读重建(原 cw_loop._battle_chain_deploy_moves
    内联段迁入;design §2.2「出战链不再装配选人输入」——出战链只调
    策略层计划入口)。空板面/计划空 = 空 move 序(CwActionStartBattle
    照发)。"""
    from sr_od.application.currency_war.kernel.cw_game_state import (
        bench_entries_of,
        deployed_rows_of,
        game_state_of,
        gold_of,
        level_of,
        max_units_of,
    )
    from sr_od.application.currency_war.kernel.cw_vocab import (
        CwActionDeployMoveParam,
    )
    from sr_od.application.currency_war.strategies.impl.mandate_v1.mandate import (
        MandateFrame,
    )
    gs = game_state_of(session)
    bench = bench_entries_of(gs)
    _front, _back = deployed_rows_of(gs)
    deployed = [d for d in (*_front, *_back) if d is not None]
    _node = gs.node.value
    frame = MandateFrame(
        gold=gold_of(gs), level=level_of(gs),
        bench=bench, deployed=deployed, deploy_cap=max_units_of(gs),
        node_type=None, stop_flag=False, k_members=(),
        round_num=int(_node.round_num) if _node is not None else 1)
    return [CwActionDeployMoveParam(bench_idx=bi, to_row=row, to_slot=slot,
                                    faction=faction)
            for bi, row, slot, faction in deploy_plan_moves(frame, session, gs)]
