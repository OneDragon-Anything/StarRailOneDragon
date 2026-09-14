"""货币战争 备战决策环 执行器(P1;strategy/03(原 doc 15§4)/§13)。

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

slot 语义(unified-action-factory 批2b 归一后):席位域动作(SellBench/
SellDeployed/DeployMove)携**容器槽位表下标**(0 基,词表单一源 =
kernel/cw_vocab,坐标系裁定见其模块头);本执行器 = **执行坐标边**——
容器下标 → screen_info 槽位中心的换算单点(bench 侧 = 备战栏-N area 序
直取;deployed 侧 = kernel ``deployed_row_slot`` 单一函数)。坐标参数化
机械动作(WearEquip/工具原子类/OpenBox/OpenTome)的 row/slot 字段 =
画面物理排槽位 1 基(动作参数定义,拖点直取 area,不经换算)。
组合动作形态已随统一词表删除(R2:RunDeploy/RunEquip/RunTools 退役,
部署/穿戴/工具 = 决策核逐帧原子发射;CwScreenDeploy 画面 op 仍由
cw_loop 0j 前台无角色恢复链直调,非词表成员)。
"""
from __future__ import annotations

import time
from typing import TYPE_CHECKING, ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_economy import XP_CLICK_COST_FALLBACK
from sr_od.application.currency_war.kernel.cw_exec_state import (
    DEPLOYED_CAPACITY,
    _advance_gold,
    deployed_row_slot,
    exec_state_of,
)
from sr_od.application.currency_war.kernel.cw_vocab import (
    CW_ACTION_TYPES,
    ClickSpheres,
    CwAction,
    DeployMove,
    FurnaceUse,
    LevelUp,
    LuckyTokenUse,
    OpenBox,
    OpenTome,
    PerfectProjectorUse,
    PrecisionWrenchUse,
    PrivilegeCardUse,
    SellBench,
    SellDeployed,
    StaffProjectorUse,
    StartBattle,
    WearEquip,
    WrenchUse,
)

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_exec_state import BenchChar
from sr_od.application.currency_war.kernel.cw_obs_core import (
    SCREEN_NAME,
    _area_rect,
    area_center,
)
from sr_od.application.currency_war.kernel.cw_prep_actions import (
    SPHERE_CLICK_HARD_CAP,
)
from sr_od.application.currency_war.obs.cw_identity_obs import (
    read_supply_boxes,
)
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


def row_area_centers(ctx: SrContext, prefix: str) -> list[Point]:
    """从 screen_info「货币战争-备战」读全部 prefix-N 区域中心(N 升序)。

    同 CwScreenDeploy._row_centers 逻辑(读全不硬编码,后排 >6 时 screen_info 补区后自动跟上);
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


# (装备穿戴计划构造已迁 kernel/cw_equip_wear_plan(R2 原子通路);原
# 「本模块 import 供执行位 _run_equip 薄派发消费」随组合壳 RunEquip 删除
# 退役——发射位(mandate M7)直接消费同一构造函数,无第二源。)


def _expose_unhealthy_tracked_slots(tracked: list[BenchChar | None]) -> None:
    """tracked 写点槽号健康显影(占用槽号重复/越界 → 缺陷台账;best-effort)。

    判据单一源 = kernel ``bench_slots_healthy``;台账行型与 reseed 健康门
    同 kind(cw_shop_action_ops._reseed_bench_layout),reader_source 分键
    = 写点 fail-fast 显影,先于 reseed 门(其拒播种=晚发现)暴露既有污染。
    只显影不拒写:本 helper 的两个调用点均为「只减不增」摘除腿(置 None),
    拒绝摘除会让已卖/已上场件滞留 tracked,两账分叉比污染本身更糟;
    布局修复归 reconcile 写回(bench_from_compact 重建归一)。"""
    from sr_od.application.currency_war.kernel.cw_exec_state import (
        bench_occupied_slot_nos,
        bench_slots_healthy,
    )
    slots = bench_occupied_slot_nos(tracked)
    if bench_slots_healthy(slots):
        return
    try:
        from sr_od.application.currency_war.telemetry import defects
        defects.record_defect(
            'bench', defects.DEFECT_KIND_BENCH_SLOT_UNHEALTHY,
            expected='tracked 占用槽号唯一 ∧ 全在 1..BENCH_CAPACITY',
            observed=f'slots={sorted(map(str, slots))}',
            verdict=('留证-tracked 写点健康显影(既有重复/越界槽号;'
                     '摘除腿照常执行,布局修复归 reconcile 写回;'
                     '处理:频发→查 tracked 写点链)'),
            reader_source='tracked_write_guard',
            gap_large=True,
            note='tracked 写点槽号唯一性守卫(观察层对账仲裁批)')
    except Exception:  # noqa: BLE001  显影 best-effort
        pass


class PrepActionExecutor:
    """备战原子动作执行器(框架层;持 ctx + 宿主 op 复用截图/区域匹配/拖拽原语)。

    宿主 op = CwScreenPrep(SrOperation);机械执行(点击/拖拽/等待),落地
    判定归观察侧 reconcile(用户裁定 2026-09-10);拖拽统一走
    DragCwChar.drag_char(中心拖 + hold0,2026-08-13 实测验证)。
    """

    BOX_OPEN_DY: ClassVar[int] = 41                   # 「开启」文字区 = 箱 icon 下方偏移(2026-08-14 实测:槽center(563,911)→命中(565,952))
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
        # (LevelUp 金腿已随批2b 翻转切 action.cost 直写——
        # apply_prep_action_logic 单一写点,本执行缝对 LevelUp 恒 0。)
        self.last_gold_delta: int | None = None
        # 槽位中心(screen_info 静态,构造时读一次;F3 参数校验 + 拖拽坐标共用)
        self._bench_pts: list[Point] = row_area_centers(ctx, '备战栏')
        self._front_pts: list[Point] = row_area_centers(ctx, '前排')
        self._back_pts: list[Point] = row_area_centers(ctx, '后排')

    # ===== F3 参数校验(非法 → 错误串;合法 → None)=====

    def validate(self, action: CwAction) -> str | None:
        """校验动作合法域 + 参数(§5.0 F3)。返回错误描述;None=合法。

        两层:① 统一词表白名单(review M-4 —— 未知类型走参数非法路径拒绝,
        不进 execute 的验证失败/fail 循环;元组单一源 = cw_vocab
        CW_ACTION_TYPES);② 静态可判参数(槽位越界/row 枚举)。动态前置
        (球是否存在/overlay 是否开)由 execute 的完成验证覆盖(验证失败
        路径,非参数非法路径)。席位域动作坐标系 = 容器槽位表下标 0 基
        (词表模块头声明);机械动作 row/slot = 画面物理槽位 1 基。
        """
        if not isinstance(action, CW_ACTION_TYPES):
            return f'未知动作类型 {type(action).__name__}(不在动作全集,§4)'
        if isinstance(action, SellBench):
            if not (0 <= action.bench_idx < len(self._bench_pts)):
                return (f'SellBench bench_idx={action.bench_idx} 越界'
                        f'(0-{len(self._bench_pts) - 1})')
        elif isinstance(action, SellDeployed):
            n = DEPLOYED_CAPACITY
            if not (0 <= action.deployed_idx < n):
                return f'SellDeployed deployed_idx={action.deployed_idx} 越界(0-{n - 1})'
        elif isinstance(action, DeployMove):
            if not (0 <= action.bench_idx < len(self._bench_pts)):
                return (f'DeployMove bench_idx={action.bench_idx} 越界'
                        f'(0-{len(self._bench_pts) - 1})')
            if action.to_row not in ('front', 'back'):
                return f'DeployMove to_row={action.to_row!r} 非法(front/back)'
        elif isinstance(action, ClickSpheres):
            if not action.points:
                return 'ClickSpheres 载荷为空(挑选归决策侧 kernel,空载荷 = 无对象)'
            if len(action.points) > SPHERE_CLICK_HARD_CAP:
                return (f'ClickSpheres 载荷 {len(action.points)} '
                        f'超硬上限 {SPHERE_CLICK_HARD_CAP}(挑选越权)')
        elif isinstance(action, OpenBox):
            if action.slot is not None and not (1 <= action.slot <= len(self._bench_pts)):
                return f'OpenBox slot={action.slot} 越界(1-{len(self._bench_pts)})'
        elif isinstance(action, OpenTome):
            if action.slot is not None and not (1 <= action.slot <= len(self._bench_pts)):
                return f'OpenTome slot={action.slot} 越界(1-{len(self._bench_pts)})'
        elif isinstance(action, WearEquip):
            if action.row not in ('front', 'back'):
                return f'WearEquip row={action.row!r} 非法(front/back)'
            n = len(self._front_pts if action.row == 'front' else self._back_pts)
            if not (1 <= action.slot <= n):
                return f'WearEquip slot={action.slot} 越界(1-{n})'
        elif isinstance(action, (FurnaceUse, PrivilegeCardUse)):
            if action.target_kind not in ('equip', 'char'):
                return (f'{type(action).__name__} target_kind='
                        f'{action.target_kind!r} 非法(equip/char)')
            if action.target_kind == 'equip':
                if not action.item_name:
                    return (f'{type(action).__name__} equip 腿缺目标件名')
            else:
                if action.row not in ('front', 'back'):
                    return (f'{type(action).__name__} row={action.row!r} '
                            '非法(front/back)')
                n = len(self._front_pts if action.row == 'front'
                        else self._back_pts)
                if not (1 <= action.slot <= n):
                    return (f'{type(action).__name__} slot={action.slot} '
                            f'越界(1-{n})')
        elif isinstance(action, (WrenchUse, PrecisionWrenchUse,
                                StaffProjectorUse, PerfectProjectorUse,
                                LuckyTokenUse)):
            if action.row not in ('front', 'back'):
                return f'{type(action).__name__} row={action.row!r} 非法(front/back)'
            n = len(self._front_pts if action.row == 'front' else self._back_pts)
            if not (1 <= action.slot <= n):
                return f'{type(action).__name__} slot={action.slot} 越界(1-{n})'
        return None

    # ===== 执行入口(机械执行,无返回;执行前拒绝见 _execute_dispatch)=====

    def execute(self, action: CwAction) -> None:
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
        if emitted:
            # T-159 迁移 D:S1 清键门(唯一写点 = mandate.mark_s1_route_
            # check,三路径封闭枚举)。批3a 跨批对齐写死:``landed`` 供给
            # 改观察侧 reconcile 落地事实(接口本批定、批5 E1 落地供给),
            # 过渡期恒传 False = fail-closed(宁「该清不清」不「乱清」,
            # 后者可无限重复——T-167 交替活锁;「该清不清」侧 wanted 滞留
            # 一拍自愈,非正确性损害,mandate docstring 在案)。部署类
            # (DeployMove)(i)-deploy_launch 路径过渡期不清,防线语义
            # (no-op 不清)完整存活。发射位只读不写的同型纪律在此不适用
            # ——本门消费「已落地」事实,发射侧天然无此事实(猎点 8)。
            # OpenShop 分支不经本执行器(cw_screen_prep 流程层编排),开店
            # 落地不触清键面,与其置位语义(商店决策访问位)自洽。
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

    def _note_action_receipt(self, action: CwAction, emitted: bool,
                             detail: str,
                             extra: dict | None = None) -> None:
        """动作执行回执 → GameState receipts 域(R2 §3.1.1-4/§3.2.5;
        渠道② logic_action,唯一写点 = kernel note_action_receipt)。

        - **发出即簿记,不是验证**(M1③):applied = 分派面「是否发出」
          事实透传(执行前输入契约拒绝 = 未发出,回执 reason 带机械摘要);
          本写点零成败判定——不读屏、不做落地推断(「拖3次源槽未变」类
          像素验回执已随 T-192 判效拆除),落地判定归观察侧 reconcile;
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

    def _note_action_journal(self, action: CwAction, emitted: bool,
                             extra: dict | None) -> None:
        """备战动作 journal 行(op_journal.jsonl kind='action';T-113/
        ADR-0579 薄流的备战域扩围,T-16 执行缝账务包络):执行缝三套账的
        journal 回执腿——备战帧金动作逐行在账(定谳缺口 = T-234 复盘
        「备战帧 5 击零 journal 行」),op 分键「货币战争-备战动作」与商店
        「货币战争-买牌」域分键,行携 ``gold_delta`` 执行点金差(LevelUp
        行自批2b 起无本键——金腿切 action.cost 逻辑态直写,见
        _executed_gold_delta)。

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

    def _pre_sell_tracked_bc(self, action: CwAction) -> BenchChar | None:
        """卖出对象 dispatch 前 tracked 快照(T-16 执行点金差供给;卖出外
        动作 = None)。

        [索引定义] SellBench.bench_idx / SellDeployed.deployed_idx =
        容器槽位表下标(0 基;tracked 表 = 同构槽位表,tracked_bench 经
        bench_from_compact 重建恒 pad 态、tracked_deployed 恒 pad 态
        ADR-0316/0392)——按下标直接对位,零换算。取值时机 = execute()
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
                tracked = es.tracked_bench_chars or []
                return (tracked[action.bench_idx]
                        if 0 <= action.bench_idx < len(tracked) else None)
            from sr_od.application.currency_war.kernel.cw_exec_state import (
                pad_deployed,
            )
            tracked = pad_deployed(list(es.tracked_deployed or []))
            idx = action.deployed_idx
            return tracked[idx] if 0 <= idx < len(tracked) else None
        except Exception:   # noqa: BLE001  观测容缺,不阻塞执行链
            return None

    def _executed_gold_delta(self, action: CwAction, emitted: bool,
                             pre_sell_bc: BenchChar | None) -> int | None:
        """执行点金差显影(备战执行缝账务包络,T-16):gold 域备战动作在
        机械半边发出时点的金变化量。

        公式单一源与边界:
        - ``SellBench``/``SellDeployed`` = +sell_refund(星×招募费;对象 =
          dispatch 前快照,费单一源 = kernel ``bench_char_cost``——与容器
          逻辑态写口 apply_prep_action_logic 同式;身份不可辨 = None 诚实
          缺失,不做保守估值假账,观察覆盖兜底);
        - ``LevelUp`` = 0(批2b 翻转:金腿切 ``action.cost`` 直写,唯一
          写点 = apply_prep_action_logic LevelUp 分支;原执行缝金差
          ``_last_levelup_spent`` 通道随翻转退役,防双记);
        - ``ClickSpheres`` = None(球金通道随机,执行点不可推算——声明
          盲区,观察覆盖兜底,禁拍值);
        - 其余动作 = 0(发出零金动);未发出 = None(无金动无账)。
        ``None`` 与 0 的消费语义:仅非 None 非 0 进回执 extra 金差键与
        容器金账直推;None = 该动作本拍金账留观察覆盖。
        """
        if not emitted:
            return None
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

    def _execute_dispatch(self, action: CwAction) -> tuple[str, bool]:
        """动作分派(原 execute 主体;期望态钩子/闩在其上层 execute)。

        返回 ``(机械执行摘要, 是否实际发出)``。``emitted`` = **发出事实**
        (非落地判定、非成败回执):False 只用于「执行前输入契约拒绝/
        环境无对象」(球/箱/按钮等目标不在,M6 边界面——动作没发出,期望
        态/闩不登记);True = 点击/拖拽已发出。原 ``(ok, detail, landed)``
        三元组随 T-223 退役(成败与落地均不再是执行器输出;部署落地结构
        化判定迁观察侧对账,S1 门过渡期 landed=False 见 execute)。
        组合动作分支(RunDeploy/RunEquip/RunTools)已随统一词表删除退役
        (R2;部署/穿戴/工具 = 决策核逐帧原子发射)。
        """
        if isinstance(action, StartBattle):
            # A6 出战链(批4 拆):内部 ok(找不到按钮/未落地 = False)经
            # 发出位返回;last_launch_ok/执行态写点在 wrapper 半部(execute,
            # 执行缝替换分派时仍成立)。
            ok, detail = self._start_battle()
            return detail, ok
        return self._dispatch_direct(action)

    def _dispatch_direct(self, action: CwAction) -> tuple[str, bool]:
        """直执行动作分派。返回 (机械执行摘要, 是否实际发出)。"""
        if isinstance(action, ClickSpheres):
            return self._click_spheres(action)
        if isinstance(action, OpenBox):
            return self._open_box(action)
        if isinstance(action, OpenTome):
            return self._open_tome(action)
        if isinstance(action, SellBench):
            return self._sell_bench(action)
        if isinstance(action, SellDeployed):
            return self._sell_deployed(action)
        if isinstance(action, DeployMove):
            return self._deploy_move(action)
        if isinstance(action, WearEquip):
            return self._wear_equip(action)
        if isinstance(action, (FurnaceUse, PrivilegeCardUse, WrenchUse,
                               PrecisionWrenchUse, StaffProjectorUse,
                               PerfectProjectorUse, LuckyTokenUse)):
            return self._use_tool(action)
        if isinstance(action, LevelUp):
            return self._level_up()
        return f'未知动作类型 {type(action).__name__}', False

    # ===== 奖励域 =====

    def _click_spheres(self, action: ClickSpheres) -> tuple[str, bool]:
        """逐坐标点球(R4 机械执行半;载荷 = kernel ``select_sphere_clicks``
        产出的有序点击列)。

        大球优先/上界挑选归决策侧 kernel 单一源(发射位构造载荷),本方法
        纯机械逐个点(2026-09-02 用户指导 screen_flow_timing.md #16:奖励球
        飞行动画最长 ~2s → 点完等满动画;去向 = 备战/商店/装备栏)。零读屏
        零排序零截断(原读屏选球与 max_k 截断半随改形退役);席满时部分球
        可能没点开——由后续 heavy 观察自然回补(球仍在 → 下轮再派)。
        掉箱感知随之删除(掉箱归下一帧观察 → OpenBox 臂)。
        """
        for _x, _y in action.points:
            center = Point(_x, _y)
            self._ctx.controller.mouse_move(center)   # bug#1 缓解
            self._ctx.controller.click(center)
            self._op.park_cursor(after_wait=0.1)
        # 用户口径:飞行动画最长 ~2s → 等满(固定等待归产生动画的操作)
        time.sleep(2.0)
        detail = (f'点球 {len(action.points)} 个(载荷机械点;'
                  f'动画等待 2s,球未消由下一帧观察回补)')
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

        选卡动作不在本执行链(R7 批 2a 定形):点完开启本动作即终结
        (OpenBox 终结化,决策循环交回外循环)——武装箱选择画面由外循环
        按画面分发独立画面 op(:mod:``cw_screen_box_pick``)选卡(选卡
        决策单一源 = 策略 ``decide_box_card`` 契约 / 局外 kernel
        ``pick_equipment`` 机器;原「决策面 PickBoxCard 臂 + 执行器选卡半」
        随 PickBoxCard 删除退役)。
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
        log.info(f'[cw][box] 开箱槽{slot} → 点开启已发(交回外循环,武装箱'
                 '选择画面分发选卡)')
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

    # ===== 席位域 =====

    def _sell_bench(self, action: SellBench) -> tuple[str, bool]:
        """卖备战槽角色:drag 槽中心 → 出售区(``drag_bench_to_sell`` 单一源;
        机械执行,T-192 源槽像素验重试拆除)。返回 (摘要, 是否发出)。

        emitted = 动作已机械发出(拖拽原语零判效,落地事实归观察侧
        reconcile 对账)。bench_idx = 容器槽位表下标,拖点直取(执行坐标
        边:备战栏-N area 序 = 下标序,零换算);detail 沿用物理槽号显示
        (= 下标+1,遥测行连续性)。"""
        drag_bench_to_sell(self._op, self._ctx, action.bench_idx)
        self._track_remove_bench(action.bench_idx)
        # 用户口述口径(screen_flow_timing.md #21,2026-09-02):卖出金币
        # 动画很快,等 1s 足够——批尾观察前补这段,防读到金币动画帧。
        time.sleep(1.0)
        return (f'卖备战槽{action.bench_idx + 1} ✓', True)

    def _sell_deployed(self, action: SellDeployed) -> tuple[str, bool]:
        """卖上阵角色:drag 排槽中心 → 出售区(落点经 ``sell_point`` 单一源)。
        返回 (摘要, 是否发出)。emitted 语义 = 同 _sell_bench(机械发出)。

        执行坐标边:deployed_idx → (row, 物理槽号) 单一换算函数 =
        kernel ``deployed_row_slot``。"""
        row, slot_no = deployed_row_slot(action.deployed_idx)
        pts = self._front_pts if row == 'front' else self._back_pts
        src = pts[slot_no - 1]
        self._drag(src, sell_point(self._ctx))
        self._track_remove_deployed(row, slot_no)
        time.sleep(1.0)   # 同上 #21 口径:卖出动画 1s
        return (f'卖{row}排{slot_no} ✓', True)

    def _deploy_move(self, action: DeployMove) -> tuple[str, bool]:
        """bench → 上阵单步拖拽(腾席链专用;统一词表 DeployMove)。
        返回 (摘要, 是否发出)。

        执行坐标边:源拖点 = ``bench_idx`` 备战栏 area 序直取(容器下标 =
        area 序,零换算);落位排 = ``to_row``,落位物理槽 = tracked 占用
        现读首空位(kernel ``empty_deploy_slots`` 单一源,与发射位
        ``assign_deploy_slots`` 选排规则逐位同构——首选排满 fallback 另一排)。
        两排全满 = 未发出(False,观察重派);faction 字段不入执行(sim
        board 计数消费)。"""
        match = self._ctx.cw_match
        session = match.session if match is not None else None
        from sr_od.application.currency_war.kernel.cw_deploy_logic import (
            empty_deploy_slots,
        )
        from sr_od.application.currency_war.kernel.cw_exec_state import (
            pad_deployed,
        )
        tracked = (pad_deployed(list(exec_state_of(session).tracked_deployed))
                   if session is not None else [])
        front_empty, back_empty = empty_deploy_slots(
            tracked, front_total=len(self._front_pts),
            back_total=max(1, len(self._back_pts)))
        chosen, fallback = ((front_empty, back_empty)
                            if action.to_row == 'front'
                            else (back_empty, front_empty))
        if chosen:
            row, slot_no = action.to_row, chosen[0]
        elif fallback:
            row = 'back' if action.to_row == 'front' else 'front'
            slot_no = fallback[0]
        else:
            return '部署落位无空槽(两排全满,观察重派)', False
        src = self._bench_pts[action.bench_idx]
        dst = (self._front_pts if row == 'front' else self._back_pts)[slot_no - 1]
        self._drag(src, dst)
        self._track_move_deployed(action.bench_idx, row, slot_no)
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
        return (f'部署槽{action.bench_idx + 1}→{row}{slot_no} ✓', True)

    # ===== 装备/工具原子域(R2 穿戴 / R8 工具按消耗品各立类)=====

    _TOOL_NAME_BY_CLASS: ClassVar[dict[type, str]] = {
        FurnaceUse: '冶金炉',
        PrivilegeCardUse: '特权赋予卡',
        WrenchUse: '拆装扳手',
        PrecisionWrenchUse: '精密拆装扳手',
        StaffProjectorUse: '员工投影仪',
        PerfectProjectorUse: '完美投影仪',
        LuckyTokenUse: '好运令牌',
    }

    def _equip_slot_drag_point(self, row: str, slot: int) -> Point | None:
        """(row, slot) → avatar 拖拽点(与 CwOpEquipAll._slot_drag_point 同式;
        前排 = 前排-N rect 中心 x + y1+21(D-36 校准),后排 = 布局选档前缀
        (select_back_layout 单一入口,ADR-0385)同式派生)。缺失 → None
        (建档漂移,禁兜底坐标)。"""
        _si = self._ctx.screen_loader.get_screen(SCREEN_NAME)
        if _si is None:
            return None
        if row == 'front':
            r = next((a for a in _si.area_list
                      if a.area_name == f'前排-{slot}' and a.pc_rect is not None),
                     None)
            if r is None:
                return None
            return Point((r.pc_rect.x1 + r.pc_rect.x2) // 2, r.pc_rect.y1 + 21)
        _pfx = '后排'
        try:
            from sr_od.application.currency_war.obs.cw_back_layout import (
                select_back_layout as _sel_bl,
            )
            _pfx = _sel_bl(self._ctx, self._op.screenshot())[1] or _pfx
        except Exception:   # noqa: BLE001  选档失败退 6 槽基线(旧行为)
            pass
        r = next((a for a in _si.area_list
                  if a.area_name == f'{_pfx}-{slot}' and a.pc_rect is not None),
                 None)
        if r is None:
            return None
        return Point((r.pc_rect.x1 + r.pc_rect.x2) // 2, r.pc_rect.y1 + 21)

    def _owned_grid_locate(self, item_name: str) -> Point | None:
        """owned 装备网格内按名定位 icon 中心(机械现读;执行坐标边合法读)。

        名字定位是唯一稳锚(网格 reflow 使快照坐标失真);miss → None
        (调用方按「计划失效」未发出通道处理,下帧重派重算)。"""
        from sr_od.application.currency_war.obs.cw_equipment import read_equips
        from sr_od.application.currency_war.operations.cw_op.cw_op_equip_all import (
            get_equip_templates_cached,
        )
        templates = get_equip_templates_cached(self._ctx)
        if templates is None:
            return None
        rect = _area_rect(self._ctx, '区域-道具装备', SCREEN_NAME)
        if rect is None:
            return None
        hits = read_equips(self._op.screenshot(), templates,
                           equip_rect=(rect.x1, rect.y1, rect.x2, rect.y2))
        entry = next(((n, p) for n, p, _ in hits if n == item_name), None)
        return Point(entry[1][0], entry[1][1]) if entry is not None else None

    def _wear_equip(self, action: WearEquip) -> tuple[str, bool]:
        """穿装备单步(WearEquip 原子通路机械半;零比对出生,裁决 3)。

        流程 = 稳帧确认(动画收尾输入条件化,非判效)→ owned 网格按名
        定位源件 → 单次拖拽 → 发出即登记。零 CV-diff 零验穿零补救链——
        穿没穿归观察写入边对账(装备期望态对账族下一入口暴露);落空由
        下一入口观察重派承接(重算计划 = 天然重试)。逻辑态(owned 摘件)
        在观察侧 ``_project_prep_obs`` 直写。
        """
        target = self._equip_slot_drag_point(action.row, action.slot)
        if target is None:
            return (f'装备槽位坐标缺失:{action.row}-{action.slot}'
                    '(建档漂移,禁兜底坐标)'), False
        start = self._owned_grid_locate(action.item_name)
        if start is None:
            return (f'owned 网格未定位到 {action.item_name}'
                    '(模板库缺失/计划失效,下帧重派重算)'), False
        self._wait_stable_frame()
        self._ctx.controller.mouse_move(start)   # bug#1 缓解
        time.sleep(0.2)
        self._ctx.controller.drag_to(start=start, end=target,
                                     hold_time=0.5, duration=1.5)
        time.sleep(1.5)   # MCP drag 异步落地(memory mcp-click-async-sleep-rule)
        self._op.park_cursor(after_wait=0.1)
        detail = (f'穿戴 {action.item_name} → {action.char_name or "前排空槽"}'
                  f'({action.row}-{action.slot}) 已发(零比对,落地归观察对账)')
        log.info(f'[cw][wear] {detail}')
        return detail, True

    def _use_tool(self, action: CwAction) -> tuple[str, bool]:
        """工具消耗单步(R8 七类共用机械半:owned 网格内 icon → 目标拖曳)。

        源件 = 工具 icon(按注册名定位);目标 = equip 模式 owned 网格
        icon / char 模式角色槽位中心。零消耗确认对拍(裁决 3:原
        CwOpTools 三态对拍随原子化由观察承接)——拖后固定等待,消费
        真值 = 下一帧装备区读数;逻辑态(工具 −1/库存变换)在
        ``_project_prep_obs`` 按 ``EQUIP_WRITE_SIDES`` 申报直写。
        """
        tool_name = self._TOOL_NAME_BY_CLASS[type(action)]
        start = self._owned_grid_locate(tool_name)
        if start is None:
            return (f'owned 网格未定位到工具 {tool_name}'
                    '(模板库缺失/已消耗,下帧重派)'), False
        if getattr(action, 'target_kind', 'char') == 'equip':
            tgt_name = getattr(action, 'item_name', '')
            end = self._owned_grid_locate(tgt_name)
            if end is None:
                return (f'owned 网格未定位到目标件 {tgt_name}'
                        '(合成消耗/reflow,下帧重派)'), False
            tgt_desc = tgt_name
        else:
            pts = self._front_pts if action.row == 'front' else self._back_pts
            end = pts[action.slot - 1]
            tgt_desc = f'{action.row}-{action.slot}'
        self._ctx.controller.mouse_move(start)   # bug#1 缓解
        time.sleep(0.2)
        self._ctx.controller.drag_to(start=start, end=end,
                                     hold_time=0.5, duration=1.2)
        time.sleep(1.5)   # MCP drag 异步落地(memory mcp-click-async-sleep-rule)
        self._op.park_cursor(after_wait=0.1)
        detail = f'{tool_name} → {tgt_desc} 拖曳已发(零对拍,消费归观察)'
        log.info(f'[cw][tool] {detail}')
        return detail, True

    def _wait_stable_frame(self, interval: float = 0.3,
                           budget_s: float = 1.2) -> None:
        """拖前稳帧确认(与 CwOpEquipAll._wait_stable_frame 同式同参):
        等相邻两帧全图像素差均值 < 阈值(画面动画收尾)再拖。输入条件化
        等待,非判效;预算耗尽仍未稳 → 放行(落空由观察重派兜底)。"""
        deadline = time.time() + budget_s
        import numpy as np

        prev = self._op.screenshot()
        while time.time() < deadline:
            time.sleep(interval)
            cur = self._op.screenshot()
            diff = float(np.abs(prev.astype('int16') - cur.astype('int16')).mean())
            if diff < 2.0:
                return
            prev = cur

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

    def _track_remove_bench(self, bench_idx: int) -> None:
        """卖出后备势跟踪同步(单一跟踪账 tracked_bench_chars)。

        [索引定义] bench_idx = bench 槽位表下标 0-8(与动作字段同系);
        摘除 = 按下标置 None(权威槽位 = 下标,pad 态契约 ADR-0316 不破坏;
        T-261 前按信息位过滤产出紧凑列表,信息位/下标脱节经后续买入
        bench_place 追加累积成重复槽号——实机缺陷台账 slots=[1,3,4,5,6,7,8,9,9]
        等 4 局实证,reseed 健康门 L0/L1 显影后归观察层仲裁批治本)。"""
        match = self._ctx.cw_match
        if match is None or match.session is None:
            return
        from sr_od.application.currency_war.kernel.cw_exec_state import (
            pad_bench,
        )
        _es = exec_state_of(match.session)
        _pre = list(_es.tracked_bench_chars or [])
        _expose_unhealthy_tracked_slots(_pre)
        tracked = pad_bench(_pre)
        if 0 <= bench_idx < len(tracked):
            tracked[bench_idx] = None   # 置 None 不移位(pad 态保持)
        _es.tracked_bench_chars = tracked

    def _track_remove_deployed(self, row: str, slot: int) -> None:
        match = self._ctx.cw_match
        if match is None or match.session is None:
            return
        # ADR-0392:tracked_deployed 槽位表(置 None 不移位);物理 (row,
        # slot) → 槽位下标换算单一函数 = deployed_idx_of(执行坐标边)
        from sr_od.application.currency_war.kernel.cw_exec_state import (
            deployed_idx_of,
            pad_deployed,
        )
        tracked = pad_deployed(list(exec_state_of(match.session).tracked_deployed))
        idx = deployed_idx_of(row, slot)
        if 0 <= idx < len(tracked) and tracked[idx] is not None \
                and tracked[idx].position_pref == row:
            tracked[idx] = None
        exec_state_of(match.session).tracked_deployed = tracked

    def _track_move_deployed(self, bench_idx: int, to_row: str, to_slot: int) -> None:
        """上阵后备势跟踪同步:bench 条目 → deployed 条目(位置/槽位改写)。

        [索引定义] bench_idx = bench 槽位表下标 0-8(tracked 行按信息位
        bc.slot = 下标+1 对位);to_slot = 落位物理槽号 1 基(执行坐标边
        现读值,落槽后覆写信息位)。bench 侧摘除 = 按下标置 None(同
        _track_remove_bench 治本:紧凑重排会累积重复槽号,实机台账实证)。"""
        match = self._ctx.cw_match
        if match is None or match.session is None:
            return
        from sr_od.application.currency_war.kernel.cw_exec_state import (
            pad_bench,
        )
        _es = exec_state_of(match.session)
        tracked = pad_bench(list(_es.tracked_bench_chars or []))
        _expose_unhealthy_tracked_slots(tracked)
        moved = (tracked[bench_idx]
                 if 0 <= bench_idx < len(tracked) else None)
        if moved is not None:
            tracked[bench_idx] = None   # 置 None 不移位(pad 态保持)
        _es.tracked_bench_chars = tracked
        # ADR-0392:tracked_deployed 槽位表——deployed_place 单一源落槽;
        # to_slot 是执行器物理槽位真值,落槽后覆写信息位。
        from sr_od.application.currency_war.kernel.cw_exec_state import deployed_place
        if moved is not None:
            moved.position_pref = to_row
            deployed_place(exec_state_of(match.session).tracked_deployed, moved)
            moved.slot = to_slot

    # ===== 商店域 =====

    def _level_up(self) -> tuple[str, bool]:
        """买经验(R6 逐帧单击形态:找钮 → 单击 → 固定等待,零授权零计数)。

        执行器授权面全删(design.md unified-action-factory §2.6 LevelUp
        粒度定案):授权击数推导/血闸整级授权/逐击金地板全部上移发射位
        (kernel ``clicks_to_next_level`` 现算击数 > 0 = 每帧发射前置;
        spend_unified / levelup_budget_gate / posture 血闸 = 决策核发射门)。
        升 N 击 = N 帧(决策循环逐帧重组,与商店域单击形态
        ``cw_level_up_action`` 同构先例)。

        金腿 = 容器逻辑态直写(批2b 翻转定案):金账唯一写点 =
        ``apply_prep_action_logic`` LevelUp 分支按 ``action.cost`` 扣减
        (cost = 发射面 xp_click_cost 现算装载);原 2a 中间态执行缝金差
        (``_last_levelup_spent`` → ``_executed_gold_delta``)随翻转退役。
        单击价本处现算仅作 detail 显影(与发射面同源 kernel 读口)。
        经验/等级真值 = 下一帧观察对账族 + 逻辑态 xp/level 推进
        (``apply_prep_action_logic`` LevelUp 分支)双通道。
        """
        match = self._ctx.cw_match
        session = match.session if match is not None else None
        from sr_od.application.currency_war.kernel.cw_economy import (
            xp_click_cost,
        )
        btn = area_center(self._ctx, '备战标识-购买经验') or Point(296, 860)
        # 单击价容器读口(kernel 单一源,失读回退兜底价;与假环境执行缝同式)
        _price = XP_CLICK_COST_FALLBACK
        if session is not None:
            from sr_od.application.currency_war.kernel.cw_game_state import (
                board_state_of,
            )
            _price = xp_click_cost(board_state_of(session))
        self._ctx.controller.mouse_move(btn)   # bug#1 缓解(review M-5)
        self._ctx.controller.click(btn)
        # 光标 parking(审计 P0,2026-08-16 = M38 level 毒化注入点):按钮距等级显示区 18px,
        # 点击后光标压住 Lv.N 区 → 下帧 OCR 读错(4 毒化 3 位面的链头)。park 后再继续。
        self._op.park_cursor(before_wait=0.3, after_wait=0.15)
        # W612 挂点A(升级事件;发出即登记,观测 best-effort,零决策语义)。
        try:
            if session is not None:
                session.effect_inventory.on_level_up()
        except Exception as e:   # noqa: BLE001  观测失败不阻塞对局
            log.warning('[cw][levelup] effect inventory 挂点失败(不阻塞): %s', e)
        detail = (f'买经验单击 1 击花金{_price}'
                  '(逐帧单击形态;级真值=下一帧观察 reconcile)')
        log.info(f'[cw][levelup] {detail}')
        return detail, True

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



# ===== 恢复原语退役墓碑(A9,用户裁定 2026-09-10)=====
#
# 原 ``try_recovery(op, ctx)``(已知弹层分型关闭恢复原语)随 B1 验证段
# 一并删除:其唯一消费位 = 验证失败 → 恢复分支(cw_screen_prep 旧路径/
# 生命周期路径),判效半拆除后该分支不复存在。已知弹层清场职责由环入口
# 清场注册表 ENTRY_OVERLAY_CLOSE 承接(观察侧,cw_screen_prep.lifecycle_
# observe/_clear_entry_overlays 在用);未知弹层交外循环 overlay 白名单
# 分发。本墓碑防同名/同职责结构静默复活。
