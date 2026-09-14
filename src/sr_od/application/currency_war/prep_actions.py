"""货币战争 备战决策环 原子动作全集 + 执行器(P1;strategy/03(原 doc 15§4)/§13)。

框架层:本模块**不含玩法判断**(何时收球/卖谁/何时出战 = 策略层 CwStrategy.decide_prep_screen),
只负责「机械执行一个动作」(用户裁定 2026-09-10:动作 op 只管机械执行,
禁止做任何验证——点击/拖拽后不读屏判「是否生效」,落地判定完全归观察侧
reconcile 对账;T-223 终裁:执行回执 ``(progressed, detail)`` 退役,
``execute`` 无返回,发出即职责完成)。失败路径(§13.2 修订):
- 参数非法 → validate 返回错误串(Director 拒绝执行 + 交回留证);
- 执行前输入契约拒绝(球/箱/按钮等目标不在,执行前观察,M6 边界面)→
  本动作未发出,机械交回外循环重观察重决策;
- 执行异常 → 异常上抛(Director 上抛 = 本环 fail,外层 op retry 接管)。
原第三路径「验证失败 → progressed=False」随验证拆除退役。

slot 语义全局统一(§13.1):**物理槽位** —— 备战栏 1-9 / 前排 1-4 / 后排 1-N;非 bench 列表下标!
与族 A(cw_state.Action 策略动作)同名类(SellBench/DeployMove/SellDeployed)的坐标系对照:
族 B 物理槽位 = 族 A 下标 + 1(bench 域);deployed 域两族结构不同(族 B=row+slot
物理排槽位,族 A=紧缩列表下标)——完整对照表见 cw_state.py Action 节约定块。
组合动作命名映射(§7 L1):RunDeploy=CwOpDeploy / RunEquip=CwOpEquipAll(RunBuyPhase 组合已随 shop.py 壳退役删除,W970 批 C 后决策核只发显式开店意图)
(P1 过渡,P2/P3 溶解为原子)。
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_economy import XP_CLICK_COST_FALLBACK
from sr_od.application.currency_war.kernel.cw_exec_state import (
    _advance_gold,
    exec_state_of,
)

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_exec_state import BenchChar
from sr_od.application.currency_war.kernel.cw_obs_core import (
    SCREEN_NAME,
    SHOP_SCREEN_NAME,
    _area_rect,
    _ocr,
    area_center,
)
from sr_od.application.currency_war.kernel.cw_prep_actions import (
    PREP_ACTION_TYPES,
    BailToOuter,
    ClickSpheres,
    DeferSpheres,
    DeployMove,
    EnsureShopClosed,
    EnsureShopOpen,
    LevelUp,
    OpenBox,
    OpenTome,
    PickBoxCard,
    PrepAction,
    RunDeploy,
    RunEquip,
    RunTools,
    SellBench,
    SellDeployed,
    StartBattle,
)
from sr_od.application.currency_war.kernel.cw_strategy_session import strategy_state_of
from sr_od.application.currency_war.obs.cw_identity_obs import (
    read_reward_spheres,
    read_supply_boxes,
)
from sr_od.application.currency_war.obs.cw_observation import read_gold
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation

#: overlay 弹出/关闭的固定动画等待(等待归产生动画的操作)。
#: 原为事件驱动轮询上界 1.8s(1.5s 旧固定值 + 0.3s 轮询间隔,依据:单局
#: 耗时审计报告 .debug/temp/currency_war/w417_duration_audit/REPORT.md
#: 「需验证·出战链」)——判效半拆除(用户裁定 2026-09-10)后收敛为固定
#: 等待,值取原上界保最坏情形覆盖面不缩水;弹窗就位与否交下一帧观察。
_OVERLAY_ANIM_WAIT_S: float = 1.8

#: 商店收起动画时长(操作完成自等动画;实测口径 screen_flow_timing
#: #15「收起过场动画 ~1s 即备战画面稳定」,用户口述。op 完成后显式等待,替代
#: 测量驱动 gate——画面状态判断已外移建档识别层,等待时长归产生动画的操作声明)。
SHOP_CLOSE_ANIM_S: float = 1.0
#: 商店打开动画时长(固定时长自等;用户口述定值 2026-09-02「干净的备战
#: 里打开商店,只要等 1 秒就够了」。开态判定由下一帧观察侧 0n 三锚承载。
#: 自动开店场景不经此处——cw_loop 备战分支按「备战阶段」识别)。
SHOP_OPEN_ANIM_S: float = 1.0


class StopBrakeShortCircuit(RuntimeError):
    """W209j 停机短路异常(ADR-0388 纵深防御第二层)。

    语义 = 运行中被停 → 拒绝执行任何动作(run 27 实证:director 环在
    Deploy 钩子 stop_running 后仍发 StartBattle 点出战——环顶检查(第一层)
    之外,本入口兜底覆盖绕环路径)。原表达通道 = 执行回执 ``(False, '已
    停止[W209j刹车]')``,随 T-223 回执退役改为停机短路异常:执行器抛出,
    调用方(cw_screen_prep 决策环 / cw_loop 发射核)捕获后交回外循环,
    下轮 loop 顶见 STOP 退出。判据 = last_run_result 非空(start 清
    None/stop 写入;run_state STOP 是 idle 初始态不能直接用)。
    """


def _read_level_raw(ctx: SrContext, screen) -> int | None:
    """OCR 直读等级数字(「文本-等级」区,**无 _expected_level 兜底**)。

    read_level 的兜底曲线适合决策估值,不适合作击数推导基线(期望值>实际时
    推导失真)。漏读返 None,调用方决定基线退路。放大读与读链单一源 =
    ``cw_observation.read_level_raw_opt``。
    """
    from sr_od.application.currency_war.obs.cw_observation import read_level_raw_opt

    return read_level_raw_opt(ctx, screen)


def row_area_centers(ctx: SrContext, prefix: str) -> list[Point]:
    """从 screen_info「货币战争-备战」读全部 prefix-N 区域中心(N 升序)。

    同 CwOpDeploy._row_centers 逻辑(读全不硬编码,后排 >6 时 screen_info 补区后自动跟上);
    prep_actions 执行器 / cw_screen_prep 观察共用。
    """
    si = ctx.screen_loader.get_screen(SCREEN_NAME)
    if si is None:
        return []
    pts: list[tuple[int, Point]] = []
    pfx = f'{prefix}-'
    for a in si.area_list:
        if a.area_name.startswith(pfx) and a.pc_rect is not None:
            try:
                n = int(a.area_name[len(pfx):])
            except ValueError:
                continue
            pts.append((n, a.pc_rect.center))
    pts.sort(key=lambda t: t[0])
    return [p for _, p in pts]


def sell_point(ctx: SrContext) -> Point:
    """出售区落点(单一源):screen_info「货币战争-备战.区域-出售区」中心
    (ADR-0329 W62 件2 落地;游戏机制 = 拖到左下区域即出售,无按钮)。

    area 缺失 = 建档漂移/档案损坏 → RuntimeError 显式上抛(信息带 area
    名),禁回退硬编码坐标静默点击(坐标单一真相源)。消费面含
    cw_op_deploy 卖 off-target 拖拽,落点直入 drag 原语 → None 不可流入,
    直取 + 上抛是唯一兼容形态。
    """
    pt = area_center(ctx, '区域-出售区')
    if pt is None:
        raise RuntimeError(
            'area 缺失:区域-出售区(货币战争-备战),出售区落点不可派生,禁兜底坐标')
    return pt


def drag_bench_to_sell(op: SrOperation, ctx: SrContext, bench_idx: int) -> None:
    """拖备战槽(槽位下标 0-8)→ 出售区(共享卖原语,W62 件2/设计章2.10)。

    d2 卖通道生产接线(shop.py prefix 循环 SellBench 分支)与 prep_actions
    ``_sell_bench`` 共用本 helper:「拖→出售区」机械一段(T-192 拆源槽
    像素验重试:发出即职责完成,落地事实归观察侧 reconcile 对账);
    tracking 同步由调用方各自做。失焦守卫同 ``PrepActionExecutor._drag``
    语义(窗口后台化时拖拽输入静默丢,r9 实证)。

    Args:
        op: 调用方 op(取 ctx.controller 操作)。
        ctx: SrContext。
        bench_idx: 槽位下标 0-8(ADR-0316:列表下标 = 物理备战栏槽位 1-9 减一);
            越界 = 调用方 bug,响亮上抛(守卫非判效)。
    """
    pts = row_area_centers(ctx, '备战栏')
    if not (0 <= bench_idx < len(pts)):
        raise AssertionError(
            f'[cw][guard] 卖出拖拽槽位越界:bench_idx={bench_idx}'
            f'(备战栏 area 数={len(pts)};调用方 bug 响亮暴露)')
    try:
        gw = ctx.controller.game_win
        if not gw.is_win_active:
            log.warning('[cw!][drag] 窗口失焦(拖拽输入将静默丢)→ 先激活')
            gw.active()
            time.sleep(0.3)
    except Exception:   # noqa: BLE001  焦点守卫 best-effort
        pass
    from sr_od.application.currency_war.operations.dev.drag_cw_char import (
        DragCwChar,
    )
    DragCwChar.drag_char(op, pts[bench_idx], sell_point(ctx))


# (血购回执行挂点已随 exogenous 流写入端退役删除——删除波 1;
#  血本位消费事实的现役证据 = 注册表建模期望账(blood_xp_mode)与结算域
#  观察链,装配端 hp_pay_defects 对账面随流冻结。)


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


def _build_equip_wear_plan(ctx: SrContext) -> EquipPlanBuild:
    """装备穿戴计划产出位(分发段;ADR-0601 §3-C1 计划随指令下发)。

    P4 观察接线(T-171):三路事实源 = **入口观察产物**
    ``session.prep_obs_frame``(PrepObservation;写者白名单 = cw_screen_prep
    观察装配点/循环投影步,装备域采集单一源 = ``obs.cw_observe_full
    .observe_full`` heavy)。本函数**零读屏**:原对执行帧现读三路
    owned(read_equips)/occupied(read_row_equipped)/deployed
    (read_deployed_chars)退役 = 调用位置迁移——识别函数本体归观察链
    复用(识别机制不出端口,obs.cw_observe_full 采集),op 外读屏白名单
    待申报面随之消点(架构正本 §1.1 白名单制);kernel 判据单一源求值
    (释放判据表/hold 逐件/词缀序/环境变体 → equip_allocation)→ 静态
    计划(EquipWearStep 列表)随 op 构造下发。

    新鲜度语义(执行帧现读退役的架构内解法,note 判据③):计划 = 入口
    观察期快照;发射后执行前板面漂移(合成耗件/列 reflow)→ 计划步定位
    miss → 装备版 ``STATUS_PLAN_STALE`` round_fail → 下帧重派 → 重新入口
    观察,不回退执行链现读。观察范围外的派生字段(配对守卫/hold 判据等)
    保持策略层纯计算(kernel 判据零改动)。「执行时刻屏态复验」职权留守
    派发位(``_run_equip`` 的 ``_guard_screen_mismatch`` 前置闸,用户裁定
    背书的分发层复验先例),与本读容器互不替代。

    op 侧四 kernel 判据(resolve_wear_release/classify_item_hold/
    apply_equip_env_variants/resolve_affix_priority_order)在
    cw_op_equip_all.py 零引用(机械执行红线,验收锁
    test_cw_equip_plan_builder::test_equip_op_kernel_criteria_free)。
    W880 装备环境信号「构造点唯一」契约维持:唯一构造点 = 本函数。

    失读通道(契约保真位,与 empty_reason 合法稳态禁并用):黑板帧缺失 /
    owned None(模板库或装备区 rect 缺失)/ occupied None(TM grays 缺失)
    → fail_reason 通道(未发出,闩不置,下帧重派;资源缺失原因在采集层
    observe_full log 留证,此处 fail_reason 保留分键关键词)。
    """
    from sr_od.application.currency_war.data.cw_equipment_data import (
        EQUIP_TOOL_CATEGORY,
        EQUIPMENTS,
    )
    from sr_od.application.currency_war.kernel.cw_comps import (
        EQUIP_CAPACITY,
    )
    from sr_od.application.currency_war.kernel.cw_equip_env import (
        classify_item_hold,
        resolve_affix_priority_order,
        resolve_wear_release,
    )
    from sr_od.application.currency_war.operations.cw_op.cw_op_equip_all import (
        DRAG_FAIL_BLACKLIST_LIMIT,
        EquipWearStep,
        _empty_slots,
        _prioritize_wearable,
        equip_drag_key,
        filter_alloc_blacklisted,
    )

    # ===== 事实源前置(读入口观察产物,零读屏;fail_reason 通道)=====
    _match = ctx.cw_match
    _sess = (_match.session if _match is not None else None)
    obs = (getattr(_sess, 'prep_obs_frame', None)
           if _sess is not None else None)
    if obs is None:
        return EquipPlanBuild(
            fail_reason='备战观察帧缺失(黑板契约:入口观察先于派发)')
    if getattr(obs, 'owned_equips', None) is None:
        return EquipPlanBuild(
            fail_reason='装备观察域未就绪:owned'
                        '(cw_equip 模板库未加载/区域-道具装备 缺失)')
    if getattr(obs, 'occupied_equips', None) is None:
        return EquipPlanBuild(
            fail_reason='装备观察域未就绪:occupied'
                        '(cw_equip TM grays 未加载)')
    owned_names = list(obs.owned_equips)
    # occupied 键坐标系 = (row, 物理槽位 1-based),采集层直出;防御拷贝
    # (计划求值全程本地态,禁反向污染黑板帧)。
    occupied_all: dict = {(row, int(slot)): list(names)
                          for (row, slot), names in obs.occupied_equips.items()}
    _bk_n = getattr(obs, 'back_layout_slots', None)
    deployed = list(getattr(obs, 'deployed_chars', None) or [])
    _tgt_comp = (strategy_state_of(_match.session).target_comp
                 if (_match is not None and _match.session is not None) else None)
    # ⚖️ 过渡期持有语义修正(r70 审计刀②,替 2026-08-16 旧指示):旧版 form<COMMIT_FRAC
    # 全 P1 攒仓库 = 白板打 8 个战斗节点 + r9 boss(每场稳定掉血的确定性损失;r70 实证
    # P1 八战掉 62 血)。修正:过渡期**穿给当前上场的 5 人**——key_equips 命中件照穿
    # (未来迁给核心只付一次性拆卸),非 key 散件穿给当前板面高战力者(carry 优先);
    # 「攒给成型核心」只在**已定型**(非双轨)且 form 低时保留。
    # 装配源换源(T-146 尾批,ADR-0530 决策2 核销;桥登记集 prep 根消点):
    # 执行侧装配源 = session 容器单例(备战帧观察写端同链刷新);旧
    # last_state 帧链 + 过渡桥装箱退役。容器与帧同帧同源
    # (同一备战观察),读口 = 容器公共读口单一源。
    from sr_od.application.currency_war.kernel.cw_game_state import (
        board_state_of,
    )
    _bs_c = (board_state_of(_match.session)
             if (_match is not None and _match.session is not None) else None)
    _form = 0.0
    if _tgt_comp is not None and deployed and _bs_c is not None:
        from sr_od.application.currency_war.kernel.cw_comps import (
            form_progress,
        )
        _form = form_progress(_tgt_comp, _bs_c)
    # W629-R1 扩口(批 2):state/last_state 通道读点点名迁移——
    # committed 读端唯一化(decision_v2.prep_brain.committed_from,
    # 内部 = cw_intention 权威派生);旧形为 last_state 通道裸直读
    # 双轨字段,已并入守卫辖域(state 通道 grep 锁,
    # test_cw_w620/test_cw_migration_direction_layer)。
    from sr_od.application.currency_war.kernel.cw_intention import (
        committed_from as _committed_from,
    )
    _committed = (_committed_from(_match.session, _bs_c)
                  if (_match is not None
                      and _match.session is not None
                      and _bs_c is not None
                      and _bs_c.node.value is not None) else False)   # 缺供给 = 双轨保守侧(D2)
    # r388(用户 live 质问「1-2 就乱装备」):开局轮(r≤2,奖励
    # 节点无战斗)穿装备零战斗变现,且阵容未起步(form≈0 时
    # 分配语义退化为「谁在场谁独占」——r2 一人穿 2 件实证);
    # key_equips 命中件照穿(命中即阵容意图明确),gen 散件
    # 攒到 r3 战斗轮再穿。与 r70「P1 白板也该穿」不冲突:
    # 白板 8 战指的是 r3+ 战斗期,不含奖励轮。
    # R3 修正(ADR-0257):开局 hold 不再依赖 target 存在。
    # hold 块换源(T-146):node 未观察 ⟺ 旧 last_state None(同帧同源,
    # 容器 node = 备战帧顶栏解析写端);kind 空串按帧未识别镜像回 None。
    _hold_node = (_bs_c.node.value if _bs_c is not None else None)
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
    _reg_eq = (getattr(getattr(_match, 'strategy', None), 'registry', None)
               or DEFAULT_REGISTRY)
    _node_type = ((_hold_node.kind or None)
                  if _hold_node is not None else None)
    if _node_type is None and _hold_node is not None and _round_now is not None:
        _node_type = ledger_node_type(_match.session,
                                      _hold_node.plane,
                                      _round_now)
    # O1 门输入(21 号稿 §2.3):后随节点 = 本备战帧之后第一个节点的
    # 台账类型(r+1);缺档 None → 门不中(保守维持保留域判定,词汇表
    # 与 row1 同源 opening_hold_battle_nodes)。
    _next_node_type = (
        ledger_node_type(_match.session, _hold_node.plane,
                         _round_now + 1)
        if (_match is not None and _hold_node is not None
            and _round_now is not None) else None)
    # W880 装备环境信号单源(设计 §2.2):构造点唯一 = 本函数(求值块
    # 搬迁后;原构造点 = op 主循环前段),一次打包传递;
    # 生锈豁免(门)、变宝为废(序)等变体一律吃 signals,
    # 不再各自摸 state;state 缺失(离线/旧栈)= 空集 → 判据安全默认不启用。
    from sr_od.application.currency_war.kernel.cw_equip_env import (
        apply_equip_env_variants as _apply_env_variants,
    )
    from sr_od.application.currency_war.kernel.cw_equip_env import (
        build_equip_env_signals,
    )
    _equip_signals = build_equip_env_signals(_bs_c)
    # 释放判据表(ADR-0526)+ 收窄(ADR-0531):
    # 五行评估单点在策略侧;row1(opening) 域扣留收窄为「三门全不中 ∧
    # 保留域命中」的逐件判定(classify_item_hold),帧级 ``.hold`` 只辖
    # row2 域——hold 触发权归策略侧(§1.2-1),禁在执行层加第二套时机判断。
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
    if deployed:
        # W209g 断点③语义保留:后排 occupied 采集随布局选档(ADR-0385/0387
        # 双通道单一源)——选档已在采集层 observe_full 完成(_bk_n 随帧携带,
        # 布局未知帧该排不采集),本处只消费采集产物。
        occupied_m7: dict[tuple[str, int], list[str]] = occupied_all
        deployed_by_name: dict[str, list] = {}
        for d in deployed:
            if d.char_id:
                deployed_by_name.setdefault(d.char_id, []).append(d)
        log.info('[cw-equip] M7 角色级分配:deployed=%s occupied=%s',
                 [(d.char_id, d.position_pref, d.slot) for d in deployed],
                 {f'{r}{s}': '+'.join(v) for (r, s), v in occupied_m7.items() if v})
        # (原 hits = read_equips 执行帧现读退役:owned 件名池 = 入口观察
        #  产物 owned_names。M7 计划消费只辖件名——read_equips 的坐标分量
        # 归执行位定位读(机械现读,合法),不在计划面。)
        wearable = [n for n in owned_names
                    if EQUIPMENTS.get(n) is not None
                    and EQUIPMENTS[n].category != EQUIP_TOOL_CATEGORY]
        # (原派发位 last_owned_equips 全量重写 + bs.equips 观察写端退役:
        #  写端随采集归位备战入口观察链,写点 = cw_screen_prep._observe
        #  heavy 装配点(P4 观察接线 T-171)——本函数零读屏零采集。)
        # ADR-0391 λ 标定埋点(P14 假设表 λ 行「待遥测标定」的数据源):
        # 每次派发记 owned 全量快照(含工具;每 pass 恰一次 = _run_equip
        # 每次派发至多调本函数一次)——离线 diff 相邻轮快照 = 各节点发放
        # 件数 → λ 与事件条件化修正(P14 记账)。
        # (换源 T-146:plane/round 取容器 node;未观察显 '?' 同旧缺帧形态)
        _ref_node = (_bs_c.node.value
                     if (_match is not None and _bs_c is not None) else None)
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
        # 件级判定——同帧可「自由件穿+key 命中穿+保留域件扣」并存;
        # 原「扣留帧只穿 key_equips 命中件」过滤迁移入
        # classify_item_hold(求值序 O3→O1/O2→保留域→清单外)。
        # free_slot = O2 门输入(存在有空装备槽的在场角色;源 = 入口
        # 观察产物 occupied_equips,非现读)。
        _free_slot_any = any(len(v) < EQUIP_CAPACITY
                             for v in occupied_m7.values())
        _releasable = [n for n in wearable
                       if not classify_item_hold(
                           _release, n, _tgt_comp, _free_slot_any)]
        if not _releasable:
            # row1/row2 分键停手(21 号稿 §5 遥测分键:row1 域帧数
            # 趋零锚与 row2 committed hold 不回归锚预期相反,无
            # 分键则 O2 实机验收锚不可判读,v3,B3)
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
        # ADR-0526 词缀条件优先层在**释放帧**
        # 重排(释放动作的次序)。收窄后扣留收窄为
        # 逐件判定,可释放集非空即(部分)释放帧——序 = 策略侧决策层
        # 产物,每次派发重算(occupied 源 = 入口观察快照,计划产出位
        # 求值不变)。
        _priority_order = resolve_affix_priority_order(
            _tgt_comp, deployed,
            sorted(_equip_signals.enemy_affixes), occupied_m7)
        # W880 装备分配入口(kernel/cw_equip_env.apply_equip_env_
        # variants;fill3 量变体与变宝为废序变体已随各自开关族删除
        # ——旧方案清退批,清查报告 OLD_MIX_AUDIT §1.3,现=基分配
        # equip_allocation 直通零漂移)。
        alloc, _env_actions = _apply_env_variants(
            _equip_signals, _reg_eq, _match.session, _tgt_comp,
            deployed, _releasable, occupied_m7,
            hold_active=_fill_hold,
            priority_order=_priority_order)
        # (P1→P2 接口机制·②分配义务 hold 豁免已随五开关定谳清理
        # 删除,ADR-0487:过渡期 hold 过滤恢复无条件既有语义。)
        if not alloc:
            # W596/W593 方案③:分配空做结构化归因(pool_empty/capacity_full/
            # pairing_guard/no_deployed/unknown),替旧的一句话两义日志。
            from sr_od.application.currency_war.kernel.cw_comps import (
                equip_alloc_empty_reason,
            )
            _empty_reason = equip_alloc_empty_reason(
                _tgt_comp, deployed, _releasable,
                occupied_m7)
            log.info('[cw-equip] 分配方案空 原因=%s(owned=%s)→ 计划空',
                     _empty_reason, _releasable)
            return EquipPlanBuild(
                empty_reason=f'分配方案空:{_empty_reason}', branch='m7',
                owned_wearable_names=wearable)
        # 拖拽失败降级:剔除已拉黑(件→角色)对后再产计划步(失败 1 次的保留,
        # 补救链重试一次;再败即拉黑,不再进后续派发的计划)。过滤随产出位
        # (读同一 exec_state.equip_drag_fail_counts;登记/键函数留执行位)。
        _fail_counts: dict = {}
        if (_match is not None and _match.session is not None):
            _fail_counts = _match.exec_state.equip_drag_fail_counts
        alloc = filter_alloc_blacklisted(alloc, _fail_counts)
        if not alloc:
            log.info('[cw-equip] 分配对全部拉黑(拖拽连败)→ 计划空;'
                     ' 拉黑集=%s', sorted(_fail_counts))
            return EquipPlanBuild(
                empty_reason='分配对全部拉黑(drag 连败)', branch='m7',
                owned_wearable_names=[n for n, _ in wearable])
        # (row, slot) 戳记(本批新落名):alloc 对 → 计划步目标物理槽位。
        # 遍历序与今日执行位解析一致(deployed_by_name 首个静态可解析者);
        # 静态可解析 = front 1..4 / back 1..选档 N(与执行位 _slot_drag_point
        # 同构;执行时拖点仍机械现读,reflow 只会导致找不到件、不会拖错目标)。
        # 全部不可解析的对不入计划 = 今日「跳过该分配项」等价面;计划 for
        # 有界,无今日 stall<2 中断面(其余计划步照常执行)。
        steps: list = []
        for char_name, want in alloc:
            _picked: tuple[str, int] | None = None
            for d in deployed_by_name.get(char_name) or []:
                _row = getattr(d, 'position_pref', None) or 'back'
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
    # 优先;求值块自 op :869-930 整体搬迁,一并计划化不设豁免——豁免会把
    # 第二套微分配语义留在执行位,违反 ADR-0601 §3-C1 红线)=====
    from sr_od.application.currency_war.operations.cw_op.cw_op_equip_all import (
        CwOpEquipAll,
    )
    # 前排已穿槽 = 入口观察产物 occupied_equips 的前排切片(键坐标系
    # 同采集层:(row, 物理槽位 1-based);原 read_row_equipped 现读退役)。
    occupied = {slot: names for (row, slot), names in occupied_all.items()
                if row == 'front'}
    if occupied:
        log.info('[cw-equip] 前排已穿槽(跳过不覆盖): %s',
                 {k: '+'.join(v) for k, v in sorted(occupied.items())})
    slots = _empty_slots(occupied, CwOpEquipAll.FRONT_SLOT_COUNT)
    unknown = [n for n in owned_names if EQUIPMENTS.get(n) is None]
    if unknown:
        log.warning('[cw-equip] owned 观察命中但不在 EQUIPMENTS registry(名对齐缺失?R18 P1): %s',
                    sorted(set(unknown)))
    # 过滤工具类(拆装扳手/冶金炉等非 drag 穿);⚠️ 过滤只辖**穿戴决策**
    # (wearable)。位置分量已无计划面消费(计划步定位 = op 执行位机械
    # 现读,合法),零元组仅保 _prioritize_wearable 元组契约形状。
    wearable = [(n, (0, 0)) for n in owned_names
                if EQUIPMENTS.get(n) is not None
                and EQUIPMENTS[n].category != EQUIP_TOOL_CATEGORY]
    # (原回退分支 last_owned_equips 全量重写 + bs.equips 观察写端退役:
    #  写点已随采集归位备战入口观察链,同 M7 分支,P4 观察接线 T-171。)
    if not slots:
        # 「前排 avatar 全已穿」→ 空计划具名 NOOP(回退分支不挂哨兵,
        # 与今日该分支 success 跳过且无哨兵覆盖一致;今日 detail 字面
        # 保留进 reason 供分键)。
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
    # 拖拽失败降级:回退路径同主路径纪律——拉黑件不重试;回退路径无角色身份
    # (拖点=空槽 avatar),拉黑键取 (件名, '')。
    _fail_counts_fb: dict = {}
    if _match is not None and _match.session is not None:
        _fail_counts_fb = _match.exec_state.equip_drag_fail_counts
    wearable = [(n, p) for n, p in wearable
                if _fail_counts_fb.get(equip_drag_key(n, ''), 0)
                < DRAG_FAIL_BLACKLIST_LIMIT]
    if not wearable:
        log.info('[cw-equip] 回退路径候选全拉黑 → 计划空')
        return EquipPlanBuild(
            empty_reason='分配对全部拉黑(drag 连败)',
            branch='front_only', owned_wearable_names=[])
    # 排序后候选 × 空槽序 zip(产出期快照;中途合成耗件 → 计划步定位
    # miss → STATUS_PLAN_STALE fail-fast,与 M7 主路径同一失效通道)。
    steps_fb: list = []
    for (name, _pos), slot_idx in zip(wearable, slots, strict=False):
        steps_fb.append(EquipWearStep(item_name=name, char_name='',
                                      row='front', slot=int(slot_idx)))
    return EquipPlanBuild(steps=steps_fb, branch='front_only',
                          owned_wearable_names=[n for n, _p in wearable])

class PrepActionExecutor:
    """备战原子/组合动作执行器(框架层;持 ctx + 宿主 op 复用截图/区域匹配/拖拽原语)。

    宿主 op = CwScreenPrep(SrOperation);机械执行(点击/拖拽/等待),落地
    判定归观察侧 reconcile(用户裁定 2026-09-10);拖拽统一走
    DragCwChar.drag_char(中心拖 + hold0,2026-08-13 实测验证)。
    """

    BOX_SCREEN: ClassVar[str] = '货币战争-备战-武装箱选择'
    BOX_OPEN_DY: ClassVar[int] = 41                   # 「开启」文字区 = 箱 icon 下方偏移(2026-08-14 实测:槽center(563,911)→命中(565,952))
    CARD_Y: ClassVar[int] = 290                       # 武装箱卡身点击 y(点卡名下方一点避「查看详情」)
    LEVEL_MAX_CLICKS: ClassVar[int] = 12              # 升级单动作最多买经验次数(同 _handle_bench_full 量级)
    SPHERE_MAX_CLICKS: ClassVar[int] = 12             # 单动作点球硬上限(防识别抖动死循环)
    LAUNCH_DEAD_LIMIT: ClassVar[int] = 3   # 出战未落地连败停机阈值(session 级计数;两局实证环重入 ~2min/次)
    #: P4R:出战后「转移成功」的拦截弹窗白名单(锚 = 已建档 id_mark)。
    #: 出战按钮点击后备战标识消失但下列弹窗在场 = 出战被游戏拒(1-1 事故
    #: 「前台区域无角色」确认弹窗盖标识 = 旧判据假成功)。新弹窗建档后追加。
    POST_LAUNCH_BLOCKERS: ClassVar[tuple[tuple[str, str], ...]] = (
        ('货币战争-提示-前台无角色', '标识-无角色提示'),
    )

    def __init__(self, op: SrOperation, ctx: SrContext) -> None:
        self._op = op
        self._ctx = ctx
        # 机械执行摘要(最近一次 execute 的 detail;登记件解析输入,非成败
        # 回执——T-223 端口无返回,摘经由本属性旁路供 on_outcome detail)。
        self.last_detail: str = ''
        # 批4 挂账:StartBattle 发射位内部事实(A6 出战链判效面,批4 随
        # J3/J4 消费端同退役)。消费方 = cw_loop 发射核(J2/J3 达标臂/锁定
        # 重试)。getattr 容缺(__new__ 桩形态)。
        self.last_launch_ok: bool | None = None
        # 执行点金差显影(备战执行缝账务包络,T-16;写点 = execute 每次
        # 入口复位)。取值时机 = dispatch 后由 _executed_gold_delta 现算
        # 写入,None = 该动作执行点金差不可推算(诚实缺失,非 0);消费方
        # = 回执 extra 金差键与观察侧备战帧金对账。getattr 容缺
        # (__new__ 桩形态,execute 入口显式复位不依赖构造)。
        self.last_gold_delta: int | None = None
        # LevelUp 机械半边的实击花金累计(写入端 = _level_up 点击环;
        # 单击价单一源 = kernel xp_click_cost 逐击现算)。execute 入口
        # 复位 None,dispatch 后由 _executed_gold_delta 消费。
        self._last_levelup_spent: int | None = None
        # 槽位中心(screen_info 静态,构造时读一次;F3 参数校验 + 拖拽坐标共用)
        self._bench_pts: list[Point] = row_area_centers(ctx, '备战栏')
        self._front_pts: list[Point] = row_area_centers(ctx, '前排')
        self._back_pts: list[Point] = row_area_centers(ctx, '后排')

    # ===== F3 参数校验(非法 → 错误串;合法 → None)=====

    def validate(self, action: PrepAction) -> str | None:
        """校验动作合法域 + 参数(§5.0 F3)。返回错误描述;None=合法。

        两层:① 动作全集白名单(review M-4 —— 未知类型走参数非法路径拒绝,不进 execute
        的验证失败/fail 循环);② 静态可判参数(槽位越界/row 枚举)。动态前置(球是否存
        在/overlay 是否开)由 execute 的完成验证覆盖(验证失败路径,非参数非法路径)。
        """
        if not isinstance(action, PREP_ACTION_TYPES):
            return f'未知动作类型 {type(action).__name__}(不在动作全集,§4)'
        if isinstance(action, SellBench):
            if not (1 <= action.slot <= len(self._bench_pts)):
                return f'SellBench slot={action.slot} 越界(1-{len(self._bench_pts)})'
        elif isinstance(action, SellDeployed):
            if action.row not in ('front', 'back'):
                return f'SellDeployed row={action.row!r} 非法(front/back)'
            n = len(self._front_pts if action.row == 'front' else self._back_pts)
            if not (1 <= action.slot <= n):
                return f'SellDeployed slot={action.slot} 越界(1-{n})'
        elif isinstance(action, DeployMove):
            if not (1 <= action.from_slot <= len(self._bench_pts)):
                return f'DeployMove from_slot={action.from_slot} 越界(1-{len(self._bench_pts)})'
            if action.to_row not in ('front', 'back'):
                return f'DeployMove to_row={action.to_row!r} 非法(front/back)'
            n = len(self._front_pts if action.to_row == 'front' else self._back_pts)
            if not (1 <= action.to_slot <= n):
                return f'DeployMove to_slot={action.to_slot} 越界(1-{n})'
        elif isinstance(action, ClickSpheres):
            if action.max_k < 1:
                return f'ClickSpheres max_k={action.max_k} < 1'
        elif isinstance(action, OpenBox):
            if action.slot is not None and not (1 <= action.slot <= len(self._bench_pts)):
                return f'OpenBox slot={action.slot} 越界(1-{len(self._bench_pts)})'
        elif isinstance(action, OpenTome):
            if action.slot is not None and not (1 <= action.slot <= len(self._bench_pts)):
                return f'OpenTome slot={action.slot} 越界(1-{len(self._bench_pts)})'
        elif isinstance(action, PickBoxCard):
            if action.card_idx is not None and not (1 <= action.card_idx <= 4):
                return f'PickBoxCard card_idx={action.card_idx} 越界(1-4)'
        return None

    # ===== 执行入口(机械执行,无返回;执行前拒绝见 _execute_dispatch)=====

    def execute(self, action: PrepAction) -> None:
        """机械执行一个动作(无返回;T-223:发出即职责完成,落地判定归
        观察侧 reconcile)。

        ⚠️ W209j 刹车(ADR-0388,纵深防御第二层):运行中被停 → 拒绝
        执行任何动作(点击/拖拽/出战),抛 :class:`StopBrakeShortCircuit`
        停机短路(原回执 ``(False, '已停止')`` 通道随回执退役改异常;
        语义与触发判据不变,run 27 实证覆盖绕环路径)。调用方捕获后交回
        外循环,下轮 loop 顶见 STOP 退出。

        发出即登记(批3a:期望态推进门/闩/清键门由「回执门控」改「发出
        即登记 + 对账纠偏」;执行前输入契约拒绝 = 动作未发出,不登记)。
        """
        _rc = getattr(self._ctx, 'run_context', None)
        if _rc is not None and getattr(_rc, 'last_run_result', None) is not None:
            log.info('[cw][battle] 停机标志已设 → 拒绝执行 %s'
                     '(W209j 刹车,ADR-0388)', type(action).__name__)
            raise StopBrakeShortCircuit('已停止[W209j刹车]')
        # 执行点金差显影账(T-16)每动作复位:上动作余量禁跨动作残留。
        self._last_levelup_spent = None
        # 落地门前捕获备战席占用(tracked 账现读):S1 路径 (ii) 翻正判读
        # 需要 pre/post 两点,post 点必须在 dispatch 之后读(dispatch 内
        # 卖出/部署 handler 会同步销账)。
        _pre_bench = self._bench_tracked_count()
        # 卖出对象 dispatch 前快照(执行点金差供给;dispatch 内 tracked
        # 已同步移除,事后复查恒落空)。
        _pre_sell_bc = self._pre_sell_tracked_bc(action)
        detail, emitted = self._execute_dispatch(action)
        self.last_detail = detail
        gold_delta = self._executed_gold_delta(action, emitted, _pre_sell_bc)
        self.last_gold_delta = gold_delta
        if emitted and gold_delta:
            # 执行缝金账直推(T-16 备战帧金动作入账;写通道单一源 =
            # cw_exec_state._advance_gold 容器金账,logic_action 渠道,
            # 观察赢覆盖修正不变)。备战帧 LevelUp 花金/卖出回金自此
            # 入状态账,不再只存在于遥测文本(根因 = 执行缝三套账只辖
            # 商店单元,定谳 = 2026-09-06 迭代 reviews/T-234-落地审.md)。
            _m_gd = self._ctx.cw_match
            _sess_gd = _m_gd.session if _m_gd is not None else None
            if _sess_gd is not None:
                _advance_gold(_sess_gd, int(gold_delta))
        _gold_extra = ({'gold_delta': int(gold_delta)}
                       if gold_delta not in (None, 0) else None)
        self._note_action_receipt(action, emitted, detail, extra=_gold_extra)
        self._note_action_journal(action, emitted, _gold_extra)
        if isinstance(action, StartBattle):
            # 批4 挂账:StartBattle 发射位内部事实(A6 判效面,批4 随
            # J2/J3/J4 消费端同退役)。真执行链 = _execute_dispatch 发射位
            # 内部 ok(找不到按钮/未落地 = False);执行缝(假环境)不经
            # 真分派 = applied 真值(F11 双轨申报)。同步写执行态(消费端
            # = cw_loop 备战环出口 0j 预算复位判定 F3/T-174,读后即清)。
            self.last_launch_ok = emitted
            _m_sb = getattr(self._ctx, 'cw_match', None)
            _sess_sb = getattr(_m_sb, 'session', None) if _m_sb is not None else None
            if _sess_sb is not None:
                exec_state_of(_sess_sb).last_prep_battle_launch_ok = emitted
        if emitted and isinstance(action, RunEquip):
            # M7 备战期装备闩置位(批3a 重推 = 发出即置 + 观察纠偏,申报
            # 择一;原「组合 op 成功返回才置」消费 ok 回执,随回执退役改
            # 发出即置——单动作备战环下发射列表中 RunEquip 之前的可续动作
            # 先执行即终结本环,发射位(策略侧)置闩会闩烧而装备未穿的
            # 论证不变(mandate.mark_equip_pass_executed docstring),本写点
            # = 执行位派发事实。组合 op 执行后失败的面由装备期望态对账族
            # 在下一入口暴露(纠偏/缺陷台账);执行前输入契约拒绝(守卫/
            # 计划产出失败)= 未发出,不置闩,下帧照常重发。唯一写点 =
            # mandate.mark_equip_pass_executed。
            try:
                from sr_od.application.currency_war.kernel.cw_game_state import (
                    board_state_of,
                )
                from sr_od.application.currency_war.strategies.impl.mandate_v1.mandate import (
                    mark_equip_pass_executed,
                )
                _m = self._ctx.cw_match
                _sess = _m.session if _m is not None else None
                if _sess is not None:
                    # 换源 T-146:phase 键 = 容器单例(mandate mark_* 族
                    # 已切 GameState 形态,键值同帧同源)
                    mark_equip_pass_executed(
                        _sess, board_state_of(_sess))
            except Exception as e:  # noqa: BLE001  记账失败不阻塞执行
                log.warning('[cw][equip-latch] 置位失败(不阻塞): %s', e)
        if emitted and isinstance(action, RunTools):
            # M7.5 工具期闩置位(工具执行批 ADR-0532;批3a 重推同装备闩:
            # 发出即置 + 观察纠偏)。唯一写点 = mandate.mark_tools_pass_executed。
            try:
                from sr_od.application.currency_war.kernel.cw_game_state import (
                    board_state_of,
                )
                from sr_od.application.currency_war.strategies.impl.mandate_v1.mandate import (
                    mark_tools_pass_executed,
                )
                _m = self._ctx.cw_match
                _sess = _m.session if _m is not None else None
                if _sess is not None:
                    mark_tools_pass_executed(
                        _sess, board_state_of(_sess))
            except Exception as e:  # noqa: BLE001  记账失败不阻塞执行
                log.warning('[cw][tools-latch] 置位失败(不阻塞): %s', e)
        if emitted:
            # T-159 迁移 D:S1 清键门(唯一写点 = mandate.mark_s1_route_
            # check,三路径封闭枚举)。批3a 跨批对齐写死:``landed`` 供给
            # 改观察侧 reconcile 落地事实(接口本批定、批5 E1 落地供给),
            # 过渡期恒传 False = fail-closed(宁「该清不清」不「乱清」,
            # 后者可无限重复——T-167 交替活锁;「该清不清」侧 wanted 滞留
            # 一拍自愈,非正确性损害,mandate docstring 在案)。RunDeploy
            # 的 (i)-deploy_launch 路径过渡期不清,防线语义(no-op 不清)
            # 完整存活。发射位只读不写的同型纪律在此不适用——本门消费
            # 「已落地」事实,发射侧天然无此事实(猎点 8)。OpenShop 分支
            # 不经本执行器(cw_screen_prep 流程层编排),开店落地不触清键
            # 面,与其置位语义(商店决策访问位)自洽。
            try:
                from sr_od.application.currency_war.kernel.cw_game_state import (
                    board_state_of,
                )
                from sr_od.application.currency_war.strategies.impl.mandate_v1.mandate import (
                    mark_s1_route_check,
                )
                _m = self._ctx.cw_match
                _sess = _m.session if _m is not None else None
                if _sess is not None:
                    mark_s1_route_check(
                        _sess, board_state_of(_sess), action,
                        pre_bench_count=_pre_bench,
                        post_bench_count=self._bench_tracked_count(),
                        landed=False)
            except Exception as e:  # noqa: BLE001  记账失败不阻塞执行
                log.warning('[cw][s1-route] 清键门失败(不阻塞): %s', e)
            # 逻辑效果推进(两态制 ADR-0651:op 可推算效果直接写 session
            # 字段,两执行面同源接线)——本执行器是两执行面的共同底层,
            # 推进挂本入口 = 两面一次覆盖、零双写;推进失败不阻塞执行
            #(观测面,best-effort)。
            try:
                from sr_od.application.currency_war.kernel.cw_exec_state import (
                    apply_op_effect,
                )
                match = self._ctx.cw_match
                session = match.session if match is not None else None
                if session is not None:
                    apply_op_effect(session, action, detail=detail,
                                    produced_by=type(self).__name__)
            except Exception as e:  # noqa: BLE001  推进失败不阻塞执行
                log.warning('[cw][expect] apply_op_effect 失败(不阻塞): %s', e)
        log.info('[cw][exec] %s → %s', type(action).__name__,
                 detail or '(无摘要)')

    def _note_action_receipt(self, action: PrepAction, emitted: bool,
                             detail: str,
                             extra: dict | None = None) -> None:
        """动作执行回执 → GameState receipts 域(R2 §3.1.1-4/§3.2.5;
        渠道② logic_action,唯一写点 = kernel note_action_receipt)。

        - **发出即簿记,不是验证**(M1③):applied = 分派面「是否发出」
          事实透传(执行前输入契约拒绝 = 未发出,回执 reason 带机械摘要);
          本写点零成败判定——不读屏、不做落地推断,「拖3次源槽未变」类
          机械事实随 detail 在账,落地判定归观察侧 reconcile;
        - 每动作 op 恰一条 logic_action 行(动作全集逐 op 覆盖;W209j 停机
          短路在本口之前抛出 = 执行被拒不产行——停机非动作);
        - ``extra`` = 执行面结构化字段透传(§3.2.1 质量词表执行面;T-16 起
          含金动作的 ``gold_delta`` 执行点金差,见 _executed_gold_delta);
        - journal 常开(R5 W1 影子闸折叠,ADR-0634)回执写入无条件;无局
          (session 缺)跳过;best-effort 不阻塞动作链。
        """
        try:
            from sr_od.application.currency_war.kernel.cw_game_state import (
                board_state_from_ctx,
                note_action_receipt,
            )
            bs = board_state_from_ctx(self._ctx)
            if bs is None:
                return
            note_action_receipt(
                bs, op=type(action).__name__, applied=bool(emitted),
                reason='' if emitted else detail, detail=detail,
                screen=SCREEN_NAME, actor=type(self).__name__, extra=extra)
        except Exception as e:  # noqa: BLE001  回执失败不阻塞执行
            log.warning('[cw][receipt] 动作回执写入失败(不阻塞): %s', e)

    def _note_action_journal(self, action: PrepAction, emitted: bool,
                             extra: dict | None) -> None:
        """备战动作 journal 行(op_journal.jsonl kind='action';T-113/
        ADR-0579 薄流的备战域扩围,T-16 执行缝账务包络):执行缝三套账的
        journal 回执腿——备战帧金动作自此逐行在账(定谳缺口 = T-234 复盘
        「备战帧 5 击零 journal 行」),op 分键「货币战争-备战动作」与商店
        「货币战争-买牌」域分键,行携 ``gold_delta`` 执行点金差。

        - seq 恒 0 = 备战域无段序账(行序即时序;商店 seq 语义不适用);
          post_frame 恒 None = 行不带期望态 delta(T-163 起两域同口径);
        - 仅发出动作产行(与商店域「未执行动作零行」同语义,调用点保证);
        - 局外(run_id 空)零行;journal best-effort,失败不阻塞动作链。
        """
        if not emitted:
            return
        try:
            from types import SimpleNamespace

            from sr_od.application.currency_war.kernel.cw_game_state import (
                board_state_of,
                plane_of,
                round_num_of,
            )
            from sr_od.application.currency_war.telemetry.op_journal import (
                record_action_journal,
            )
            match = self._ctx.cw_match
            session = match.session if match is not None else None
            if session is None:
                return
            _bs = board_state_of(session)
            _pre = SimpleNamespace(plane=int(plane_of(_bs) or 0),
                                   round_num=int(round_num_of(_bs) or 0))
            record_action_journal(
                match, action, 0, bool(emitted), _pre, None,
                op_name='货币战争-备战动作', extra=extra)
        except Exception as e:   # noqa: BLE001  journal best-effort
            log.warning('[cw][journal] 备战动作行写入失败(不阻塞): %s', e)

    def _pre_sell_tracked_bc(self, action: PrepAction) -> BenchChar | None:
        """卖出对象 dispatch 前 tracked 快照(T-16 执行点金差供给;卖出外
        动作 = None)。

        [槽位定义] SellBench.slot = 备战栏物理槽位 1-9(1 基,tracked 表
        slot 字段同系直接对位);SellDeployed (row, slot) = 物理排槽位
        1 基(front 1-4 / back 1-N),下标换算 = 前排 slot-1 / 后排
        4+slot-1(ADR-0392 定长 10 槽表,pad 后取)。取值时机 = execute()
        内 dispatch **前** tracked 账现读(卖出 handler 在 dispatch 内
        同步销账,dispatch 后按 tracked 复查恒落空——apply_op_effect
        卖入会话推进在现役链路不可达的同根);消费 = dispatch 后
        _executed_gold_delta 一次读用,不跨动作存活。tracked 不可读
        (无局/形状异常)= None(金差诚实缺失,观察覆盖兜底)。
        """
        if not isinstance(action, (SellBench, SellDeployed)):
            return None
        try:
            match = self._ctx.cw_match
            session = match.session if match is not None else None
            if session is None:
                return None
            es = exec_state_of(session)
            if isinstance(action, SellBench):
                return next((b for b in (es.tracked_bench_chars or [])
                             if b is not None and b.slot == action.slot), None)
            from sr_od.application.currency_war.kernel.cw_exec_state import (
                DEPLOYED_FRONT_CAPACITY,
                pad_deployed,
            )
            tracked = pad_deployed(list(es.tracked_deployed or []))
            idx = (action.slot - 1 if action.row == 'front'
                   else DEPLOYED_FRONT_CAPACITY + action.slot - 1)
            return tracked[idx] if 0 <= idx < len(tracked) else None
        except Exception:   # noqa: BLE001  观测容缺,不阻塞执行链
            return None

    def _executed_gold_delta(self, action: PrepAction, emitted: bool,
                             pre_sell_bc: BenchChar | None) -> int | None:
        """执行点金差显影(备战执行缝账务包络,T-16):gold 域备战动作在
        机械半边发出时点的金变化量。

        公式单一源与边界:
        - ``LevelUp`` = −实击花金(机械半边 ``_level_up`` 逐击累计,单击价
          单一源 = kernel ``xp_click_cost``;与假环境 fixtures _apply_
          levelup_clicks/_prep_gold_channel 同式同源);
        - ``SellBench``/``SellDeployed`` = +sell_refund(星×招募费;对象 =
          dispatch 前快照,费单一源 = kernel ``bench_char_cost``——与容器
          投影写口 apply_prep_action_logic 同式;身份不可辨 = None 诚实
          缺失,不做保守估值假账,观察覆盖兜底);
        - ``ClickSpheres`` = None(球金通道随机,执行点不可推算——声明
          盲区,观察覆盖兜底,禁拍值);
        - 其余动作 = 0(发出零金动);未发出 = None(无金动无账)。
        ``None`` 与 0 的消费语义:仅非 None 非 0 进回执 extra 金差键与
        容器金账直推;None = 该动作本拍金账留观察覆盖。
        """
        if not emitted:
            return None
        if isinstance(action, LevelUp):
            spent = getattr(self, '_last_levelup_spent', None)
            return None if spent is None else -int(spent)
        if isinstance(action, (SellBench, SellDeployed)):
            if pre_sell_bc is None:
                return None
            if not str(getattr(pre_sell_bc, 'char_id', '') or ''):
                return None   # 身份不可辨 → 回金不可算(诚实缺失)
            from sr_od.application.currency_war.kernel.cw_economy import (
                bench_char_cost,
                sell_refund,
            )
            refund = sell_refund(int(getattr(pre_sell_bc, 'star', 1) or 1),
                                 bench_char_cost(pre_sell_bc))
            return int(refund)
        if isinstance(action, ClickSpheres):
            return None
        return 0

    def _execute_dispatch(self, action: PrepAction) -> tuple[str, bool]:
        """动作分派(原 execute 主体;期望态钩子/闩在其上层 execute)。

        返回 ``(机械执行摘要, 是否实际发出)``。``emitted`` = **发出事实**
        (非落地判定、非成败回执):False 只用于「执行前输入契约拒绝/
        环境无对象」(球/箱/按钮等目标不在,M6 边界面——动作没发出,期望
        态/闩不登记);True = 点击/拖拽/组合 op 已发出。原 ``(ok, detail,
        landed)`` 三元组随 T-223 退役(成败与落地均不再是执行器输出;
        RunDeploy 落地结构化判定 F1b 迁观察侧对账,S1 门过渡期 landed=
        False 见 execute)。
        """
        if isinstance(action, RunDeploy):
            # 画面检查属转移验证用途(cw_op_deploy 内,非路由闸门);
            # STATUS 具名常量经 detail 显影透传(观察侧对账供给面)。
            return self._run_composite(
                '部署', 'sr_od.application.currency_war.operations.cw_op.cw_op_deploy.CwOpDeploy')
        if isinstance(action, RunEquip):
            # 计划随指令下发(ADR-0601 §3-C1,2026-09-09):装备走专用
            # 派发 _run_equip——分发段产出穿戴计划(_build_equip_wear_plan)
            # 随 op 构造下发,空计划具名 NOOP(闩照置);通用 _run_composite
            # 路径 op_cls(self._ctx).execute() 无法传构造参,不承接装备。
            return self._run_equip()
        if isinstance(action, RunTools):
            return self._run_composite('工具', 'sr_od.application.currency_war.operations.cw_op.cw_op_tools.CwOpTools',
                                       guard_screen='货币战争-备战')
        if isinstance(action, StartBattle):
            # A6 出战链(批4 拆):内部 ok(找不到按钮/未落地 = False)经
            # 发出位返回;last_launch_ok/执行态写点在 wrapper 半部(execute,
            # 执行缝替换分派时仍成立)。
            ok, detail = self._start_battle()
            return detail, ok
        if isinstance(action, (DeferSpheres, BailToOuter)):   # 本模块定义,无需导入
            return '控制流动作不经 execute(框架信号,§4.2b;环应在控制流分支拦下)', False
        return self._dispatch_direct(action)

    def _dispatch_direct(self, action: PrepAction) -> tuple[str, bool]:
        """直执行动作分派(非组合动作)。返回 (机械执行摘要, 是否实际发出)。"""
        if isinstance(action, ClickSpheres):
            return self._click_spheres(action)
        if isinstance(action, OpenBox):
            return self._open_box(action)
        if isinstance(action, OpenTome):
            return self._open_tome(action)
        if isinstance(action, PickBoxCard):
            _clicked, msg = self._pick_box_card(action)
            return msg, _clicked
        if isinstance(action, SellBench):
            return self._sell_bench(action)
        if isinstance(action, SellDeployed):
            return self._sell_deployed(action)
        if isinstance(action, DeployMove):
            return self._deploy_move(action)
        if isinstance(action, LevelUp):
            return self._level_up()
        if isinstance(action, EnsureShopOpen):
            return self._ensure_shop(True)
        if isinstance(action, EnsureShopClosed):
            return self._ensure_shop(False)
        return f'未知动作类型 {type(action).__name__}', False

    # ===== 奖励域 =====

    def _click_spheres(self, action: ClickSpheres) -> tuple[str, bool]:
        """批式点球(大球优先):一次全点 → 等满动画(机械执行半)。

        2026-09-02 用户指导(screen_flow_timing.md #16):奖励球飞行动画
        最长 ~2s(去向 = 备战/商店/装备栏),原逐球「点击 + 1.2s 验证」×N
        慢(且实证日志有同 step 重复发球)。权衡(用户裁定):席满时部分球
        可能没点开——由后续 heavy 观察自然回补(球仍在 → 下轮再派)。
        A2 拆除(用户裁定 2026-09-10):点后「重读验球消失」判效半删除,
        球未消由下一帧观察回补;幻球检出+会话黑名单随 M5 裁定整体删除
        (幻球 = 观察 bug,观察侧质量治理另立不入本线——读侧过滤函数与
        其测试面归拖拽失败降级批五文件面)。
        """
        budget = min(action.max_k, PrepActionExecutor.SPHERE_MAX_CLICKS)
        screen = self._op.screenshot()
        spheres = read_reward_spheres(self._ctx, screen)
        if not spheres:
            return '无球(观察-执行竞态,无事可做)', False   # LOW-2:环境无对象
        targets = sorted(spheres, key=lambda t: t[2], reverse=True)[:budget]
        clicked = 0
        for _color, center, _r in targets:
            self._ctx.controller.mouse_move(center)   # bug#1 缓解
            self._ctx.controller.click(center)
            clicked += 1
            self._op.park_cursor(after_wait=0.1)
        # 用户口径:飞行动画最长 ~2s → 等满(固定等待归产生动画的操作)
        time.sleep(2.0)
        detail = (f'点球 {clicked}/{budget}(动画等待 2s;'
                  f'球未消由下一帧观察回补)')
        if read_supply_boxes(self._ctx, screen):
            detail += ' 掉箱→下步 OpenBox 统筹'
        log.info(f'[cw][sphere] {detail}')
        return detail, True

    def _bench_tracked_count(self) -> int:
        """备战席占用数(tracked 账现读;T-159 路径 (ii) 席翻正判读输入)。

        tracked 账由本执行器卖出/部署 handler 同步销账,pre/post 两点
        夹一次 dispatch 即「本帧落地是否使席 free 由 0 翻正」的观测读数
        (方案 §3.3 (ii);账缺页形态由消费臂门 1 下帧现读自愈)。会话
        缺席/读失败 = -1(调用侧按「不可判」处理,不产生翻正)。
        """
        try:
            match = self._ctx.cw_match
            if match is None or match.session is None:
                return -1
            tracked = exec_state_of(match.session).tracked_bench_chars
            return sum(1 for bc in tracked if bc is not None)
        except Exception:   # noqa: BLE001  观测 best-effort
            return -1

    def _poll_transition(self, check, timeout_s: float,
                         interval_s: float = 0.3) -> bool:
        """[已退役 A3] 点击后过渡的事件驱动轮询判效原语。

        用户裁定 2026-09-10(动作 op 只管机械执行禁止验证):轮询读屏判
        「点击是否生效」= 判效,拆除;等待半改固定动画等待
        (``_OVERLAY_ANIM_WAIT_S``,等待归产生动画的操作),弹窗就位与否
        交下一帧观察。方法体保留墓碑占位防同名复活,零调用。
        """
        raise AssertionError(
            '_poll_transition 已随验证拆除退役(A3,用户裁定 2026-09-10;'
            '等待归 _OVERLAY_ANIM_WAIT_S 固定等待,判效交下一帧观察)')

    def _open_box(self, action: OpenBox) -> tuple[str, bool]:
        """开箱:找箱槽 → 点「开启」→ 固定动画等待(纯机械执行,ADR-0601)。

        选卡动作不在本执行链(ADR-0601:动作 op 机械执行,决策归决策面;
        原内联选卡 = 「决策与点卡同执行链闭环」违例,随动作 op 规范判读
        拆除):点完开启本动作即结束——武装箱选择 overlay 在场由观察侧
        每步现读(``PrepObservation.box_overlay_open``),策略器 prep 实体
        面臂(mandate_v1 entry「箱对话框在场 ⇒ PickBoxCard」,臂序先于
        boxes 重开臂)在下一决策帧提选卡动作,经 ``_dispatch_direct`` →
        :meth:`_pick_box_card` 执行(选卡打分单一源 = 策略
        ``decide_box_card``;与 ``_open_tome``「选卡交决策面」同构)。
        历史注记:同动作内联选卡(commit 698631b19)的动机 = 当时跨帧
        闭环链(观察臂)未接住 overlay;承接面失真要治在观察/建档面,
        不在执行链内联第二决策点。
        A3 拆除:「轮询验 overlay 弹出」判效半删除,改固定动画等待
        (等待归产生动画的操作);弹窗就位与否交下一帧观察。
        """
        screen = self._op.screenshot()
        boxes = read_supply_boxes(self._ctx, screen)
        if not boxes:
            return '无补给箱', False
        picked = boxes[0]
        if action.slot is not None:
            matched = next((b for b in boxes if b[0] == action.slot), None)
            if matched is None:
                return f'槽{action.slot} 无补给箱(实读 {boxes})', False
            picked = matched
        slot, center = picked
        open_point = Point(center.x, center.y + PrepActionExecutor.BOX_OPEN_DY)
        self._ctx.controller.mouse_move(open_point)   # bug#1 缓解
        self._ctx.controller.click(open_point)
        # 固定动画等待(原轮询判效半拆除,A3;值取原轮询上界)
        time.sleep(_OVERLAY_ANIM_WAIT_S)
        log.info(f'[cw][box] 开箱槽{slot} → 点开启已发(选卡交决策面 PickBoxCard 臂)')
        return f'开箱槽{slot}', True

    def _open_tome(self, action: OpenTome) -> tuple[str, bool]:
        """开秘密典籍:点槽两次(选中→开启)→ 固定动画等待。

        点两次间隔 ~1s(第一次选中边框高亮,第二次弹窗);弹窗后 loop 0i
        接管选卡(本动作不选 —— 选卡是策略决策,板上阵营匹配在 0i handler)。
        A3 拆除:「轮询验星徽四选一弹出」判效半删除,改固定等待;弹窗就位
        与否交下一帧观察(0i 分发重判)。
        """
        from sr_od.application.currency_war.obs.cw_identity_obs import read_tomes
        screen = self._op.screenshot()
        tomes = read_tomes(self._ctx, screen)
        if not tomes:
            return '无秘密典籍', False
        picked = tomes[0]
        if action.slot is not None:
            matched = next((t for t in tomes if t[0] == action.slot), None)
            if matched is None:
                return f'槽{action.slot} 无典籍(实读 {tomes})', False
            picked = matched
        slot, center = picked
        self._ctx.controller.mouse_move(center)   # bug#1 缓解
        self._ctx.controller.click(center)        # 第一次:选中
        time.sleep(1.0)
        self._ctx.controller.click(center)        # 第二次:开启
        # 固定动画等待(原轮询判效半拆除,A3)
        time.sleep(_OVERLAY_ANIM_WAIT_S)
        log.info(f'[cw][tome] 开典籍槽{slot} → 点两次已发(选卡交 loop 0i)')
        return f'开典籍槽{slot}', True

    def _pick_box_card(self, action: PickBoxCard) -> tuple[bool, str]:
        """选卡:OCR 卡名行 → (card_idx 指定 | 执行器默认:key_equips 命中 → 材料通用性 → 第1张)→ 点卡 + 固定等待。

        返回 ``(选卡点击是否已发出, 摘要)``——点击事实(期望态登记门控),
        非成败回执:overlay 关没关交下一帧观察(A3 判效半拆除,用户裁定
        2026-09-10)。入口锚检查 = 选卡点击的前置读(需 overlay 在场才有
        卡名可读,机械目标获取面)。"""
        overlay = self._op.screenshot()
        if not self._op.round_by_find_area(overlay, PrepActionExecutor.BOX_SCREEN, '标识-请选择').is_success:
            return False, '武装箱 overlay 未开(先 OpenBox)'
        rect = _area_rect(self._ctx, '区域-卡名行', PrepActionExecutor.BOX_SCREEN)
        names: list[tuple[str, int]] = []
        if rect is not None:
            for r in _ocr(self._ctx, overlay, rect):
                if 2 <= len(r.data) <= 8:
                    names.append((r.data, r.center.x))
        names.sort(key=lambda t: t[1])
        if not names:
            # 简易武装箱变体兜底:卡名行 OCR 不可得(变体字型/布局)→
            # 点首张装备卡(点卡选中即确认)。
            _fb = _area_rect(self._ctx, '装备卡-1',
                             PrepActionExecutor.BOX_SCREEN)
            if _fb is None:
                return False, 'OCR 未读到卡名且无装备卡-1 兜底区'
            chosen, choose_x = '装备卡-1(兜底)', (_fb.x1 + _fb.x2) // 2
        elif action.card_idx is not None:
            if not (1 <= action.card_idx <= len(names)):
                return False, f'card_idx={action.card_idx} 超实读卡数 {len(names)}'
            chosen, choose_x = names[action.card_idx - 1]
        else:
            chosen, choose_x = self._default_box_card(names)
        card_point = Point(choose_x, PrepActionExecutor.CARD_Y)
        self._ctx.controller.mouse_move(card_point)   # bug#1 缓解
        self._ctx.controller.click(card_point)        # 点卡选中即确认(实测单步)
        # 固定动画等待(原轮询判效半拆除,A3)
        time.sleep(_OVERLAY_ANIM_WAIT_S)
        log.info(f'[cw][box] 选卡 {chosen} → 点击已发')
        return True, f'选卡 {chosen}'

    def _default_box_card(self, names: list[tuple[str, int]]) -> tuple[str, int]:
        """执行器默认选卡:决策单一源 = 共享机器 ``pick_equipment``
        (armory-box-value landing 3.2;局内经策略模块 ``decide_box_card``
        薄壳,局外直接机器空键 = 纯通用输出先验排序)。

        分层纪律(T-20 谓词单一源判例同款):打分只住机器,本执行器
        **禁第二打分实现**——``decide_box_card`` 异常留证(完整栈)后显式
        上抛(与 ``cw_op_buy_cards.run_buy_waves`` 决策异常同款;本模块
        docstring 失败路径「执行异常 → 异常上抛,外层 op retry 接管」
        同约),返回越界索引同 fail-closed 上抛;两者都禁无声回落内联打分
        (策略 bug 永久遮蔽,2026-09-12 动作 op 规范判读应修②)。
        局外回落行为变化(armory-box-value §2.6 行 10):材料通用性梯度
        (出处文档已删,注册表无据)→ 通用输出先验;行为锁重锚 =
        test_cw_screens_ops 回落行为锁(重锚后 = test_pick_card_fallback_by_output_prior)。
        """
        match = self._ctx.cw_match
        if match is not None:
            try:
                # 决策输入 = session 容器单例(W6 波 4 取帧点改道容器直读,
                # 与全 pick 族同款;decide_box_card 契约面已切 GameState)。
                # 禁回落 last_state 直读——被删的 cw_screen_supply.
                # pick_box_card 原本同款直读,迁移批已切,直读 = 观察流旁路。
                from sr_od.application.currency_war.kernel.cw_game_state import (
                    board_state_of,
                )
                idx = match.strategy.decide_box_card(
                    [n for n, _ in names], board_state_of(match.session),
                    match.session, getattr(match, 'config', None))
            except Exception:   # noqa: BLE001  留证后显式上抛,禁无声回落
                import traceback

                log.error('[cw!][box] decide_box_card 异常(留证后上抛):\n%s',
                          traceback.format_exc())
                raise
            if not (0 <= idx < len(names)):
                raise ValueError(
                    f'decide_box_card 返回越界索引 {idx}(实读卡数 '
                    f'{len(names)});策略契约违约 fail-closed,禁回落内联选卡')
            return names[idx]
        # 局外(无策略面):机器空键 = 纯 base 排序(与局内未锁态同构,
        # 打分单一源;原梯度回落随虚构表退役,行 10)
        from sr_od.application.currency_war.kernel.cw_equip_value import (
            pick_equipment,
        )
        return names[pick_equipment([n for n, _ in names])]

    # ===== 席位域 =====

    def _sell_bench(self, action: SellBench) -> tuple[str, bool]:
        """卖备战槽角色:drag 槽中心 → 出售区(``drag_bench_to_sell`` 单一源;
        机械执行,T-192 源槽像素验重试拆除)。返回 (摘要, 是否发出)。

        emitted = 动作已机械发出(拖拽原语零判效,落地事实归观察侧
        reconcile 对账)。"""
        drag_bench_to_sell(self._op, self._ctx, action.slot - 1)
        self._track_remove_bench(action.slot)
        # 用户口述口径(screen_flow_timing.md #21,2026-09-02):卖出金币
        # 动画很快,等 1s 足够——批尾观察前补这段,防读到金币动画帧。
        time.sleep(1.0)
        return (f'卖备战槽{action.slot} ✓', True)

    def _sell_deployed(self, action: SellDeployed) -> tuple[str, bool]:
        """卖上阵角色:drag 排槽中心 → 出售区(落点经 ``sell_point`` 单一源)。
        返回 (摘要, 是否发出)。emitted 语义 = 同 _sell_bench(机械发出)。"""
        pts = self._front_pts if action.row == 'front' else self._back_pts
        src = pts[action.slot - 1]
        self._drag(src, sell_point(self._ctx))
        self._track_remove_deployed(action.row, action.slot)
        time.sleep(1.0)   # 同上 #21 口径:卖出动画 1s
        return (f'卖{action.row}排{action.slot} ✓', True)

    def _deploy_move(self, action: DeployMove) -> tuple[str, bool]:
        """bench → 上阵单步拖拽(腾席链专用)。返回 (摘要, 是否发出)。"""
        pts = self._front_pts if action.to_row == 'front' else self._back_pts
        src = self._bench_pts[action.from_slot - 1]
        dst = pts[action.to_slot - 1]
        self._drag(src, dst)
        self._track_move_deployed(action.from_slot, action.to_row, action.to_slot)
        # 用户口述口径(screen_flow_timing.md #10,2026-09-02):拖动触发
        # 羁绊阶段变更时角色头顶徽章动画 ~2s——拖完立即返回会让批尾
        # heavy 观察打在徽章动画帧上(SIFT/对账读脏,「对账纠漂」日志
        # 噪声源之一)。按「都等 2s」简单方案落(批尾/中间的区分不做)。
        time.sleep(2.0)
        # 用户口述口径(#24,2026-09-02):羁绊达标触发的 overlay(盛会之星
        # 等)在徽章动画后再 ~2s 才弹出——固定等待覆盖不住。执行端等待后
        # 快查一次触发型 overlay 锚(模板毫秒级),命中 → detail 标注(拖拽
        # 本身已发出);批尾 heavy 的 event_overlay 检测将看到它并 bail 交
        # 外环 handler——防「decide 的下一步动作打在 overlay 上」。清单
        # 可扩(圣杯/银狼升星等实测出现时加锚)。
        _post = self._op.screenshot()
        if self._op.round_by_find_area(
                _post, '货币战争-盛会之星', '标识-盛会之星',
                crop_first=False).is_success:
            log.info('[cw][deploy] 拖后检出盛会之星 overlay(羁绊达标触发)')
            return ('部署已发,盛会之星 overlay 弹出(外环接管)', True)
        return (f'部署槽{action.from_slot}→{action.to_row}{action.to_slot} ✓',
                True)

    def _drag(self, src: Point, dst: Point) -> None:
        """统一拖拽原语(DragCwChar.drag_char:中心拖+hold0;机械执行,
        T-192 源槽像素验重试拆除)。

        r10 review#2:失焦守卫下沉到本原语(所有拖拽路径共享)——窗口后台化时
        拖拽输入静默丢(r9 实证同机制:截图正常/输入丢/连环「源槽未变」假失败),
        拖前验焦点,失焦先激活。StartBattle 的 click 守卫同款语义(在它自己的
        路径上,click 不走本原语)。
        """
        from sr_od.application.currency_war.operations.dev.drag_cw_char import (
            DragCwChar,
        )

        try:
            gw = self._ctx.controller.game_win
            if not gw.is_win_active:
                log.warning('[cw!][drag] 窗口失焦(拖拽输入将静默丢)→ 先激活')
                gw.active()
                time.sleep(0.3)
        except Exception:   # noqa: BLE001  焦点守卫 best-effort
            pass
        DragCwChar.drag_char(self._op, src, dst)

    def _track_remove_bench(self, slot: int) -> None:
        """卖出后备势跟踪同步(单一跟踪账 tracked_bench_chars)。"""
        match = self._ctx.cw_match
        if match is None or match.session is None:
            return
        # 形状双源防御(ADR-0316):tracked_bench_chars 可能是 pad 态(含 None)
        exec_state_of(match.session).tracked_bench_chars = [
            bc for bc in exec_state_of(match.session).tracked_bench_chars
            if bc is not None and bc.slot != slot]

    def _track_remove_deployed(self, row: str, slot: int) -> None:
        match = self._ctx.cw_match
        if match is None or match.session is None:
            return
        # ADR-0392:tracked_deployed 槽位表(置 None 不移位);(row, slot)
        # 物理 1-based → 槽位下标(front: slot-1 / back: 4+slot-1)
        from sr_od.application.currency_war.kernel.cw_exec_state import (
            DEPLOYED_FRONT_CAPACITY,
            pad_deployed,
        )
        tracked = pad_deployed(list(exec_state_of(match.session).tracked_deployed))
        idx = (slot - 1 if row == 'front'
               else DEPLOYED_FRONT_CAPACITY + slot - 1)
        if 0 <= idx < len(tracked) and tracked[idx] is not None \
                and tracked[idx].position_pref == row:
            tracked[idx] = None
        exec_state_of(match.session).tracked_deployed = tracked

    def _track_move_deployed(self, from_slot: int, to_row: str, to_slot: int) -> None:
        """上阵后备势跟踪同步:bench 条目 → deployed 条目(位置/槽位改写)。"""
        match = self._ctx.cw_match
        if match is None or match.session is None:
            return
        # 形状双源防御(ADR-0316):tracked_bench_chars 可能是 pad 态(含 None)
        moved = [bc for bc in exec_state_of(match.session).tracked_bench_chars
                 if bc is not None and bc.slot == from_slot]
        exec_state_of(match.session).tracked_bench_chars = [
            bc for bc in exec_state_of(match.session).tracked_bench_chars
            if bc is not None and bc.slot != from_slot]
        # ADR-0392:tracked_deployed 槽位表——deployed_place 单一源落槽;
        # to_slot 是执行器物理槽位真值,落槽后覆写信息位。
        from sr_od.application.currency_war.kernel.cw_exec_state import deployed_place
        for bc in moved:
            bc.position_pref = to_row
            deployed_place(exec_state_of(match.session).tracked_deployed, bc)
            bc.slot = to_slot

    # ===== 商店域 =====

    def _level_up(self) -> tuple[str, bool]:
        """买经验(循环点「购买经验」机械执行;gold 前置由策略保证)。

        A4 拆除(用户裁定 2026-09-10):逐击点后 OCR 验级判效半删除——
        点击按授权击数机械执行(金本位 = kernel ``clicks_to_next_level``
        推导击数;血本位 = 入口整级授权击数,血闸授权已是入口整级授权),
        级真值由下一帧观察 reconcile(``_reconcile_xp_expect`` 经验对账族
        承接);原过冲 fail-closed 防线改策略层授权口径(授权击数 = 上界,
        循环结构性不超击)。

        入口前检(M6 边界面,非判效):level 基线读不到拒绝盲点(击数无法
        推导);血闸(ADR-0578,血本位协议限定;金模式零改动)整级授权检
        (全量口径 ``⌈need/4⌉×血单价``,hp 不可信 fail-closed)。
        r15 review P1 金检查保留:每点前读金,gold < 单击价(kernel
        ``XP_CLICK_COST_FALLBACK``)即停(防排干买牌本金——执行前资源契约,
        非点击效果判断)。
        """
        match = self._ctx.cw_match
        session = match.session if match is not None else None
        screen = self._op.screenshot()
        before = _read_level_raw(self._ctx, screen)
        if before is None and session is not None and session.last_level_obs:
            before = session.last_level_obs   # OCR 漏读基线退单调守卫值(只作比较基,不写回)
        if before is None:
            return 'level 基线读不到(OCR 漏读),拒绝盲点', False
        from sr_od.application.currency_war.kernel.cw_discipline_rules import (
            hp_decision_trusted,
        )
        from sr_od.application.currency_war.kernel.cw_economy import (
            blood_xp_full_clicks,
            blood_xp_gate,
            clicks_to_next_level,
            xp_click_cost,
        )
        from sr_od.application.currency_war.kernel.cw_game_state import (
            board_state_of as _bs_of_auth,
        )
        from sr_od.application.currency_war.kernel.cw_hp_policy import (
            decision_hp as _decision_hp_auth,
        )
        from sr_od.application.currency_war.kernel.cw_investments import (
            blood_xp_mode,
        )
        _blood = None if session is None else blood_xp_mode(session)
        _hp: int | None = None
        _auth_clicks = 0
        if _blood is not None:
            _mode_name, _cost = _blood
            # 血闸 hp 消费经决策读口(prep 链容器化段 2 消点,kernel 判读
            # S5:旧 last_state 帧 raw hp 直读未经新鲜度门+桥视图可信位
            # 恒 observation 失真,与同闸 P21 面「同面同输入」申报不符;
            # 现改 decision_hp 门后值+容器来源位可信位,两面对同一购买
            # 动作输入同源——可信位单一源 = kernel cw_discipline_rules)。
            _bs_auth = _bs_of_auth(session)
            _hp = _decision_hp_auth(_bs_auth, session)
            _trusted = hp_decision_trusted(_bs_auth)
            # 批入口整级授权检(全量口径);拒 → 与「level 基线读不到」同返回路径
            if not blood_xp_gate(_hp, _trusted, before, _cost):
                return (f'血闸拒:hp={_hp} < 下一级血成本 '
                        f'{blood_xp_full_clicks(before) * _cost}'
                        f'(mode={_mode_name};[40]② 否则停,升级走买牌自然 XP)',
                        False)
            _auth_clicks = blood_xp_full_clicks(before)
        else:
            # 金本位授权击数 = kernel 击数推导(§6.6 单击价/击数单一源):
            # 优先容器现值(W6 波 4 接缝族切容器帧;xp 进度精确),缺席退
            # 权威表全量口径(blood_xp_full_clicks = ⌈need/4⌉ 同式,xp 结转
            # 忽略);满级(0 击)= 无购买对象,机械不发。
            from sr_od.application.currency_war.kernel.cw_game_state import (
                board_state_of as _bs_of_clicks,
            )
            from sr_od.application.currency_war.kernel.cw_game_state import (
                level_of as _level_of_clicks,
            )
            _st = _bs_of_clicks(session)
            _gold_clicks = clicks_to_next_level(_st)
            if _gold_clicks <= 0:
                lv_now = _level_of_clicks(_st)
                return f'已满级(level {lv_now}),无购买对象', False
            _auth_clicks = min(_gold_clicks, PrepActionExecutor.LEVEL_MAX_CLICKS)
        btn = area_center(self._ctx, '备战标识-购买经验') or Point(296, 860)
        _clicked = 0   # 实击数(机械回显真实停点;金地板可提前停)
        _spent = 0     # 实击花金累计(T-16 执行点金差;单价 = xp_click_cost 逐击现算)
        # 单击价容器读口(逐击现算:等级门折扣随升级跨档变化,禁循环外
        # 单次快照;无局 = 兜底价。单一源 = kernel xp_click_cost,与假
        # 环境执行缝同式)。
        _bs_price = None
        if session is not None:
            from sr_od.application.currency_war.kernel.cw_game_state import (
                board_state_of,
            )
            _bs_price = board_state_of(session)
        for k in range(_auth_clicks):
            if _blood is not None and _hp is not None:
                # 逐击支付能力地板:modeled_hp(= hp_trusted − 已击数×单价)≥ 单价才可点下一击
                if _hp - k * _cost < _cost:
                    log.info('[cw][levelup] 血模式 modeled hp %s 第%s击前不足单价 %s → 停点',
                             _hp - k * _cost, k + 1, _cost)
                    break
            # r15 review P1:循环内金检查——策略侧金前置滞后一环时
            # (如 P2 急救态 _saving_for_level 仍攒金但 plan 已发 LevelUp),gold 63→9
            # 一动作排干(M57 P2-1 实证)。每点前读金,gold < 单击价即停(防排干
            # 买牌本金);单击价单一源 = kernel XP_CLICK_COST_FALLBACK。
            gold_now = read_gold(self._ctx, self._op.screenshot())
            if gold_now is not None and gold_now < XP_CLICK_COST_FALLBACK:
                log.info('[cw][levelup] gold %s < 单击价 → 停点(保买牌本金)', gold_now)
                break
            _price = xp_click_cost(_bs_price) if _bs_price is not None \
                else XP_CLICK_COST_FALLBACK
            _clicked += 1
            _spent += _price
            self._ctx.controller.mouse_move(btn)   # bug#1 缓解(review M-5:循环内 screenshot 移光标后紧接 click)
            self._ctx.controller.click(btn)
            # 血购回执行挂点已随 exogenous 流写入端退役删除
            # (删除波 1);点击循环其余机械事实面不变。
            # 光标 parking(审计 P0,2026-08-16 = M38 level 毒化注入点):按钮距等级显示区 18px,
            # 点击后光标压住 Lv.N 区 → 下帧 OCR 读错(4 毒化 3 位面的链头)。park 后再继续。
            self._op.park_cursor(before_wait=0.3, after_wait=0.15)
        if _clicked <= 0:
            return f'授权击数 {_auth_clicks} 击未发出(金地板/血地板先行停点)', False
        # W612 挂点A(升级事件;发射时点登记,批3a:原「验级成功分支内」
        # 挂点随判效拆除改发出即登记;级真值由下一帧观察 reconcile,锚点
        # 吸收外生差):inventory 标记(level_up 外生事件行已随 exogenous
        # 流写入端退役删除——删除波 1)。观测 best-effort,零决策语义。
        try:
            if session is not None:
                session.effect_inventory.on_level_up()
        except Exception as e:   # noqa: BLE001  观测失败不阻塞对局
            log.warning('[cw][levelup] effect inventory 挂点失败(不阻塞): %s', e)
        self._last_levelup_spent = _spent   # 执行点金差供给(_executed_gold_delta 消费)
        detail = (f'买经验授权{_auth_clicks}击实击{_clicked}花金{_spent}'
                  f'(基线 level {before};级真值=下一帧观察 reconcile)')
        log.info(f'[cw][levelup] {detail}')
        return detail, True

    def _ensure_shop(self, want_open: bool) -> tuple[str, bool]:
        """开/关商店(点击 + 固定动画等待;开态判定交下一帧观察侧 0n 三锚)。

        入口幂等检查 = 执行前观察(已开/已关 = 无动作可发,M6 边界面,非
        判效)。A5 拆除(用户裁定 2026-09-10):点击 + 固定等待后「重读
        按钮-收起」判效半删除(原单次验证在动画窗可假阴性喂恢复机制噪声
        的 r312 论证随验证拆除一并退役)——开/关是否生效由下一帧观察
        (0n 三锚/备战双锚)自然判定。
        """
        screen = self._op.screenshot()
        is_open = self._op.round_by_find_area(screen, SHOP_SCREEN_NAME, '按钮-收起').is_success
        if want_open:
            if is_open:
                return '商店已开(无动作可发)', False
            # 手动开(用户口述 2026-09-02 场景②):干净备战画面点击商店打开。
            # 自动开店场景不经此处:结算后由 cw_loop 备战分支按
            # 「备战阶段」识别等面板就位(W971 §2.5/§2.6 场景①),两场景互不竞速。
            self._op.round_by_find_and_click_area(
                screen, SCREEN_NAME, '按钮-商店')
            # 光标 parking(审计 R3):点击点在动画后观察矩形正中(0px),park 防光标压读
            self._op.park_cursor(before_wait=0.5, after_wait=0.1)
            time.sleep(SHOP_OPEN_ANIM_S)
            return '开商店 点击已发(动画等待 1s;开态交下一帧观察)', True
        if not is_open:
            return '商店已关(无动作可发)', False
        self._op.round_by_find_and_click_area(
            screen, SHOP_SCREEN_NAME, '按钮-收起')
        self._op.park_cursor(before_wait=0.5, after_wait=0.1)   # 同 R3
        # 收起动画 ~1s(#15)自等;关态由下一帧观察判定。
        time.sleep(SHOP_CLOSE_ANIM_S)
        return '关商店 点击已发(动画等待 1s;关态交下一帧观察)', True

    # ===== 战斗域 =====

    def _start_battle(self) -> tuple[bool, str]:
        """出战发射:常规发射 → 未落地原样重发(长按下) → 仍败计连败停机留证。

        恢复语义(用户裁定 2026-08-30):禁用 active_window 激活——激活会抢占
        用户桌面焦点,自主推进运行期不可接受,无例外;重发=同通道原样重试。
        连续失败达限 → 停机留证(截图+flag+stop_running,与 bail ping-pong
        停机同款三要素),根因判定交人工:留证线索=输入投递机制状态
        (SendInput 落点 vs 真前台句柄)与游戏侧输入管线状态。
        """
        ok, detail = self._launch_attempt()
        if ok:
            self._launch_dead_reset()
            return True, detail
        log.warning('[cw!][battle] 出战未落地(%s) → 原样重发(长按下)', detail)
        # 重发段 press_time=0.15:人工解锁实证参数(2026-08-30 16:31 手动 click_game
        # 0.15 即生效)——输入管线半死态下短按下可能不被采样,重发放长按下加固。
        ok2, detail2 = self._launch_attempt(press_time=0.15)
        if ok2:
            self._launch_dead_reset()
            return True, f'{detail2}(重发)'
        self._op.save_screenshot()   # 诊断存证(同 battle_prep:bug#1 drag vs overlay 挡 vs 坐标偏)
        if '未落地' not in detail2:
            return False, f'出战失败(重发后): {detail2}'
        escalated = self._launch_dead_escalate()
        if escalated is not None:
            return False, escalated
        return False, f'出战 click 未落地(重发后仍在备战;首次: {detail})'

    def _launch_attempt(self, press_time: float = 0.1) -> tuple[bool, str]:
        """单次发射尝试:找按钮 → mouse_move+click+失焦守卫 → 轮询转移。

        press_time:按下时长(秒);默认 0.1(框架 click 默认),重发段用
        0.15(人工解锁实证参数,防输入管线半死态短按下不被采样)。
        成功判据 = 备战标识消失(或未达上限警告弹出后确认完成且标识消失);
        轮询耗尽仍备战 = 未落地 → (False, detail),由调用方决定重发/失败。

        子态(2026-08-17 M72 实锤建档):「免战牌」策略激活时出战按钮变「跳过(N/N)」(直跳战斗,
        免战 2 次)——查不到「出战」时查子态「按钮-跳过」,同语义点它(推进节点)。

        ⚠️ 正交态查找(子态建模四问③,skill feedback 案例库):免战与「商店开」**可叠加**(跳过
        按钮 + 牌区展开同帧)——叠加帧识别为 货币战争-备战-开商店(它盖基态 id_mark),
        按单一屏查「按钮-跳过」会落空。跳过/出战按钮在两屏同一位置 → fallback 查找
        **不锁死单一屏**(备战+开商店都查);按钮 area 单源归备战屏,不复制双源。
        """
        screen = self._op.screenshot()
        _btn_area = '按钮-出战'
        _btn_screens: list[str] = [SCREEN_NAME, '货币战争-备战-开商店']
        _btn_found = any(
            self._op.round_by_find_area(screen, _sc, '按钮-出战').is_success
            for _sc in _btn_screens)
        if not _btn_found:
            if any(self._op.round_by_find_area(screen, _sc, '按钮-跳过', crop_first=False).is_success
                   for _sc in _btn_screens):
                _btn_area = '按钮-跳过'   # 免战牌子态:跳过=本节点直进(免战次数-1)
                log.info('[cw][battle] 出战按钮为子态「跳过」(免战牌激活)→ 点跳过')
            else:
                return False, '找不到出战按钮'
        btn = area_center(self._ctx, _btn_area)
        if btn is None:
            # area 缺失 = 建档漂移,显式失败禁兜底坐标(坐标单一真相源)。
            # (False, 非「未落地」detail)→ _start_battle 重发后立即判败上交,
            # 不进连败停机环(area 缺失是确定性失败,重发无意义)。
            return False, f'area 缺失:{_btn_area}({SCREEN_NAME}),禁兜底坐标'
        self._ctx.controller.mouse_move(btn)   # bug#1 缓解(2026-08-06 r9 实打出战 click ×4 未落地)
        self._ctx.controller.click(btn, press_time=press_time)
        # r9 失焦守卫:click 后验窗口焦点,失焦 → game_win.active() 激活 + 重点一次
        # (live 实证 2026-08-18:窗口后台化时输入静默丢,截图正常 → 环僵尸 20min;
        # MCP click 激活后立即恢复。active() 是框架窗口原语,见 pc_game_window)。)
        try:
            time.sleep(0.4)
            if not self._ctx.controller.game_win.is_win_active:
                log.warning('[cw!][battle] 窗口失焦(输入静默丢)→ 激活 + 重试出战')
                self._ctx.controller.game_win.active()
                time.sleep(0.3)
                self._ctx.controller.mouse_move(btn)
                self._ctx.controller.click(btn, press_time=press_time)
        except Exception:   # noqa: BLE001  焦点守卫 best-effort(无窗口对象则跳过)
            pass
        for _ in range(6):   # 6 × 0.5s 轮询窗口(同 battle_prep D-70)
            time.sleep(0.5)
            scr = self._op.screenshot()
            if self._op.round_by_find_area(scr, '货币战争-未达上限警告', '标识-未达上限警告').is_success:
                # M16 死循环根因修复(ADR-0136):只点确认不勾「本局不再提示」→ 人口不足时**每次**出战
                # 都弹此窗;确认后若弹窗未消(点击落空/动画)轮询重进 → 外层判"仍在备战"=fail → 死循环 86min。
                # 对齐 CwScreenDeployNotFull 完整行为:勾选(幂等,已勾无害)→ 确认 → 下轮验消失。
                check = area_center(self._ctx, '勾选-本局不再提示',
                                    '货币战争-未达上限警告')
                if check is None:
                    return False, ('area 缺失:勾选-本局不再提示'
                                   '(货币战争-未达上限警告),禁兜底坐标')
                self._ctx.controller.mouse_move(check)
                self._ctx.controller.click(check)
                time.sleep(0.3)
                confirm = area_center(self._ctx, '按钮-确认',
                                      '货币战争-未达上限警告')
                if confirm is None:
                    return False, ('area 缺失:按钮-确认'
                                   '(货币战争-未达上限警告),禁兜底坐标')
                self._ctx.controller.mouse_move(confirm)   # bug#1 缓解(review M-5)
                self._ctx.controller.click(confirm)
                time.sleep(1.0)
                continue
            if not self._op.round_by_find_area(scr, SCREEN_NAME, '备战标识-购买经验').is_success:
                # P4R 弹窗污染守卫(1-1 事故):备战标识消失 ≠ 出战成功——
                # 「前台区域无角色」等确认弹窗同样盖掉标识(实锤:假成功 →
                # 交回外循环 → 「确认关闭→重部署」无限 round_wait 死循环)。
                # 出战被拒弹窗在场 = 失败,交上层「带验证的重部署 → 再出战」链。
                time.sleep(0.6)   # 弹窗渲染窗(标识消失帧可能早于弹窗)
                _post = self._op.screenshot()
                for _bscr, _banchor in PrepActionExecutor.POST_LAUNCH_BLOCKERS:
                    if self._op.round_by_find_area(_post, _bscr, _banchor).is_success:
                        return False, f'出战被拒:弹窗 {_banchor}(标识消失为弹窗污染,非转移)'
                log.info('[cw][battle] 出战成功 → 备战标识消失(无拦截弹窗)')
                if _btn_area == '按钮-跳过':
                    # 免战牌跳过递减挂点(迁移批次三,设计 §3.2.19 载体归一
                    # 另一半/§8.7 批次三件 5):正本 = effect_inventory
                    # .remaining_uses(§5.1),跳过**执行落地**(备战标识消失
                    # 验证通过)= 次数递减,归零移除。与登记挂点解耦:未登记
                    # (登记面缺位的局)→ consume_use 返 None 零动作,不炸
                    # 发射回执。best-effort 记录面(与升级挂点同纪律)。
                    try:
                        from sr_od.application.currency_war.kernel.cw_game_state import (
                            board_state_of,
                        )
                        from sr_od.application.currency_war.kernel.cw_investments import (
                            STRATEGY_EFFECTS,
                        )
                        _mz = getattr(self._ctx, 'cw_match', None)
                        _sz = getattr(_mz, 'session', None) if _mz is not None else None
                        _spec_z = STRATEGY_EFFECTS.get('免战牌')
                        if _sz is not None and _spec_z is not None:
                            _left = board_state_of(_sz).effects.consume_use(
                                _spec_z.id)
                            log.info(f'[cw][battle] 免战牌跳过落地 → '
                                     f'次数递减(余 {_left})')
                    except Exception as e:   # noqa: BLE001  记录面不阻塞
                        log.warning(f'[cw][battle] 免战牌递减记录失败(不阻塞): {e}')
                return True, '出战成功'
        return False, '出战 click 未落地(6×0.5s 轮询+失焦守卫后仍在备战)'

    def _launch_dead_reset(self) -> None:
        """发射成功/环内任何成功发射 → 清连败计数(输入通道已恢复的证据)。"""
        match = getattr(self._ctx, 'cw_match', None)
        session = getattr(match, 'session', None) if match is not None else None
        if session is not None and getattr(exec_state_of(session), 'launch_dead_streak', 0):
            exec_state_of(session).launch_dead_streak = 0

    def _launch_dead_escalate(self) -> str | None:
        """发射连败升级:未落地连发达限 → 停机留证(返回失败 detail);未达限返回 None。

        只对「未落地」型失败计数(识别类失败如找不到按钮不是输入通道问题);
        计数挂 session(跨环重入存活——环级计数随 Director 重建清零,挡不住
        round_fail → 外环重入的 2min/次僵尸循环,两局实证)。
        """
        match = getattr(self._ctx, 'cw_match', None)
        session = getattr(match, 'session', None) if match is not None else None
        if session is None:
            return None
        streak = getattr(exec_state_of(session), 'launch_dead_streak', 0) + 1
        exec_state_of(session).launch_dead_streak = streak
        if streak < PrepActionExecutor.LAUNCH_DEAD_LIMIT:
            log.warning('[cw!][battle] 出战未落地连败 %s/%s', streak,
                        PrepActionExecutor.LAUNCH_DEAD_LIMIT)
            return None
        # 停机留证三要素(截图 + 自描述 flag + stop_running;与 bail ping-pong 同款)。
        # 截图走显式通道不落 suppress(2026-09-02 夜间语料批局1实证:last 帧
        # 通道在停机时刻静默缺失,被 bare suppress 吞掉无日志线索)——失败
        # 必须 log.error 留痕,且 last 帧缺失时用独立现帧兜底(同 L0 安灯
        # _save_andon_frame 通道,不污染 op 循环帧缓存)。
        import contextlib
        stop_shot = ''
        try:
            stop_shot = self._op.save_screenshot(prefix='launch_dead')
        except Exception:
            log.error('[cw!][battle] launch_dead 取证截图失败(last 帧通道)', exc_info=True)
        if not stop_shot:
            try:
                _ts, _img = self._ctx.controller.screenshot(independent=True)
                if _img is not None:
                    from one_dragon.utils import debug_utils
                    stop_shot = debug_utils.save_debug_image(_img, prefix='launch_dead')
            except Exception:
                log.error('[cw!][battle] launch_dead 取证截图失败(独立现帧兜底通道)', exc_info=True)
        with contextlib.suppress(Exception):
            import time as _t

            # flag 路径锚项目根(与 defects.l0_andon_flag_path 同口径):相对路径
            # 会把 flag 落在进程 cwd 下——pytest(仓根 cwd)复现本钩子时会误写
            # 真 flag,值班者误判实机停线(2026-09-03 停机现场实证)。
            from one_dragon.utils.file_utils import get_project_root
            _flag = (get_project_root()
                     / '.debug/temp/currency_war/launch_dead_hook.flag')
            _flag.parent.mkdir(parents=True, exist_ok=True)
            _flag.write_text(
                f'[HOOK-STOP] 出战发射连败停机(常驻安全网,无激活自愈——用户裁定)\n'
                f'触发:出战 click 未落地 ×{streak}(原样重发仍败)——根因未定,\n'
                f'头号候选=真前台被其他进程抢占(SendInput 落点非游戏)/游戏侧输入管线挂起。\n'
                f'取证:1. 对比 GetForegroundWindow 句柄与游戏句柄(谁在真前台);\n'
                f'2. 手动点击游戏画面确认输入是否恢复;3. 看 .debug/images/launch_dead_*;\n'
                f'4. 处理完删本 flag 重启对局。\n'
                f'ts={_t.strftime("%m-%d %H:%M:%S")}\n', encoding='utf-8')
        rc = getattr(self._ctx, 'run_context', None)
        if rc is not None:
            with contextlib.suppress(Exception):
                rc.stop_running(reason='hook:cw_launch_dead')
        return f'出战 click 未落地×{streak} → 停机留证(hook:cw_launch_dead)'

    # ===== 组合动作(P1 过渡;旧 op 内部一行不动)=====

    def _guard_screen_mismatch(self, guard_screen: str) -> str | None:
        """派发前置预期屏检查(T-163 D5 判断上提的共用实现)。

        返回 None = 干净可派;返回当前画面名 = 不干净、不派、环重观察
        (断批重规划)。``_run_composite``(部署/工具)与 ``_run_equip``
        (装备计划派发)共用——守卫语义单一源,防两派发位漂移。
        """
        current = self._op.check_and_update_current_screen(
            self._op.screenshot(), screen_name_list=[guard_screen])
        return None if current == guard_screen else current

    def _run_equip(self) -> tuple[str, bool]:
        """RunEquip 专用派发:计划产出 → 空计划具名 NOOP / 计划随 op 下发。

        为什么不走 _run_composite:通用路径 ``op_cls(self._ctx).execute()``
        无法传构造参——穿戴计划在分发段产出(``_build_equip_wear_plan``,
        ADR-0601 §3-C1 计划产出位)后随 op 构造下发(CwOpEquipAll
        ``__init__(ctx, plan)`` 必填),「计划」概念不泄漏进部署/工具分派。

        空计划 = 合法稳态具名 NOOP(发射契约形态):返回
        ``(f'装备 计划空: {具名原因}', True)``——发出事实 = True,execute
        的 ``mark_equip_pass_executed`` 唯一写点照置(装备穿戴放行判定活锁
        三条件闭环不变;批3a:原 ok=True 语义同值为「发出事实」)。

        资源前置缺失走未发出通道 (detail, False):闩不置,下帧重派,与
        今日 op round_fail('模板库未加载')同形,Director 交回外循环
        重观察重派(ADR-0601 §5),无新环。
        """
        from sr_od.application.currency_war.operations.cw_op.cw_op_equip_all import (
            CwOpEquipAll,
            record_zero_wear_defect,
        )
        _drift = self._guard_screen_mismatch('货币战争-备战')
        if _drift is not None:
            log.warning('[cw!][composite] 装备 派发前置:当前画面 %s 非干净备战'
                        ' → 不派,环重观察', _drift)
            return f'装备 不在预期屏: {_drift}', False
        build = _build_equip_wear_plan(self._ctx)
        if build.fail_reason:
            return f'装备 {build.fail_reason}', False
        if not build.steps:
            # 空计划短路:不实例化 op。哨兵双挂点之计划面(equipped=0,
            # 计划面具名原因);front_only 回退分支不挂——与今日该分支
            # 无哨兵覆盖一致。
            if build.branch == 'm7':
                record_zero_wear_defect(self._ctx, 0,
                                        build.owned_wearable_names,
                                        build.empty_reason)
            log.info('[cw-equip] 计划空(%s)→ 具名 NOOP(闩照置)',
                     build.empty_reason)
            return f'装备 计划空: {build.empty_reason}', True
        result = CwOpEquipAll(self._ctx, build.steps).execute()
        # live 修复(2026-08-14,同 _run_composite):OperationResult 字段
        # 是 success(非 is_success)。op 级 success/status 作摘要透传
        #(信息面;成败不再门控任何下游——批3a 发出即职责完成,穿戴
        # 落地面由装备期望态对账族在下一入口暴露)。
        status = getattr(result, 'status', '')
        log.info(f'[cw][composite] 装备 → {status}')
        return f'装备 {status}', True

    def _run_composite(self, name: str, op_path: str,
                       guard_screen: str | None = None,
                       ) -> tuple[str, bool]:
        """执行组合动作(按模块路径延迟导入,避免 prep_actions ↔ operations 循环导入)。

        返回 ``(摘要, 是否发出)``:守卫不派/环境不备 = 未发出(False);
        组合 op 已实例化执行 = 发出(True,op 级结果仅作摘要透传)。

        :param guard_screen: 派发前置预期屏(T-163 D5,2026-09-08 用户架构
            裁定:「该不该执行」的判断归分发层)——非 None 时实例化组合 op
            **前**判干净备战,不干净即不派、环重观察(返回未发出断批重规划;
            批前提中途失效本就该重规划)。装备/工具两组合传入(对应 op 内
            旧 success-skip 闸门同批降级为执行断言);部署不传——其画面
            检查属转移验证用途(cw_op_deploy),非路由闸门,不越权接管。
        """
        import importlib

        if guard_screen is not None:
            current = self._guard_screen_mismatch(guard_screen)
            if current is not None:
                log.warning('[cw!][composite] %s 派发前置:当前画面 %s 非干净备战'
                            ' → 不派,环重观察', name, current)
                return f'{name} 不在预期屏: {current}', False
        module_path, cls_name = op_path.rsplit('.', 1)
        op_cls = getattr(importlib.import_module(module_path), cls_name)
        result = op_cls(self._ctx).execute()
        # live 修复(2026-08-14):OperationResult 字段是 success(非 is_success —— 那是
        # OperationRoundResult 的字段);旧 getattr 恒 False → 组合动作全被误判失败。
        # (批3a:success 仅作日志摘要,成败不再门控下游——发出即职责完成。)
        status = getattr(result, 'status', '')
        log.info(f'[cw][composite] {name} → {status}')
        return f'{name} {status}', True


# ===== 恢复原语退役墓碑(A9,用户裁定 2026-09-10)=====
#
# 原 ``try_recovery(op, ctx)``(已知弹层分型关闭恢复原语)随 B1 验证段
# 一并删除:其唯一消费位 = 验证失败 → 恢复分支(cw_screen_prep 旧路径/
# 生命周期路径),判效半拆除后该分支不复存在。已知弹层清场职责由环入口
# 清场注册表 ENTRY_OVERLAY_CLOSE 承接(观察侧,cw_screen_prep.lifecycle_
# observe/_clear_entry_overlays 在用);未知弹层交外循环 overlay 白名单
# 分发。本墓碑防同名/同职责结构静默复活。
