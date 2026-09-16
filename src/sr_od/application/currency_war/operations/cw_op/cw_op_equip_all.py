
"""货币战争 全员装备 op:read_equips 多列 owned → 过滤工具 → drag 穿戴类 → 前排角色头像。

**机制(D-36~D-40)**:drag **穿戴类**装备(排除工具)→ 前排角色头像 (743,350) = 穿(D-36 轮滑鞋验)。
装备 owned = **多列规则网格**(col1 x1800-1918 + col2 x1660-1800 + ...,D-40),**无空槽**(「+」=星徽 icon D-38)。
read_equips(thr7)名准+无假阳(D-39,4/4 click 验),覆盖多列(区域 = screen_info「区域-道具装备」x1620-1918,D-40)。

**零比对形态(裁决 3 比对收口,2026-09-14 unified-action-factory 批 2a)**:
原 avatar-slot CV-diff 验穿(R19)随穿戴原子化删除——穿没穿归观察写入边
对账(装备期望态对账族在下一入口暴露),动作 op 内零验证;拖前稳帧确认
(``_wait_stable_frame``,动画收尾输入条件化)保留,拖后零判效。
计划/拉黑/排序判据单一源 = ``kernel/cw_equip_wear_plan``(2a 自本模块迁居,
本模块只消费)。**已接 cycle**(CwScreenPrep 备战单轮 ③,live A8 实跑)。

**前置(外层判干净)**:建档画面判定确认「货币战争-备战」(入口 + 每次拖拽循环重入点)。
面板/浮窗态各有独立建档且盖备战 id_mark(角色详情面板盖右下「出战」)→ 判不出备战
即非干净,直接停;识别器 read_equip_grid 纯识别,画面状态判断统一在本层。
"""
import time
from typing import ClassVar

import numpy as np
from cv2.typing import MatLike

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.file_utils import get_project_root
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_equip_env import (
    classify_zero_wear_stop_reason,
)
from sr_od.application.currency_war.kernel.cw_equip_wear_plan import (  # noqa: F401
    DRAG_FAIL_BLACKLIST_LIMIT,  # noqa: F401
    EquipPlanBuild,  # noqa: F401
    EquipWearStep,
    _empty_slots,  # noqa: F401
    _prioritize_wearable,  # noqa: F401
    equip_drag_key,
    filter_alloc_blacklisted,  # noqa: F401
    register_equip_drag_failure,  # noqa: F401
)
from sr_od.application.currency_war.kernel.cw_equip_wear_plan import (
    FRONT_SLOT_COUNT as _FRONT_SLOT_COUNT,
)
from sr_od.application.currency_war.kernel.cw_obs_core import _area_rect
from sr_od.application.currency_war.obs.currency_war_char_id import (
    AvatarTemplates,
    load_avatar_templates,
)
from sr_od.application.currency_war.obs.cw_equipment import (
    EQUIPMENTS,
    load_equip_templates,
    load_equip_tm_grays,
    read_equips,
)
from sr_od.application.currency_war.obs.cw_identity_obs import (
    _ctx_slots,
)
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation

# 工具类装备(拆装扳手/冶金炉/随便骰子等,非 drag 穿;D-34 单独处理)
# 类名单一源 = cw_equipment_data.EQUIP_TOOL_CATEGORY(与策略侧同源,原本地
# 平行定义 _TOOL_CATEGORIES 已收编)。

# ===== bug#1 drag 落空根治参数(replay/defect_ledger.jsonl drag 条目实证)=====
# 拖前稳帧确认保留(拖前输入条件化,非判效);补救链(坐标现读重定位 +
# 按压/移动参数逐档升级)随 CV-diff 判效半退役——无落地信号即无重试判据,
# 落空由下一入口观察重派(重算计划 = 天然重试)。
DRAG_HOLD_TIME: float = 0.5    # 首拖按压保持秒数(拾取识别窗)
DRAG_DURATION: float = 1.5     # 首拖移动时长秒数
_SETTLE_DIFF_THRESHOLD: float = 2.0   # 稳帧判据:相邻两帧全图像素差均值 < 阈值 = 画面已稳


def register_equip_worn(session, item_name: str, char_name: str,
                        row: str, slot: int,
                        produced_by: str = 'CwOpEquipAll') -> None:
    """装备分布逻辑推进(两态制 ADR-0651;原 §3 B-6 行 M7 装备拖拽期望态)。

    拖拽发出即调(发出即登记,零比对形态:原「落点已验(CV-diff 判穿)
    后调」门随验穿拆除;实读帧照常覆盖,失配 = 推算 bug 留证修码):
    ``last_owned_equips`` −1 件 + ``tracked_deployed`` 目标角色 equips +1 件。
    槽位坐标系:deployed 槽位表下标 = 前排 slot−1 / 后排
    DEPLOYED_FRONT_CAPACITY+slot−1(与 apply_op_effect SellDeployed 同式)。
    best-effort:session 缺失 / infra 异常不阻塞穿戴主循环。
    """
    if session is None:
        return
    try:
        from sr_od.application.currency_war.kernel.cw_exec_state import (
            DEPLOYED_FRONT_CAPACITY,
        )
        from sr_od.application.currency_war.kernel.cw_game_state import (
            game_state_of,
        )
        owned = list(getattr(session, 'last_owned_equips', None) or [])
        if item_name in owned:
            owned.remove(item_name)
            session.last_owned_equips = owned
        idx = (slot - 1 if row == 'front'
               else DEPLOYED_FRONT_CAPACITY + slot - 1)
        dep = list(game_state_of(session).tracked_books.deployed or [])
        if 0 <= idx < len(dep) and dep[idx] is not None:
            dep[idx].equips = list(getattr(dep[idx], 'equips', None) or []) \
                + [item_name]
    except Exception as e:  # noqa: BLE001  观测面不阻塞穿戴
        log.info('[cw-equip] 装备分布逻辑推进跳过: %s', e)


def _owned_wearable_names(hits: list) -> list[str]:
    """read_equips 命中 → 穿戴类 owned 名单(工具类过滤;ADR-0358 搬运链写端)。

    与主流程 ``wearable`` 同过滤口径(非工具类即穿戴候选);ADR-0358 修法 A:owned
    持有面原先有读点、无写链,决策/遥测全盲(3,061 条 decisions 里 state.equips
    0 条非空)——本函数供 ``equip_all`` 写 ``session.last_owned_equips``。
    """
    from sr_od.application.currency_war.data.cw_equipment_data import (
        EQUIP_TOOL_CATEGORY,
    )
    return [n for n, _, _ in hits
            if EQUIPMENTS.get(n) is not None
            and EQUIPMENTS[n].category != EQUIP_TOOL_CATEGORY]


# ===== hold 触发权归策略侧(ADR-0526 判据表;ADR-0601 §3-C1)=====
# hold/释放判据已整编迁移至 kernel/cw_equip_env(函数名清单与唯一消费位 =
# prep_actions._build_equip_wear_plan 分发段);收窄后的逐件判定亦随求值块
# 迁出(2026-09-09 批),本层零时机判断(与 ADR-0461 裁定 3 同理由),
# 残留判据函数引用 = 违规回归(验收锁 test_cw_equip_plan_builder)。


def get_equip_templates_cached(ctx: SrContext) -> dict[str, tuple[MatLike, tuple, np.ndarray]] | None:
    """加载 cw_equip SIFT 模板(缓存 ctx.cw_equip_templates,首次 load 后复用)。

    模块级共享 helper(工具执行批 ADR-0532 整改:与 CwOpTools 的模板装载
    同一单一源,禁两处各写一份装载逻辑);``CwOpEquipAll``/``CwOpTools``
    同源消费。
    """
    cached = getattr(ctx, 'cw_equip_templates', None)
    if cached is not None:
        return cached
    base = get_project_root() / 'assets/template'
    equip_dir = base / 'currency_war' / 'equip_plaza'   # 混合库(plaza 官方+手工补充)
    if not equip_dir.is_dir():
        equip_dir = base / 'currency_war' / 'equip_legacy'
    if not equip_dir.is_dir():
        log.warning(f'[cw-equip] cw_equip 模板库不存在 {equip_dir}')
        return None
    templates = load_equip_templates(equip_dir)
    ctx.cw_equip_templates = templates
    log.info(f'[cw-equip] 加载 {len(templates)} 个 cw_equip 模板(缓存 ctx)')
    return templates


def get_equip_tm_grays_cached(ctx: SrContext) -> dict[str, MatLike] | None:
    """加载 cw_equip TM grays(缓存 ctx.cw_equip_tm_grays;``read_row_equipped``
    读 avatar 已穿用;模块级单一源,``CwOpEquipAll._get_tm_grays`` 委托本函数,
    分发段 ``_build_equip_wear_plan`` 资源前置同源消费)。

    与 ``get_equip_templates_cached`` 互补:后者 SIFT keypoint/descriptor
    (read_equips owned 列用);本函数返简单 gray(``matchTemplate`` 用,
    read_equipped_below below-avatar mini icon 用)。两套同源(`assets/template/cw_equip`)。
    """
    cached = getattr(ctx, 'cw_equip_tm_grays', None)
    if cached is not None:
        return cached
    base = get_project_root() / 'assets/template'
    equip_dir = base / 'currency_war' / 'equip_plaza'   # 混合库(同 get_equip_templates_cached)
    if not equip_dir.is_dir():
        equip_dir = base / 'currency_war' / 'equip_legacy'
    if not equip_dir.is_dir():
        log.warning(f'[cw-equip] cw_equip 模板库不存在 {equip_dir}')
        return None
    grays = load_equip_tm_grays(equip_dir)
    ctx.cw_equip_tm_grays = grays
    log.info(f'[cw-equip] 加载 {len(grays)} 个 cw_equip TM grays(缓存 ctx)')
    return grays


def get_avatar_templates_cached(ctx: SrContext) -> AvatarTemplates | None:
    """加载立绘 SIFT 模板(M7 角色身份用;缓存 ctx.cw_portrait_templates,
    与 deploy_bench 同源;模块级单一源供分发段 ``_build_equip_wear_plan`` 消费,
    ``CwOpEquipAll._get_avatar_templates`` 委托本函数)。"""
    cached = getattr(ctx, 'cw_portrait_templates', None)
    if cached is not None:
        return cached
    base = get_project_root() / 'assets/template'
    portrait_dir = base / 'currency_war' / 'portrait_plaza'
    if not portrait_dir.is_dir():
        return None
    templates = load_avatar_templates(portrait_dir)
    ctx.cw_portrait_templates = templates
    log.info(f'[cw-equip] 加载 {len(templates)} 个 avatar 模板(M7 身份,缓存 ctx)')
    return templates


def record_zero_wear_defect(ctx: SrContext, equipped: int,
                            owned_names: list[str], stop_reason: str) -> None:
    """零穿戴哨兵(W596/W593 方案②;纯观测,零行为变更;ADR-0601 §3-C1
    起为**双挂点单一源**:op 执行面(拖拽落空/槽位坐标缺失/画面漂移)与
    分发段计划面(pool_empty/两 hold/分配方案空/分配对全部拉黑,经
    ``prep_actions._run_equip`` 空计划短路挂,equipped=0)。

    触发面(DESIGN §五):装备 pass 结束时 worn_added==0 且 owned 有**可穿**件
    (工具类过滤,与穿戴决策同口径)且 state.round_num≥3 → defect_ledger 记
    ``equip_zero_wear`` 一条(带 owned 名单、stop 原因与**辖域归域**;
    severity 走通道缺省 L2 观测,不停机)。病灶出处:局22(r3~r9 连续零
    穿戴无一报警,排查靠三段证据合围)——本哨兵让下次复发当轮可查台账归因。
    round<3 不触发:r1~r2 开局 hold(ADR-0257)零穿戴是 by design。
    无 state(run 上下文缺失/离线)静默跳过。
    **辖域二分(18 号稿 §1.2)**:stop_reason 按归域分流裁定——
    strategy_by_design=策略 by-design(释放判据表解释);strategy_gap=
    策略语义缺口;execution=执行链;execution_pending=枚举外兜底行
    (暂归执行链待分诊,新枚举值回 18 号稿 §1.2 补表)。
    """
    if equipped > 0:
        return
    from sr_od.application.currency_war.data.cw_equipment_data import (
        EQUIP_TOOL_CATEGORY,
    )
    wearable_owned = [n for n in owned_names
                      if EQUIPMENTS.get(n) is not None
                      and EQUIPMENTS[n].category != EQUIP_TOOL_CATEGORY]
    if not wearable_owned:
        return
    from sr_od.application.currency_war.telemetry import defects as cw_telemetry
    _match = getattr(ctx, 'cw_match', None)
    # 换源(装配源迁移):plane/round = 容器单例 node(同备战观察
    # 写端刷新);node 未观察沿用旧缺帧静默跳过语义。
    _node_zw = None
    _sess_zw = getattr(_match, 'session', None) if _match is not None else None
    if _sess_zw is not None:
        from sr_od.application.currency_war.kernel.cw_game_state import (
            game_state_of,
        )
        _node_zw = game_state_of(_sess_zw).node.value
    if _node_zw is None or int(_node_zw.round_num) < 3:
        return
    _reason = stop_reason or '循环自然结束(stall)'
    cw_telemetry.record_defect(
        surface='equip', kind='equip_zero_wear',
        expected='owned 有可穿件且 round>=3:本 op 至少穿 1 件',
        observed=(f'worn_added=0 owned={wearable_owned} '
                  f'stop_reason={_reason} '
                  f'domain={classify_zero_wear_stop_reason(stop_reason)}'),
        plane=int(_node_zw.plane),
        round_num=int(_node_zw.round_num),
        note=('观测面不停机;辖域二分(18 号稿 §1.2):'
              'strategy_by_design=by-design 残留;'
              'strategy_gap=策略语义缺口(词缀优先层/工具消费评估);'
              'execution=执行链即查;execution_pending=枚举外兜底待分诊'))


class CwOpEquipAll(SrOperation):
    """备战:read_equips 多列 owned → 过滤工具 → drag 穿戴类 → 前排**空**角色头像(P0-2 占位检测)。

    装备库区域 = screen_info「区域-道具装备」(多列 x1620-1918,D-40;坐标维护 yml 非硬编码)。
    **P0-2 drag 前占位检测**:``read_row_equipped`` 读前排 avatar 已穿 → 只往空槽 drag(``_empty_slots``,
    修原 target 按已穿计数索引旧字面量表 → 已穿槽被覆盖)。
    **零比对形态**(裁决 3,批 2a):avatar-slot CV-diff 验穿删除——拖前
    稳帧确认(输入条件化)+ 单次机械拖拽 + 发出即登记,穿没穿归观察
    写入边对账(装备期望态对账族下一入口暴露)。落空重试通道 = 观察
    重派(重算计划天然重试)。
    前置:已在「货币战争-备战」(角色详情面板关 —— 装备详情面板不遮 icon D-37)。**已接 cycle**(CwScreenPrep 备战单轮 ③)。
    """

    SCREEN_NAME: ClassVar[str] = '货币战争-备战'
    # 失败状态具名常量(ADR-0601 §4;禁散字符串,判读侧可分键)——
    # 消费面 = run_record/日志判读与 prep_no_progress 停机留证归因。
    STATUS_SCREEN_DRIFTED: ClassVar[str] = \
        '画面漂移(批内非干净备战,执行环境失配)'
    # 计划失效(ADR-0601 §3-C1;tools C3 同形):计划步件经首读+一次机械
    # 现读重试仍不可定位(robust 合成消耗/列 reflow)→ round_fail 闩不置,
    # 下帧重派时分发段 _build_equip_wear_plan 对 fresh 帧重算 = 天然重算,
    # 保住期内穿戴极大性(合成产物当帧进入新计划)。
    STATUS_PLAN_STALE: ClassVar[str] = \
        '装备计划失效(计划步件两次现读不可定位,交回重派重算)'
    # 空计划合法稳态(发射契约对称出口):生产路径不可达(分发段 _run_equip
    # 已对空计划短路 NOOP+闩照置),仅为直接构造面(测试/未来调用方)提供
    # 对称出口,不承担闩闭合职责。
    STATUS_PLAN_EMPTY: ClassVar[str] = \
        '装备计划空(合法稳态,无穿戴步)'
    # 前排槽位数(= screen_info 前排-1..4;deploy 侧同容量;消费面 =
    # 本类旧计划面,现役单一源 = kernel/cw_equip_wear_plan.FRONT_SLOT_COUNT)。
    FRONT_SLOT_COUNT: ClassVar[int] = _FRONT_SLOT_COUNT

    def __init__(self, ctx: SrContext, plan: list[EquipWearStep]):
        """组合 op 构造(计划随指令下发;ADR-0601 §3-C1)。

        ``plan`` = 分发段 ``prep_actions._build_equip_wear_plan`` 产出的
        机械执行计划(EquipWearStep 列表),**必填无缺省**——缺计划无法
        执行;空计划由分发段短路具名 NOOP,生产路径不会以空计划构造本 op
        (直接构造面的空计划走 STATUS_PLAN_EMPTY 防御分支)。
        """
        SrOperation.__init__(self, ctx, op_name='货币战争-全员装备')
        self.plan: list[EquipWearStep] = list(plan)

    def _front_avatar_points(self) -> list[Point] | None:
        """前排 4 槽 avatar 拖拽点(screen_info 前排-N rect 派生);缺档 → None。

        坐标单一源(screen_info「前排-N」),派生式与后排 _slot_drag_point
        同款 —— x = rect 中心,y = rect.y1+21(D-36 验 y350 = rect.y1+21
        校准)。任一 前排-N area 缺失(建档漂移/档案损坏)→ 返回 None,
        **禁残表输出**:槽位下标与 area 号对齐,残表会把 slot 语义错位
        (拖点落邻槽);消费方各自按既有语义显式失败/跳过申报,禁兜底
        硬编码坐标。
        """
        pts: list[Point] = []
        for _i in range(1, self.FRONT_SLOT_COUNT + 1):
            _r = _area_rect(self.ctx, f'前排-{_i}', self.SCREEN_NAME)
            if _r is None:
                log.warning('[cw!][equip] screen_info 前排-%d 缺失(%s),'
                            '前排拖拽点不可派生,禁兜底坐标', _i, self.SCREEN_NAME)
                return None
            pts.append(Point((_r.x1 + _r.x2) // 2, _r.y1 + 21))
        return pts

    def _get_templates(self) -> dict[str, tuple[MatLike, tuple, np.ndarray]] | None:
        """加载 cw_equip SIFT 模板(单一源 = get_equip_templates_cached)。"""
        return get_equip_templates_cached(self.ctx)

    def _get_tm_grays(self) -> dict[str, MatLike] | None:
        """加载 cw_equip TM grays(单一源 = get_equip_tm_grays_cached)。"""
        return get_equip_tm_grays_cached(self.ctx)

    def _wait_stable_frame(self, interval: float = 0.3,
                           budget_s: float = 1.2) -> MatLike:
        """拖前稳帧确认:等相邻两帧全图像素差均值 < 阈值(画面动画收尾)再拖。

        根因关系:drag 坐标来自截图现读;若备战面板入场/上件 reflow 动画未收尾,
        帧内 icon 位置与终态错位 → 按压抓空(drag 物理落空形态之一)。预算耗尽
        仍未稳 → 放行返回当前帧(不卡死流程;落空由补救链兜底)。
        """
        deadline = time.time() + budget_s
        prev = self.screenshot()
        while time.time() < deadline:
            time.sleep(interval)
            cur = self.screenshot()
            diff = float(np.abs(prev.astype(np.int16) - cur.astype(np.int16)).mean())
            if diff < _SETTLE_DIFF_THRESHOLD:
                return cur
            prev = cur
        return prev

    def _drag_equip(self, start: Point, target: Point) -> None:
        """单次 drag 穿戴 + 拖前稳帧确认(零比对形态:无验穿无返回值)。

        拖前 ``_wait_stable_frame`` 确认画面已稳(动画未收尾时按压抓空 =
        落空主形态,输入条件化等待非判效);拖后固定异步落地等待,零
        CV-diff 零判效——穿没穿归观察写入边对账(裁决 3,批 2a 零比对
        出生;落空由下一入口观察重派,重算计划 = 天然重试)。
        """
        self._wait_stable_frame()
        self.ctx.controller.mouse_move(start)
        time.sleep(0.2)
        self.ctx.controller.drag_to(start=start, end=target,
                                    duration=DRAG_DURATION,
                                    hold_time=DRAG_HOLD_TIME)
        time.sleep(1.5)  # MCP drag 异步落地(memory mcp-click-async-sleep-rule)
        # 光标 parking(审计 R4):drag 终点=目标 avatar,光标停其上 → Director heavy observe 的
        # read_deployed_chars SIFT 同 rect 读被遮。park 后再继续。
        self.park_cursor(after_wait=0.1)

    def _get_avatar_templates(self) -> AvatarTemplates | None:
        """加载立绘 SIFT 模板(单一源 = get_avatar_templates_cached)。"""
        return get_avatar_templates_cached(self.ctx)

    def _slot_drag_point(self, row: str, slot: int) -> Point | None:
        """(row, slot) → avatar 拖拽点;后排位扩展支持。

        前排走 _front_avatar_points()(screen_info 前排-N rect 派生,D-36 验
        y350);后排从 screen_info rect 推导:drag_y = rect.y1+21(前排 329→350
        校准外推)。验穿 y 分量随 CV-diff 拆除退役(零比对形态)。

        排障修正:后排 area 前缀原硬编码「后排」(6 槽档),而占用读侧
        (M7 ``_row_specs``)与部署侧均走 ``select_back_layout`` 档位前缀
        (「后排7槽」/「后排8槽」,ADR-0385)——布局非 6 槽时槽号→rect 错配
        半个槽位,拖点落在邻槽(装备穿到别人身上/落空;复盘
        g_20260902_181254 A 条「back-3 拖点坐标可疑」的坐标侧根因)。
        修正 = 与占用读侧同源(布局选档单一入口);读档失败退 6 槽基线。
        """
        if row == 'front':
            _front_pts = self._front_avatar_points()
            if _front_pts is None:
                return None   # 前排 area 缺档 → None,走既有跳步申报语义
            if 1 <= slot <= len(_front_pts):
                return _front_pts[slot - 1]
            return None
        _pfx = '后排'
        try:
            from sr_od.application.currency_war.obs.cw_back_layout import (
                select_back_layout as _sel_bl,
            )
            _pfx = _sel_bl(self.ctx, self.screenshot())[1] or _pfx
        except Exception:   # noqa: BLE001  选档失败退 6 槽基线(旧行为)
            pass
        slots = _ctx_slots(self.ctx, _pfx, 10)
        for idx, r in slots:
            if idx == slot:
                return Point((r.x1 + r.x2) // 2, r.y1 + 21)
        return None

    def _zero_wear_sentinel(self, equipped: int, owned_names: list[str],
                            stop_reason: str) -> None:
        """零穿戴哨兵挂点(执行面;单一源 = 模块级 record_zero_wear_defect,
        计划面挂点在 prep_actions._run_equip 空计划短路,双挂点共用实现)。"""
        record_zero_wear_defect(self.ctx, equipped, owned_names, stop_reason)

    @operation_node(name='全员装备', is_start_node=True, node_max_retry_times=5)
    def equip_all(self) -> OperationRoundResult:
        screen = self.last_screenshot
        # 入口预期屏执行断言(2026-09-08 用户架构裁定):动作 op
        # 不作路由决策——非预期屏如实 round_fail 交回外循环重判,禁旧
        # round_success('跳过') 假成功吞分发(外层把 RunEquip ✓ 当完成入账,
        # 装备实际没装;事故里还掩盖了「环的批前提已变」)。「该不该
        # 执行」的判断上提 = PrepActionExecutor._run_composite 派发前置
        # (实例化前判干净备战,不干净不派、环重观察),本检查降级为第二道
        # 执行断言(派发到落地间隙的画面漂移防线)。
        current = self.check_and_update_current_screen(
            screen, screen_name_list=[self.SCREEN_NAME])
        if current != self.SCREEN_NAME:
            log.warning('[cw!][equip] 当前画面 %s 非预期屏(%s)→ 执行断言 fail',
                        current, self.SCREEN_NAME)
            return self.round_fail(f'不在预期屏: {current}')
        templates = self._get_templates()
        if templates is None:
            return self.round_fail('cw_equip 模板库未加载')
        # 装备库区域 = screen_info「区域-道具装备」(多列 owned icon,D-40;坐标单一源 yml)
        rect = _area_rect(self.ctx, '区域-道具装备', self.SCREEN_NAME)
        if rect is None:
            return self.round_fail('screen_info 区域-道具装备 缺失')
        equip_rect = (rect.x1, rect.y1, rect.x2, rect.y2)
        # P0-2 drag 前占位检测:读前排 avatar 已穿(read_row_equipped below-avatar TM)→ 只往空槽 drag。
        # 修原 bug:target 按已穿计数索引旧字面量表(符号已删) → 已穿槽被覆盖。空槽序号 1-based → 派生表[slot-1]。
        tmpl_grays = self._get_tm_grays()
        if tmpl_grays is None:
            return self.round_fail('cw_equip TM grays 未加载(无法读槽位占位)')
        # ===== 计划消费循环(ADR-0601 §3-C1:机械执行,禁二次求值)=====
        # 计划 = kernel/cw_equip_wear_plan 产出随构造下发(self.plan);
        # hold/释放/分配四 kernel 判据已随求值块迁出至 kernel 构造位——
        # 本文件对四名零字面引用(机械执行红线)。
        # 本循环只做:屏断言(E2/E3 执行断言)→ owned 现读(W209g 快照
        # 写端)→ 计划件定位(miss → 一次机械现读重试 → 仍 miss =
        # STATUS_PLAN_STALE fail-fast,下帧重派时构造位对 fresh 帧重算)
        # → 拖点解析(缺失跳步)→ 零比对机械拖拽(发出即登记)。
        _match = self.ctx.cw_match
        equipped = 0
        _owned_last: list[str] = []   # 哨兵输入:步内最后一次 owned 全量快照
        _stop_reason = ''   # 零穿戴哨兵(W596)归因字段:执行面停手原因
        # 回退计划(全步 char_name='')不挂哨兵——与今日 front-only 分支
        # 无哨兵覆盖一致(哨兵的 M7 观测面辖域保持不变)。
        _is_m7 = any(s.char_name for s in self.plan)
        _skipped = 0   # 拖点解析失败跳步计数(计划 for 有界,无今日 stall 断面)
        if not self.plan:
            # 空计划防御(发射契约对称出口):生产路径不可达——分发段
            # _run_equip 已对空计划短路(具名 NOOP + 闩照置);本分支只为
            # 直接构造面(测试/未来调用方)提供合法稳态,不承担闩闭合职责
            # (闩写点唯一在 prep_actions.execute 执行位)。
            return self.round_success(CwOpEquipAll.STATUS_PLAN_EMPTY)
        for step in self.plan:
            cur = self.screenshot()
            if self.check_and_update_current_screen(
                    cur, screen_name_list=[self.SCREEN_NAME]) != self.SCREEN_NAME:
                # 执行断言(ADR-0601 §4 E2/E3;前置画面闸执行断言化裁定的
                # 批内延伸):批内画面漂移 = 执行环境失配,如实 round_fail
                # 交回外循环重判,禁 break+success 把弃批记成假完成。
                # 哨兵观测保留(纯观测零行为;stop_reason 串供分类域锁)。
                log.warning('[cw!][equip] 画面漂移(面板/浮窗开)→ 执行断言 fail')
                if _is_m7:
                    self._zero_wear_sentinel(equipped, _owned_last,
                                             '画面非干净备战')
                return self.round_fail(
                    CwOpEquipAll.STATUS_SCREEN_DRIFTED)
            hits = read_equips(cur, templates, equip_rect=equip_rect)
            _owned_last = [n for n, _, _ in hits]
            # ADR-0358 修法 A 搬运链写端(W209g 断点②,ADR-0387 追加):
            # 写端**全量 hits**(工具进快照,采集层无权丢数据);每次现读
            # 都覆写(穿戴后 owned 减少,末次读=最新持有面)。主写端 =
            # 备战入口观察装配点(cw_screen_prep._observe heavy,P4 观察
            # 接线);本执行位步内重写 = 穿戴推进后的最新持有面
            # (定位读的合法执行层锚),两写端值同构后写覆盖先写。
            if _match is not None and _match.session is not None:
                _match.session.last_owned_equips = list(_owned_last)
            # 拖点解析(front-only 步 = 前排空槽 avatar 序号;M7 步 =
            # (row, slot) 物理槽位现读)。解析失败只跳过本计划步——计划
            # for 有界(每对恰出现一次),其余计划步照常执行。
            if step.char_name == '':
                _front_pts = self._front_avatar_points()
                if _front_pts is None:
                    # area 缺失 = 建档漂移,显式失败交外环重判(同上
                    # 「区域-道具装备 缺失」round_fail 先例);禁兜底坐标,
                    # 禁残表索引(槽位语义错位)。
                    return self.round_fail(
                        'screen_info 前排-N 缺失(货币战争-备战),'
                        '前排 avatar 拖拽点不可派生,禁兜底坐标')
                target = _front_pts[step.slot - 1]
            else:
                target = self._slot_drag_point(step.row, step.slot)
                if target is None:
                    log.info('[cw-equip] %s 槽位坐标缺失 → 跳过该计划步',
                             step.char_name)
                    _skipped += 1
                    _stop_reason = f'{step.char_name} 槽位坐标缺失'
                    continue
            # 网格现读定位计划件:首读 miss → 一次机械现读重试(单件瞬时
            # 识别 miss 由该次重试吸收,不进失效通道)→ 仍 miss = 计划失效
            # (件被 robust 合成消耗/列 reflow)→ fail-fast 闩不置,下帧
            # 重派重算(保住期内穿戴极大性)。
            entry = next(((n, p) for n, p, _ in hits if n == step.item_name),
                         None)
            if entry is None:
                _retry = read_equips(self.screenshot(), templates,
                                     equip_rect=equip_rect)
                entry = next(((n, p) for n, p, _ in _retry
                              if n == step.item_name), None)
            if entry is None:
                log.warning('[cw!][equip] 计划步件 %s 两次现读不可定位 → %s',
                            step.item_name, CwOpEquipAll.STATUS_PLAN_STALE)
                if _is_m7:
                    self._zero_wear_sentinel(equipped, _owned_last,
                                             CwOpEquipAll.STATUS_PLAN_STALE)
                return self.round_fail(CwOpEquipAll.STATUS_PLAN_STALE)
            name, (cx, cy) = entry
            log.info('[cw-equip] 计划步 drag %s @(%d,%d) → %s(%s-%d)',
                     name, cx, cy,
                     step.char_name or '前排空槽', step.row, step.slot)
            # 零比对机械拖拽(裁决 3):单次发出,无验穿无补救链无拉黑
            # 登记——落地信号面已删,失败由下一入口观察重派承接(重算
            # 计划天然重试);发出即登记装备分布逻辑推进。
            self._drag_equip(Point(cx, cy), target)
            equipped += 1
            if _match is not None and _match.session is not None:
                register_equip_worn(_match.session, name,
                                    step.char_name,
                                    step.row, step.slot)
            log.info('[cw-equip] %s → %s 拖拽已发(零比对,落地归观察对账)',
                     name, step.char_name or '前排空槽')
        if _is_m7:
            # 零穿戴哨兵(W596/W593 方案②;纯观测,不停机零行为变更)。
            # 计划面原因(pool_empty/两 hold/分配方案空/分配对全部拉黑)
            # 挂分发段空计划短路(双挂点单一源 = record_zero_wear_defect),
            # 本挂点只辖执行面原因。
            self._zero_wear_sentinel(equipped, _owned_last, _stop_reason)
        if _skipped:
            log.info('[cw-equip] 拖点解析失败跳步 %d(其余计划步已照常执行)', _skipped)
        if self.plan and all(s.char_name == '' for s in self.plan):
            # front-only 回退计划:detail 字面与今日回退路径一致
            # (空槽列表 = 计划步槽位集,升序)。
            return self.round_success(
                f'装备 {equipped} 件到前排 avatar(空槽 '
                f'{sorted(s.slot for s in self.plan)})')
        return self.round_success(f'M7 装备 {equipped} 件(角色级分配)')
