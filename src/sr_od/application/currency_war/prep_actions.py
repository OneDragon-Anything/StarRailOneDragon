"""货币战争 备战决策环 执行器(P1;strategy/03(原 doc 15§4)/§13)。

框架层:本模块**不含玩法判断**(何时收球/卖谁/何时出战 = 策略层 CwStrategy.decide_prep_screen),
只负责「机械执行一个动作」(用户裁定 2026-09-10:动作 op 只管机械执行,
禁止做任何验证——点击/拖拽后不读屏判「是否生效」,落地判定完全归观察侧
reconcile 对账;终裁:执行回执 ``(progressed, detail)`` 退役,
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
机械动作(WearEquip/工具原子类/OpenBox/OpenTome/OpenBookcard)的
row/slot 字段 = 画面物理排槽位 1 基(动作参数定义,拖点直取 area,
不经换算)。
组合动作形态已随统一词表删除(R2:RunDeploy/RunEquip/RunTools 退役,
部署/穿戴/工具 = 决策核逐帧原子发射;CwScreenDeploy 画面 op 仍由
cw_loop 0j 前台无角色恢复链直调,非词表成员)。
统一动作工厂批3 收编(design.md unified-action-factory §2.4):动作级
机械执行体已逐字迁入 ``operations/cw_op/`` 备战 op 类(一 op 一文件),
分派改查单一注册表 ``action_op_for``(_dispatch_action);本模块保留
runner 包络(W209j 刹车/执行点金差/回执登记/validate 与机械原语)与
原方法薄委托(替身缝)。
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_exec_state import (
    DEPLOYED_CAPACITY,
    _advance_gold,
    exec_state_of,
)
from sr_od.application.currency_war.kernel.cw_game_state import board_state_of
from sr_od.application.currency_war.kernel.cw_vocab import (
    CW_ACTION_TYPES,
    ClickSpheres,
    CwAction,
    DeployMove,
    FurnaceUse,
    LevelUp,
    LuckyTokenUse,
    OpenBookcard,
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
    停止[W209j刹车]')``,随端口回执退役改为停机短路异常:执行器抛出,
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
    ``_sell_bench`` 共用本 helper:「拖→出售区」机械一段(拆源槽
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


@dataclass
class PrepExecEnv:
    """备战动作 op 执行环境(统一动作工厂批3;design.md unified-action-
    factory §2.4 env 条款)。

    以公共字段 ``op``/``match``/``config`` 结构化满足
    ``cw_action_base.ActionExecEnv`` 协议(与 ShopExecEnv 同构;运行时不
    检查协议,项目既有风格)。``executor`` = 备战 runner 包络引用(坐标
    槽位表/机械原语/tracked 账同步的单一宿主;体迁 op 经此消费,执行包络
    留守 runner);``detail``/``emitted`` = prep 域 ``(detail, emitted)``
    语义旁路字段(基类 ``execute`` 返回契约恒 True,不进返回值;与现行
    ``executor.last_detail`` 旁路同构),op 类写、runner 包络读。
    """

    op: SrOperation
    match: object            # CurrencyWarMatch(避免运行时导入环,注解宽松)
    config: object = None    # 协议公共面(备战动作执行面零 config 消费)
    executor: PrepActionExecutor | None = None
    detail: str = ''
    emitted: bool = False


class PrepActionExecutor:
    """备战原子动作执行器(框架层;持 ctx + 宿主 op 复用截图/区域匹配/拖拽原语)。

    宿主 op = CwScreenPrep(SrOperation);机械执行(点击/拖拽/等待),落地
    判定归观察侧 reconcile(用户裁定 2026-09-10);拖拽统一走
    DragCwChar.drag_char(中心拖 + hold0,2026-08-13 实测验证)。
    """

    LAUNCH_DEAD_LIMIT: ClassVar[int] = 3   # 出战未落地连败停机阈值(session 级计数;两局实证环重入 ~2min/次)
    #: P4R:出战后「转移成功」的拦截弹窗白名单(锚 = 已建档 id_mark)。
    #: 出战按钮点击后备战标识消失但下列弹窗在场 = 出战被游戏拒(1-1 事故
    #: 「前台区域无角色」确认弹窗盖标识 = 旧判据假成功)。新弹窗建档后追加。
    #: (批3 体迁后单一源仍在本 runner:消费 = StartBattleOp 发射家族,
    #: cw_exec_state/cw_loop 注释指针同源。)
    POST_LAUNCH_BLOCKERS: ClassVar[tuple[tuple[str, str], ...]] = (
        ('货币战争-提示-前台无角色', '标识-无角色提示'),
    )

    def __init__(self, op: SrOperation, ctx: SrContext) -> None:
        self._op = op
        self._ctx = ctx
        # 机械执行摘要(最近一次 execute 的 detail;登记件解析输入,非成败
        # 回执——端口无返回,摘经由本属性旁路供 on_outcome detail)。
        self.last_detail: str = ''
        # 批4 挂账:StartBattle 发射位内部事实(A6 出战链判效面,批4 随
        # J3/J4 消费端同退役)。消费方 = cw_loop 发射核(J2/J3 达标臂/锁定
        # 重试)。getattr 容缺(__new__ 桩形态)。
        self.last_launch_ok: bool | None = None
        # 执行点金差显影(备战执行缝账务包络;写点 = execute 每次
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
        elif isinstance(action, OpenBookcard):
            if action.slot is not None and not (1 <= action.slot <= len(self._bench_pts)):
                return f'OpenBookcard slot={action.slot} 越界(1-{len(self._bench_pts)})'
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

    # ===== 执行入口(机械执行,无返回;执行前拒绝见 validate)=====

    def execute(self, action: CwAction) -> None:
        """机械执行一个动作(无返回;发出即职责完成,落地判定归
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
        # 执行点金差显影账每动作复位:上动作余量禁跨动作残留。
        # 落地门前捕获备战席占用(tracked 账现读):S1 路径 (ii) 翻正判读
        # 需要 pre/post 两点,post 点必须在 dispatch 之后读(dispatch 内
        # 卖出/部署 handler 会同步销账)。
        _pre_bench = self._bench_tracked_count()
        # 卖出对象 dispatch 前快照(执行点金差供给;dispatch 内 tracked
        # 已同步移除,事后复查恒落空)。
        _pre_sell_bc = self._pre_sell_tracked_bc(action)
        detail, emitted = self._dispatch_action(action)
        self.last_detail = detail
        gold_delta = self._executed_gold_delta(action, emitted, _pre_sell_bc)
        self.last_gold_delta = gold_delta
        if emitted and gold_delta:
            # 执行缝金账直推(备战帧金动作入账;写通道单一源 =
            # cw_exec_state._advance_gold 容器金账,logic_action 渠道,
            # 观察赢覆盖修正不变)。备战帧 LevelUp 花金/卖出回金自此
            # 入状态账,不再只存在于遥测文本(根因 = 执行缝三套账只辖
            # 商店单元,定谳 = 2026-09-06 迭代落地审)。
            _m_gd = self._ctx.cw_match
            _sess_gd = _m_gd.session if _m_gd is not None else None
            if _sess_gd is not None:
                _advance_gold(_sess_gd, int(gold_delta))
        _gold_extra = ({'gold_delta': int(gold_delta)}
                       if gold_delta not in (None, 0) else None)
        self._note_action_receipt(action, emitted, detail, extra=_gold_extra)
        if isinstance(action, StartBattle):
            # 批4 挂账:StartBattle 发射位内部事实(A6 判效面,批4 随
            # J2/J3/J4 消费端同退役)。真执行链 = 注册表分派 StartBattleOp
            # 发射位内部 ok(找不到按钮/未落地 = False,在册例外返回契约,
            # design.md unified-action-factory §2.4);执行缝(假环境)不经
            # 真分派 = applied 真值(F11 双轨申报)。同步写执行态(消费端
            # = cw_loop 备战环出口 0j 预算复位判定 F3,读后即清)。
            self.last_launch_ok = emitted
            _m_sb = getattr(self._ctx, 'cw_match', None)
            _sess_sb = getattr(_m_sb, 'session', None) if _m_sb is not None else None
            if _sess_sb is not None:
                exec_state_of(_sess_sb).last_prep_battle_launch_ok = emitted
        if emitted:
            # S1 清键门(唯一写点 = mandate.mark_s1_route_
            # check,三路径封闭枚举)。批3a 跨批对齐写死:``landed`` 供给
            # 改观察侧 reconcile 落地事实(接口本批定、批5 E1 落地供给),
            # 过渡期恒传 False = fail-closed(宁「该清不清」不「乱清」,
            # 后者可无限重复——交替活锁形态;「该清不清」侧 wanted 滞留
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
          像素验回执已随判效拆除),落地判定归观察侧 reconcile;
        - 每动作 op 恰一条 logic_action 行(动作全集逐 op 覆盖;W209j 停机
          短路在本口之前抛出 = 执行被拒不产行——停机非动作);
        - ``extra`` = 执行面结构化字段透传(§3.2.1 质量词表执行面;
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

    def _pre_sell_tracked_bc(self, action: CwAction) -> BenchChar | None:
        """卖出对象 dispatch 前 tracked 快照(执行点金差供给;卖出外
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
            if isinstance(action, SellBench):
                tracked = board_state_of(session).tracked_books.bench or []
                return (tracked[action.bench_idx]
                        if 0 <= action.bench_idx < len(tracked) else None)
            from sr_od.application.currency_war.kernel.cw_exec_state import (
                pad_deployed,
            )
            tracked = pad_deployed(list(
                board_state_of(session).tracked_books.deployed or []))
            idx = action.deployed_idx
            return tracked[idx] if 0 <= idx < len(tracked) else None
        except Exception:   # noqa: BLE001  观测容缺,不阻塞执行链
            return None

    def _executed_gold_delta(self, action: CwAction, emitted: bool,
                             pre_sell_bc: BenchChar | None) -> int | None:
        """执行点金差显影(备战执行缝账务包络):gold 域备战动作在
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

    def _dispatch_action(self, action: CwAction) -> tuple[str, bool]:
        """动作分派(统一动作工厂批3 收编:原 ``_execute_dispatch``/
        ``_dispatch_direct`` 两条 isinstance 链删除,入口改查单一注册表
        ``action_op_for``;design.md unified-action-factory §2.4。原组合
        动作分支(RunDeploy/RunEquip/RunTools)已随统一词表删除退役(R2))。

        返回 ``(机械执行摘要, 是否实际发出)``。prep 域 ``(detail,
        emitted)`` 语义经 :class:`PrepExecEnv` 旁路字段承载(动作 op 的
        ``execute`` 返回契约恒 True,基类 cw_action_base);在册例外 =
        StartBattleOp——返回值 = 发射位**内部事实**(非恒 True;找不到
        按钮/未落地 = False),即发出事实。词表外类型 = 注册表
        AssertionError 响亮暴露(生产不可达:F3 validate 先拒)。
        """
        from sr_od.application.currency_war.operations.cw_op.cw_action_registry import (
            action_op_for,
        )
        env = PrepExecEnv(op=self._op, match=self._ctx.cw_match, config=None,
                          executor=self)
        ret = action_op_for(action).execute(env)
        if isinstance(action, StartBattle):
            return env.detail, bool(ret)
        return env.detail, env.emitted

    # ===== 奖励域 =====

    def _click_spheres(self, action: ClickSpheres) -> tuple[str, bool]:
        """薄委托(体已迁 ``cw_click_spheres_action.ClickSpheresOp``,统一
        动作工厂批3 体迁 + 薄委托,替身缝保留;机械语义 docstring 随体)。"""
        return self._dispatch_action(action)

    def _bench_tracked_count(self) -> int:
        """备战席占用数(tracked 账现读;席翻正判读输入)。

        tracked 账由本执行器卖出/部署 handler 同步销账,pre/post 两点
        夹一次 dispatch 即「本帧落地是否使席 free 由 0 翻正」的观测读数
        (方案 §3.3 (ii);账缺页形态由消费臂门 1 下帧现读自愈)。会话
        缺席/读失败 = -1(调用侧按「不可判」处理,不产生翻正)。
        """
        try:
            match = self._ctx.cw_match
            if match is None or match.session is None:
                return -1
            tracked = board_state_of(match.session).tracked_books.bench
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
        """薄委托(体已迁 ``cw_open_box_action.OpenBoxOp``;批3 体迁 +
        薄委托,替身缝保留)。终结动作(R7):交回等待 = OpenBoxOp.
        terminal_wait(与 _OVERLAY_ANIM_WAIT_S 等价,等价锁在册)。"""
        return self._dispatch_action(action)

    def _open_tome(self, action: OpenTome) -> tuple[str, bool]:
        """薄委托(体已迁 ``cw_open_tome_action.OpenTomeOp``;批3 体迁 +
        薄委托,替身缝保留)。"""
        return self._dispatch_action(action)

    def _open_bookcard(self, action: OpenBookcard) -> tuple[str, bool]:
        """薄委托(体已迁 ``cw_open_bookcard_action.OpenBookcardOp``;批3
        体迁 + 薄委托,替身缝保留——测试直调面沿此缝)。"""
        return self._dispatch_action(action)

    # ===== 席位域 =====

    def _sell_bench(self, action: SellBench) -> tuple[str, bool]:
        """薄委托(体已迁 ``cw_prep_sell_bench_action.PrepSellBenchOp``;
        批3 体迁 + 薄委托,替身缝保留)。"""
        return self._dispatch_action(action)

    def _sell_deployed(self, action: SellDeployed) -> tuple[str, bool]:
        """薄委托(体已迁 ``cw_sell_deployed_action.SellDeployedOp``;批3
        体迁 + 薄委托,替身缝保留)。"""
        return self._dispatch_action(action)

    def _deploy_move(self, action: DeployMove) -> tuple[str, bool]:
        """薄委托(体已迁 ``cw_deploy_move_action.DeployMoveOp``;批3 体迁
        + 薄委托,替身缝保留)。"""
        return self._dispatch_action(action)

    # ===== 装备/工具原子域(R2 穿戴 / R8 工具按消耗品各立类;机械原语
    #       _equip_slot_drag_point/_owned_grid_locate/_wait_stable_frame
    #       留守本 runner,体迁 op 经 env.executor 消费)=====

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
        """薄委托(体已迁 ``cw_wear_equip_action.WearEquipOp``;批3 体迁 +
        薄委托,替身缝保留)。"""
        return self._dispatch_action(action)

    def _use_tool(self, action: CwAction) -> tuple[str, bool]:
        """薄委托(体已迁 ``cw_tool_use_action.ToolUseOp``,工具原子七类
        共用;批3 体迁 + 薄委托,替身缝保留)。"""
        return self._dispatch_action(action)

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
        源槽像素验重试已拆除)。

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
        信息位/下标脱节会让后续买入
        bench_place 追加累积成重复槽号——实机缺陷台账 slots=[1,3,4,5,6,7,8,9,9]
        等 4 局实证,reseed 健康门 L0/L1 显影后归观察层仲裁批治本)。"""
        match = self._ctx.cw_match
        if match is None or match.session is None:
            return
        from sr_od.application.currency_war.kernel.cw_exec_state import (
            pad_bench,
        )
        _books = board_state_of(match.session).tracked_books
        _pre = list(_books.bench or [])
        _expose_unhealthy_tracked_slots(_pre)
        tracked = pad_bench(_pre)
        if 0 <= bench_idx < len(tracked):
            tracked[bench_idx] = None   # 置 None 不移位(pad 态保持)
        _books.bench = tracked

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
        tracked = pad_deployed(list(
            board_state_of(match.session).tracked_books.deployed))
        idx = deployed_idx_of(row, slot)
        if 0 <= idx < len(tracked) and tracked[idx] is not None \
                and tracked[idx].position_pref == row:
            tracked[idx] = None
        board_state_of(match.session).tracked_books.deployed = tracked

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
        _books = board_state_of(match.session).tracked_books
        tracked = pad_bench(list(_books.bench or []))
        _expose_unhealthy_tracked_slots(tracked)
        moved = (tracked[bench_idx]
                 if 0 <= bench_idx < len(tracked) else None)
        if moved is not None:
            tracked[bench_idx] = None   # 置 None 不移位(pad 态保持)
        _books.bench = tracked
        # ADR-0392:tracked_deployed 槽位表——deployed_place 单一源落槽;
        # to_slot 是执行器物理槽位真值,落槽后覆写信息位。
        from sr_od.application.currency_war.kernel.cw_exec_state import deployed_place
        if moved is not None:
            moved.position_pref = to_row
            deployed_place(board_state_of(match.session).tracked_books.deployed,
                           moved)
            moved.slot = to_slot

    # ===== 商店域 =====

    def _level_up(self, action: LevelUp | None = None) -> tuple[str, bool]:
        """薄委托(体已迁 ``cw_prep_level_up_action.PrepLevelUpOp``;批3
        体迁 + 薄委托,替身缝保留)。

        ``action`` 形参 = 注册表分派载体(原签名无参——单击体不读动作
        字段;缺省补零价占位实例仅作类型解析,行为零变化)。"""
        return self._dispatch_action(
            action if action is not None else LevelUp(cost=0))

    # ===== 战斗域 =====
    # (批3 体迁:_start_battle/_launch_attempt/_launch_dead_reset/
    #  _launch_dead_escalate 已迁 cw_start_battle_action.StartBattleOp,
    #  基类契约在册例外——execute 返回值 = 发射位内部事实;本入口保留
    #  薄委托替身缝,返回序保持原 (ok, detail)。)

    def _start_battle(self) -> tuple[bool, str]:
        """薄委托(体已迁 ``cw_start_battle_action.StartBattleOp``;批3
        体迁 + 薄委托,替身缝保留)。"""
        detail, emitted = self._dispatch_action(StartBattle())
        return emitted, detail




# ===== 恢复原语退役墓碑(A9,用户裁定 2026-09-10)=====
#
# 原 ``try_recovery(op, ctx)``(已知弹层分型关闭恢复原语)随 B1 验证段
# 一并删除:其唯一消费位 = 验证失败 → 恢复分支(cw_screen_prep 旧路径/
# 生命周期路径),判效半拆除后该分支不复存在。已知弹层清场职责由环入口
# 清场注册表 ENTRY_OVERLAY_CLOSE 承接(观察侧,cw_screen_prep.lifecycle_
# observe/_clear_entry_overlays 在用);未知弹层交外循环 overlay 白名单
# 分发。本墓碑防同名/同职责结构静默复活。
