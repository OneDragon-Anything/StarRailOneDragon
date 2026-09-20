"""货币战争 装备穿戴计划构造(kernel 桶;R2 组合壳溶解的原子通路件)。

本模块自执行器模块 ``prep_actions.py`` 迁居(design.md
unified-action-factory §2.6「穿装备:计划构造 = 现役 _build_equip_wear_plan
自执行器模块迁 kernel,决策侧逐帧现算」):计划单一源随发射位上移,
组合壳(RunEquip→CwOpEquipAll)退役后发射位直接消费同一构造函数,
无第二源。机械执行半(定位/拖拽)留守 ``operations/cw_op/
cw_op_equip_all.py``;``EquipWearStep`` 及拉黑/排序纯 helper 一并迁入
(kernel 不得依 operations——依赖方向倒置是本次迁居的另一半动机)。

**边界申报(批 2a)**:``_build_equip_wear_plan(session,
registry)`` 形参 = 决策链可达两件(黑板帧宿主 session / 判据开关
registry),类型 Any(duck 型;kernel 零 app/context import)。

W880 装备环境信号「构造点唯一」契约维持:唯一构造点 = 本模块
``_build_equip_wear_plan``(求值块自 op 迁出后,一次打包传递)。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_strategy_session import (
    strategy_state_of,
)

#: 前排槽位数(= screen_info 前排-1..4;deploy 侧同容量;原
#: CwOpEquipAll.FRONT_SLOT_COUNT 迁居,计划面消费)。
FRONT_SLOT_COUNT: int = 4


def _empty_slots(occupied: dict[int, list[str]], count: int) -> list[int]:
    """已穿槽位 dict → 空槽位序号列表(1-based;P0-2 drag 前占位检测)。

    ``occupied`` = ``{slot_idx: [装备名]}``(slot_idx 1-based);槽不在
    dict = 空。纯函数(可离线测):只往空槽 drag,避免覆盖已穿装备。
    """
    return [i for i in range(1, count + 1) if i not in occupied]


def _prioritize_wearable(
    wearable: list[tuple[str, tuple[int, int]]],
    key_equips: list[str] | None,
) -> list[tuple[str, tuple[int, int]]]:
    """穿戴候选按 target_comp.key_equips 优先排序(命脉件在前,其余原序)。

    comp 驱动穿戴(替 naive ``wearable[0]``);无 target / 无 key_equips
    → 原序(等价旧行为)。``key_equips`` 可含重复 → 按 multiplicity 消费
    (命中的重复件也优先,但不超额)。决策见 ADR-0101。
    """
    if not key_equips:
        return wearable
    remaining = list(key_equips)
    prioritized: list[tuple[str, tuple[int, int]]] = []
    rest: list[tuple[str, tuple[int, int]]] = []
    for name, pos in wearable:
        if name in remaining:
            prioritized.append((name, pos))
            remaining.remove(name)   # 消费一个 multiplicity(重复件不超额优先)
        else:
            rest.append((name, pos))
    return prioritized + rest


@dataclass(frozen=True)
class EquipWearStep:
    """单件穿戴计划步(计划随指令下发的契约载体;ADR-0601 §3-C1)。

    产出位 = 分发段 ``_build_equip_wear_plan``(读备战入口观察产物
    PrepObservation,P4 观察接线后零读屏,由 kernel 判据单一源
    求值),随 ``CwOpEquipAll.__init__(ctx, plan)`` 构造下发;op 对计划
    只做机械执行(定位/拖拽/报告),禁二次求值。2a 原子通路:本步同时
    是 ``CwActionWearEquipParam`` 动作的构造源(发射位逐步产原子动作)。

    字段坐标系(索引/槽位字段定义注释约定):
    - ``row``: 'front'|'back'(画面物理排;deployed 槽位表同坐标系);
    - ``slot``: 物理槽位 1-based(前排 1-4 / 后排 1-选档 N;非列表下标
      ——与 prep_actions §13.1 slot 语义全局统一一致),**产出期快照**
      (builder 现读 deployed 戳记),pass 内恒稳;
    - ``char_name``: 分配目标角色注册名;**'' = front-only 回退步**
      (身份读失败分支:无角色身份,拖点 = 前排空槽 avatar),全 char_name
      为 '' 的计划 = 回退路径计划(哨兵不挂,与今日该分支无哨兵一致)。
    """
    item_name: str
    char_name: str
    row: str
    slot: int


@dataclass(frozen=True)
class EquipPlanBuild:
    """装备穿戴计划产出(``_build_equip_wear_plan`` 返回载体;ADR-0601 §3-C1)。

    - ``steps``: 机械执行计划(EquipWearStep 列表,产出期快照,pass 内恒稳);
    - ``empty_reason``: 计划空时的具名原因(字面量与今日 op 停手归因逐字
      相等——``classify_zero_wear_stop_reason`` 词表与分键锁零漂移);
      非空计划时为 ''(发射契约 NOOP 形态的产生位);
    - ``fail_reason``: 资源前置缺失原因(模板/tm_grays/rect None → 走本
      通道 ok=False 闩不置,同今日 op round_fail 同形);非空时 steps=[] 且
      不与 empty_reason 并用;
    - ``branch``: 'm7'(M7 角色级分配)| 'front_only'(身份读失败回退;
      空计划 NOOP 不挂哨兵,与今日该分支无哨兵覆盖一致);
    - ``owned_wearable_names``: 本帧可穿名单(零穿戴哨兵双挂点之计划面输入;
      哨兵内部再做工具类过滤,幂等)。
    """
    steps: list = field(default_factory=list)
    empty_reason: str = ''
    fail_reason: str = ''
    branch: str = 'm7'
    owned_wearable_names: list[str] = field(default_factory=list)


def _build_equip_wear_plan(session: Any,
                           registry: Any = None) -> EquipPlanBuild:
    """装备穿戴计划产出位(分发段;ADR-0601 §3-C1 计划随指令下发)。

    事实源 = **容器 game state 读口**(迭代 2026-09-18-prep-obs-retirement
    阶段 3.2 换源):owned ← ``gs.equips``、occupied ← ``gs.occupied_equips``
    (键 'front:1' 形态)、deployed ← 容器行域 ``deployed_rows_of``、
    后排选档 ← ``gs.back_layout`` Field 原值;写者单一源 = cw_screen_prep
    观察装配点(装备域采集单一源 = ``obs.cw_observe_full.observe_full``
    heavy)。
    本函数**零读屏**:原对执行帧现读三路
    owned/occupied/deployed 退役 = 调用位置迁移——识别函数本体归观察链
    复用(识别机制不出端口,obs.cw_observe_full 采集);kernel 判据单一
    源求值(释放判据表/hold 逐件/词缀序/环境变体 → equip_allocation)
    → 静态计划(EquipWearStep 列表)随 op 构造下发。

    新鲜度语义(执行帧现读退役的架构内解法):计划 = 入口观察期快照;
    发射后执行前板面漂移(合成耗件/列 reflow)→ 计划步定位 miss →
    装备版计划失效 round_fail → 下帧重派 → 重新入口观察,不回退执行链
    现读。观察范围外的派生字段(配对守卫/hold 判据等)保持策略层纯计算
    (kernel 判据零改动)。

    op 侧四 kernel 判据(resolve_wear_release/classify_item_hold/
    apply_equip_env_variants/resolve_affix_priority_order)在
    cw_op_equip_all.py 零引用(机械执行红线)。W880 装备环境信号
    「构造点唯一」契约维持:唯一构造点 = 本函数。

    失读通道(契约保真位,与 empty_reason 合法稳态禁并用):黑板帧缺失 /
    owned None(模板库或装备区 rect 缺失)/ occupied None(TM grays 缺失)
    → fail_reason 通道(未发出,闩不置,下帧重派;资源缺失原因在采集层
    observe_full log 留证,此处 fail_reason 保留分键关键词)。

    **签名边界(批 2a)**:形参 = (session, registry)——原
    ctx 鸭子形参收窄为决策链可达两件(session 黑板帧/
    registry 判据开关),发射位(mandate M7)与执行位薄派发两调用面同参;
    形参类型 Any(duck 型,kernel 零 app import)。
    """
    from sr_od.application.currency_war.data.cw_equipment_data import (
        EQUIP_TOOL_CATEGORY,
        EQUIPMENTS,
    )
    from sr_od.application.currency_war.kernel.cw_comps import (
        EQUIP_CAPACITY,
        _wearable_gate_ok,
    )
    from sr_od.application.currency_war.kernel.cw_equip_env import (
        classify_item_hold,
        resolve_affix_priority_order,
        resolve_wear_release,
    )

    # ===== 事实源前置(容器现读,零读屏;fail_reason 通道)=====
    # 全面换源(迭代 2026-09-18-prep-obs-retirement 阶段 3.2):owned/
    # occupied/back_layout/deployed 四路输入全部改容器读口,黑板帧
    # (gs.prep_obs)消费清零。None 语义映射 = 容器 Field 未观察(None)
    # = 识别域未就绪,fail 门保守关方向与旧黑板 None 逐位同。
    from sr_od.application.currency_war.kernel.cw_game_state import (
        deployed_rows_of,
        game_state_of,
    )
    _gs_c = game_state_of(session)
    _owned_v = _gs_c.equips.value
    if _owned_v is None:
        return EquipPlanBuild(
            fail_reason='装备观察域未就绪:owned'
                        '(cw_equip 模板库未加载/区域-道具装备 缺失)')
    owned_names = list(_owned_v)
    _occupied_v = _gs_c.occupied_equips.value
    if _occupied_v is None:
        return EquipPlanBuild(
            fail_reason='装备观察域未就绪:occupied'
                        '(cw_equip TM grays 未加载)')
    # occupied 容器键 'front:1' 形态 → 求值键 (row, 物理槽位 1-based)
    # (坐标系正本 = cw_prep_actions.PrepObservation.occupied_equips 声明);
    # 防御拷贝(计划求值全程本地态,禁反向污染容器)。
    occupied_all: dict = {(key.split(':', 1)[0], int(key.split(':', 1)[1])):
                          list(names)
                          for key, names in _occupied_v.items()}
    # back_layout 读 Field 原值:None(未观察) = 布局未知双弃权帧,有值 =
    # 槽数(禁 back_capacity_of——其 None→6 缺省翻转弃权语义);
    # 依据 = 迭代详设 obs-retirement §阶段 3.2-4。
    _bk_raw = _gs_c.back_layout.value
    _bk_n = int(_bk_raw) if _bk_raw is not None else None
    # 容器行域现读(benchchar-retirement P4:(front_row, back_row) 的 Unit,
    # 排归属由行承载,零 legacy 槽表换形)
    deployed_rows = deployed_rows_of(_gs_c)
    _has_deployed = any(units for units in deployed_rows)
    _tgt_comp = strategy_state_of(session).target_comp
    # ⚖️ 过渡期持有语义修正(r70 审计刀②):过渡期**穿给当前上场的 5 人**
    # ——key_equips 命中件照穿,非 key 散件穿给当前板面高战力者(carry 优先);
    # 「攒给成型核心」只在**已定型**(非双轨)且 form 低时保留。
    # 装配源换源(ADR-0530 决策2 核销):执行侧装配源 =
    # session 容器单例(备战帧观察写端同链刷新);容器与帧同帧同源
    # (同一备战观察),读口 = 容器公共读口单一源。
    _form = 0.0
    if _tgt_comp is not None and _has_deployed:
        from sr_od.application.currency_war.kernel.cw_comps import (
            form_progress,
        )
        _form = form_progress(_tgt_comp, _gs_c)
    # W629-R1 扩口(批 2):state/last_state 通道读点点名迁移——
    # committed 读端唯一化(decision_v2.prep_brain.committed_from,
    # 内部 = cw_intention 权威派生)。
    from sr_od.application.currency_war.kernel.cw_intention import (
        committed_from as _committed_from,
    )
    _committed = (_committed_from(session, _gs_c)
                  if (_gs_c is not None
                      and _gs_c.node.value is not None) else False)   # 缺供给 = 双轨保守侧(D2)
    # r388(用户 live 质问「1-2 就乱装备」):开局轮(r≤2,奖励节点无战斗)
    # 穿装备零战斗变现;key_equips 命中件照穿,gen 散件攒到 r3 战斗轮再穿。
    # R3 修正(ADR-0257):开局 hold 不再依赖 target 存在。
    # hold 块换源:node 未观察镜像回 None。
    _hold_node = (_gs_c.node.value if _gs_c is not None else None)
    _round_now = (_hold_node.round_num
                  if (_hold_node is not None
                      and _hold_node.plane == 1) else None)
    # ADR-0461:hold 收窄+生锈豁免,开关走策略 registry
    # (DecisionV2Strategy 注入臂可达;default 栈无 registry 属性 → 缺省表
    # =全关,零漂移)。
    from sr_od.application.currency_war.kernel.cw_exec_state import ledger_node_type
    from sr_od.application.currency_war.kernel.cw_registry import (
        DEFAULT_REGISTRY,
    )
    _reg_eq = (registry or DEFAULT_REGISTRY)
    _node_type = ((_hold_node.kind or None)
                  if _hold_node is not None else None)
    if _node_type is None and _hold_node is not None and _round_now is not None:
        _node_type = ledger_node_type(session,
                                      _hold_node.plane,
                                      _round_now)
    # O1 门输入(21 号稿 §2.3):后随节点 = 本备战帧之后第一个节点的
    # 台账类型(r+1);缺档 None → 门不中。
    _next_node_type = (
        ledger_node_type(session, _hold_node.plane,
                         _round_now + 1)
        if (_hold_node is not None
            and _round_now is not None) else None)
    # W880 装备环境信号单源(设计 §2.2):构造点唯一 = 本函数,一次打包
    # 传递;state 缺失(离线/旧栈)= 空集 → 判据安全默认不启用。
    from sr_od.application.currency_war.kernel.cw_equip_env import (
        apply_equip_env_variants as _apply_env_variants,
    )
    from sr_od.application.currency_war.kernel.cw_equip_env import (
        build_equip_env_signals,
    )
    _equip_signals = build_equip_env_signals(_gs_c)
    # 释放判据表(ADR-0526)+ 收窄(ADR-0531):row1(opening) 域扣留收窄为
    # 逐件判定(classify_item_hold),帧级 ``.hold`` 只辖 row2 域。
    _release = resolve_wear_release(
        _round_now, _node_type,
        _reg_eq.opening_hold_battle_gate_enabled,
        _reg_eq.opening_hold_battle_nodes,
        _tgt_comp, _form, _committed,
        sorted(_equip_signals.enemy_affixes),
        _reg_eq.rust_wear_release_enabled,
        next_node_type=_next_node_type)
    _hold = _release.hold
    # fill 防线③(设计 §3.1):row2 帧级扣留不激活 fill——
    # hold 语义(攒给成型核心)优先,防两套意图打架
    _fill_hold = _hold
    if _release.rust_release and (_release.opening_hold
                                  or _release.committed_hold):
        log.info('[cw-equip] 库藏生锈在场 → hold 豁免(owned 滞留喂敌),全量穿戴')
    elif _release.opening_hold or _hold:
        log.info('[cw-equip] hold 域活跃(row1=%s O1战斗前置=%s row2=%s '
                 'node=%s next_node=%s rust=%s penalty=%s form=%.2f):'
                 'opening 扣留收窄为逐件判定(21 号稿 §2.3)',
                 _release.opening_hold, _release.battle_precede_release,
                 _release.committed_hold, _node_type, _next_node_type,
                 _release.rust_release, _release.output_penalty_release,
                 _form)
    if _has_deployed:
        # W209g 断点③语义保留:后排 occupied 采集随布局选档(ADR-0385/0387
        # 双通道单一源)——本处只消费采集产物。
        occupied_m7: dict[tuple[str, int], list[str]] = occupied_all
        deployed_by_name: dict[str, list] = {}
        _row_units: list[tuple[str, object]] = (
            [('front', u) for u in (deployed_rows[0] or [])]
            + [('back', u) for u in (deployed_rows[1] or [])])
        for _rn, d in _row_units:
            if d.char_id:
                deployed_by_name.setdefault(d.char_id, []).append((_rn, d))
        log.info('[cw-equip] M7 角色级分配:deployed=%s occupied=%s',
                 [(rn, d.char_id, d.slot) for rn, d in _row_units],
                 {f'{r}{s}': '+'.join(v) for (r, s), v in occupied_m7.items() if v})
        # (原 hits = read_equips 执行帧现读退役:owned 件名池 = 入口观察
        #  产物 owned_names。M7 计划消费只辖件名——read_equips 的坐标分量
        #  归执行位定位读(机械现读,合法),不在计划面。)
        wearable = [n for n in owned_names
                    if EQUIPMENTS.get(n) is not None
                    and EQUIPMENTS[n].category != EQUIP_TOOL_CATEGORY]
        # ADR-0391 λ 标定埋点(P14 假设表 λ 行「待遥测标定」的数据源):
        # 每次派发记 owned 全量快照(含工具;每 pass 恰一次 = 每次派发至多
        # 调本函数一次)——离线 diff 相邻轮快照 = 各节点发放件数。
        # (换源:plane/round 取容器 node;未观察显 '?' 同旧缺帧形态)
        _ref_node = (_gs_c.node.value
                     if _gs_c is not None else None)
        _own_ct: dict[str, int] = {}
        for n in owned_names:
            _own_ct[n] = _own_ct.get(n, 0) + 1
        log.info('[cw!][grant] plane=%s round=%s owned=%s',
                 _ref_node.plane if _ref_node is not None else '?',
                 _ref_node.round_num if _ref_node is not None else '?',
                 _own_ct)
        # 判读锚点(P14 检验点 2):「缺什么囤什么」——目标 K 的
        # 组件需求 − 当前库存正差,判读/值守按此报装备面。
        if _tgt_comp is not None and _tgt_comp.key_equips:
            from sr_od.application.currency_war.data.cw_synthesis import (
                hoard_gaps,
            )
            gaps = hoard_gaps(list(_tgt_comp.key_equips), list(owned_names))
            log.info('[cw!][hoard] gaps=%s', gaps or '库存已覆盖需求')
        if not wearable:
            log.info('[cw-equip] 无穿戴候选(count=%d,全工具/空)→ 计划空',
                     len(owned_names))
            return EquipPlanBuild(
                empty_reason='pool_empty(无穿戴候选)',
                branch='m7',
                owned_wearable_names=wearable)
        # 21 号稿 §2.3 消费位逐件化(v3,S6/B1):帧级布尔 hold 改
        # 件级判定——同帧可「自由件穿+key 命中穿+保留域件扣」并存。
        # free_slot = O2 门输入(存在有空装备槽的在场角色;源 = 入口
        # 观察产物 occupied_equips,非现读)。
        _free_slot_any = any(len(v) < EQUIP_CAPACITY
                             for v in occupied_m7.values())
        _releasable = [n for n in wearable
                       if not classify_item_hold(
                           _release, n, _tgt_comp, _free_slot_any)]
        if not _releasable:
            # row1/row2 分键停手(21 号稿 §5 遥测分键)
            if _release.opening_hold:
                log.info('[cw-equip] opening(row1) 三门全不中'
                         '(保留域扣留)→ 计划空')
                _reason = ('opening_hold(row1):三门全不中'
                           '(保留域扣留)')
            else:
                log.info('[cw-equip] 扣留帧无 key_equips 命中(全攒着)→ 计划空')
                _reason = '过渡期hold:无 key_equips 命中(全攒着)'
            return EquipPlanBuild(
                empty_reason=_reason, branch='m7',
                owned_wearable_names=wearable)
        # ADR-0526 词缀条件优先层在**释放帧**重排(释放动作的次序)。
        _priority_order = resolve_affix_priority_order(
            _tgt_comp, deployed_rows,
            sorted(_equip_signals.enemy_affixes), occupied_m7)
        # W880 装备分配入口(kernel/cw_equip_env.apply_equip_env_variants)。
        alloc, _env_actions = _apply_env_variants(
            _equip_signals, _reg_eq, session, _tgt_comp,
            deployed_rows, _releasable, occupied_m7,
            hold_active=_fill_hold,
            priority_order=_priority_order)
        if not alloc:
            # W596/W593 方案③:分配空做结构化归因(pool_empty/capacity_full/
            # pairing_guard/no_deployed/unknown)。
            from sr_od.application.currency_war.kernel.cw_comps import (
                equip_alloc_empty_reason,
            )
            _empty_reason = equip_alloc_empty_reason(
                _tgt_comp, deployed_rows, _releasable,
                occupied_m7)
            log.info('[cw-equip] 分配方案空 原因=%s(owned=%s)→ 计划空',
                     _empty_reason, _releasable)
            return EquipPlanBuild(
                empty_reason=f'分配方案空:{_empty_reason}', branch='m7',
                owned_wearable_names=wearable)
        # (row, slot) 戳记:alloc 对 → 计划步目标物理槽位。
        # 遍历序与执行位解析一致(deployed_by_name 首个静态可解析者);
        # 全部不可解析的对不入计划;计划 for 有界。
        steps: list = []
        for char_name, want in alloc:
            _picked: tuple[str, int] | None = None
            for _row, d in deployed_by_name.get(char_name) or []:
                _slot = int(getattr(d, 'slot', 0) or 1)
                if (_row == 'front' and 1 <= _slot <= 4) \
                        or (_row != 'front' and 1 <= _slot <= (_bk_n or 6)):
                    _picked = (_row, _slot)
                    break
            if _picked is None:
                log.info('[cw-equip] %s 槽位坐标缺失 → 跳过该分配项(计划面)',
                         char_name)
                continue
            steps.append(EquipWearStep(item_name=want, char_name=char_name,
                                       row=_picked[0], slot=_picked[1]))
        return EquipPlanBuild(steps=steps, branch='m7',
                              owned_wearable_names=wearable)
    # ===== front-only 回退分支(身份读失败 fallback;ADR-0101 key_equips
    # 优先;求值块自 op 整体搬迁,一并计划化不设豁免)=====
    # 前排已穿槽 = 入口观察产物 occupied_equips 的前排切片(键坐标系
    # 同采集层;原 read_row_equipped 现读退役)。
    occupied = {slot: names for (row, slot), names in occupied_all.items()
                if row == 'front'}
    if occupied:
        log.info('[cw-equip] 前排已穿槽(跳过不覆盖): %s',
                 {k: '+'.join(v) for k, v in sorted(occupied.items())})
    slots = _empty_slots(occupied, FRONT_SLOT_COUNT)
    unknown = [n for n in owned_names if EQUIPMENTS.get(n) is None]
    if unknown:
        log.warning('[cw-equip] owned 观察命中但不在 EQUIPMENTS registry(名对齐缺失?R18 P1): %s',
                    sorted(set(unknown)))
    # 过滤工具类(拆装扳手/冶金炉等非 drag 穿);⚠️ 过滤只辖**穿戴决策**
    # (wearable)。位置分量已无计划面消费,零元组仅保 _prioritize_wearable
    # 元组契约形状。
    _wearable_all = [n for n in owned_names
                     if EQUIPMENTS.get(n) is not None
                     and EQUIPMENTS[n].category != EQUIP_TOOL_CATEGORY]
    # 回退帧穿戴门(fail-closed):回退帧 char='' 无 per-char 语境,判定
    # 单源 ``_wearable_gate_ok`` 三谓词中 W1(worn 输入)与 W2(空栏前置)
    # 无信息恒过 = 与历史行为等价;生效面 = W3 专属门——件级门(银狼专属
    # 10 件)与类别门(骇客类)命中件 × char 不在白名单 → 拒,只放无门件。
    # 不对称取向与 W3 主路径一致(错杀 = 件滞留 owned;漏放 = 拖错白拖
    # + 安灯)。单源复用先例 = equip_alloc_empty_reason 同消费本函数,
    # 禁回退分支内联白名单(分配语义与分配空诊断不漂移)。
    wearable = []
    _gate_held: list[str] = []
    for _n in _wearable_all:
        if _wearable_gate_ok([], '', _n):
            wearable.append((_n, (0, 0)))
        else:
            _gate_held.append(_n)
    if _gate_held:
        log.info('[cw-equip] 回退帧专属门拒穿(fail-closed,滞留 owned): %s',
                 sorted(set(_gate_held)))
    if not slots:
        # 「前排 avatar 全已穿」→ 空计划具名 NOOP(回退分支不挂哨兵)。
        log.info('[cw-equip] 前排 avatar 全已穿 → 计划空(回退分支)')
        return EquipPlanBuild(empty_reason='前排 avatar 全已穿',
                              branch='front_only',
                              owned_wearable_names=[n for n, _p in wearable])
    if not wearable:
        log.info('[cw-equip] 无穿戴候选(count=%d,全工具/空)→ 计划空(回退分支)',
                 len(owned_names))
        return EquipPlanBuild(empty_reason='pool_empty(无穿戴候选)',
                              branch='front_only',
                              owned_wearable_names=[])
    # comp 驱动穿戴(ADR-0101):优先穿 target_comp.key_equips 命脉件。
    _key_equips = (_tgt_comp.key_equips if _tgt_comp is not None else None)
    wearable = _prioritize_wearable(wearable, _key_equips)
    # 排序后候选 × 空槽序 zip(产出期快照;中途合成耗件 → 计划步定位
    # miss → 计划失效 fail-fast,与 M7 主路径同一失效通道)。
    steps_fb: list = []
    for (name, _pos), slot_idx in zip(wearable, slots, strict=False):
        steps_fb.append(EquipWearStep(item_name=name, char_name='',
                                      row='front', slot=int(slot_idx)))
    return EquipPlanBuild(steps=steps_fb, branch='front_only',
                          owned_wearable_names=[n for n, _p in wearable])
