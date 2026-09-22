"""货币战争 备战决策环 执行器(P1;strategy/03(原 doc 15§4)/§13)。

框架层:本模块**不含玩法判断**(何时收晶矿/卖谁/何时出战 = 策略层 CwStrategy.decide_prep_screen),
只负责「机械执行一个动作」(用户裁定 2026-09-10:动作 op 只管机械执行,
禁止做任何验证——点击/拖拽后不读屏判「是否生效」,落地判定完全归观察侧
reconcile 对账;终裁:执行回执 ``(progressed, detail)`` 退役,
``execute`` 无返回,发出即职责完成)。失败路径(§13.2 修订):
- 参数非法 → validate 返回错误串(Director 拒绝执行 + 交回留证);
- 执行前输入契约拒绝(晶矿/箱/按钮等目标不在,执行前观察,M6 边界面)→
  本动作未发出,机械交回外循环重观察重决策;
- 执行异常 → 异常上抛(Director 上抛 = 本环 fail,外层 op retry 接管)。

slot 语义(unified-action-factory 批2b 归一后):席位域动作(CwActionSellBenchParam/
CwActionSellDeployedParam/CwActionDeployMoveParam)携**容器槽位表下标**(0 基,词表单一源 =
kernel/cw_vocab,坐标系裁定见其模块头);本执行器 = **执行坐标边**——
容器下标 → screen_info 槽位中心的换算单点(bench 侧 = 备战栏-N area 序
直取;deployed 侧 = kernel ``deployed_row_slot`` 单一函数)。坐标参数化
机械动作(CwActionWearEquipParam/工具原子类/CwActionOpenBoxParam/CwActionOpenTomeParam/CwActionOpenBookcardParam)的
row/slot 字段 = 画面物理排槽位 1 基(动作参数定义,拖点直取 area,
不经换算)。
统一动作工厂批3 收编(design.md unified-action-factory §2.4):动作级
机械执行体已逐字迁入 ``operations/cw_op/`` 备战 op 类(一 op 一文件),
分派改查单一注册表 ``action_op_for``(_dispatch_action);本模块保留
runner 包络(W209j 刹车/执行点金差/回执登记/validate 与机械原语)与
原方法薄委托(替身缝)。
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

from one_dragon.base.geometry.point import Point
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_exec_state import (
    DEPLOYED_CAPACITY,
)
from sr_od.application.currency_war.kernel.cw_game_state import gs_of_ctx
from sr_od.application.currency_war.kernel.cw_vocab import (
    CW_ACTION_TYPES,
    OBS_SCOPES,
    CwAction,
    CwActionCollectOreParam,
    CwActionDeployMoveParam,
    CwActionFurnaceUseParam,
    CwActionLevelUpParam,
    CwActionLuckyTokenUseParam,
    CwActionObsParam,
    CwActionOpenBookcardParam,
    CwActionOpenBoxParam,
    CwActionOpenTomeParam,
    CwActionPerfectProjectorUseParam,
    CwActionPrecisionWrenchUseParam,
    CwActionPrivilegeCardUseParam,
    CwActionSellBenchParam,
    CwActionSellDeployedParam,
    CwActionStaffProjectorUseParam,
    CwActionStartBattleParam,
    CwActionWearEquipParam,
    CwActionWrenchUseParam,
)

if TYPE_CHECKING:
    from sr_od.application.currency_war.kernel.cw_game_state import Unit
from sr_od.application.currency_war.kernel.cw_obs_core import (
    SCREEN_NAME,
    _area_rect,
    area_center,
)
from sr_od.application.currency_war.kernel.cw_prep_actions import (
    ORE_CLICK_HARD_CAP,
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
#: 穿戴拖前固定等待(等备战面板/上件 reflow 动画收尾,非判效)。取值 =
#: 被替换的稳帧轮询典型检测档 0.3s 向上取整(与 pick 确认 0.6-1.2s 固定
#: 等待族同量级);后随动作的动画由拖后固定等待覆盖,极端 reflow 未收尾
#: 致按压抓空 = 未发出形态,由下一入口观察对账显影 + 决策环自然重派
#: (按「不存在偶发丢失」纪律查根因调常量,禁恢复轮询)。
PREP_DRAG_SETTLE_WAIT_S: float = 0.5


class StopBrakeShortCircuit(RuntimeError):
    """W209j 停机短路异常(纵深防御第二层)。

    语义 = 运行中被停 → 拒绝执行任何动作(run 27 实证:director 环在
    Deploy 钩子 stop_running 后仍发 CwActionStartBattleParam 点出战——环顶检查(第一层)
    之外,本入口兜底覆盖绕环路径)。原表达通道 = 执行回执 ``(False, '已
    停止[W209j刹车]')``,随端口回执退役改为停机短路异常:执行器抛出,
    调用方(cw_screen_prep 决策环 / cw_loop 发射核)捕获后交回外循环,
    下轮 loop 顶见 STOP 退出。判据 = last_run_result 非空(start 清
    None/stop 写入;run_state STOP 是 idle 初始态不能直接用)。
    """


def row_area_centers(ctx: SrContext, prefix: str) -> list[Point]:
    """从 screen_info「货币战争-备战」读全部 prefix-N 区域中心(N 升序)。

    逐区现读、不硬编码(后排 >6 时 screen_info 补区后自动跟上);
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
    (W62 件2 落地;游戏机制 = 拖到左下区域即出售,无按钮)。

    area 缺失 = 建档漂移/档案损坏 → RuntimeError 显式上抛(信息带 area
    名),禁回退硬编码坐标静默点击(坐标单一真相源)。消费面含
    卖上阵 off-target 拖拽,落点直入 drag 原语 → None 不可流入,
    直取 + 上抛是唯一兼容形态。
    """
    pt = area_center(ctx, '区域-出售区')
    if pt is None:
        raise RuntimeError(
            'area 缺失:区域-出售区(货币战争-备战),出售区落点不可派生,禁兜底坐标')
    return pt


def drag_bench_to_sell(op: SrOperation, ctx: SrContext, bench_idx: int) -> None:
    """拖备战槽(槽位下标 0-8)→ 出售区(共享卖原语,W62 件2/设计章2.10)。

    d2 卖通道生产接线(shop.py prefix 循环 CwActionSellBenchParam 分支)与 prep_actions
    ``_sell_bench`` 共用本 helper:「拖→出售区」机械一段(拆源槽
    像素验重试:发出即职责完成,落地事实归观察侧 reconcile 对账);
    tracking 同步由调用方各自做。失焦守卫同 ``PrepActionExecutor._drag``
    语义(窗口后台化时拖拽输入静默丢,r9 实证)。

    Args:
        op: 调用方 op(取 ctx.controller 操作)。
        ctx: SrContext。
        bench_idx: 槽位下标 0-8(:列表下标 = 物理备战栏槽位 1-9 减一);
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


# (装备穿戴计划构造单一源 = kernel/cw_equip_wear_plan(R2 原子通路);
#  发射位(mandate M7)直接消费同一构造函数,无第二源。)


def _expose_unhealthy_tracked_slots(tracked: list) -> None:
    """tracked 写点槽号健康显影(占用槽号重复/越界 → 缺陷台账;best-effort)。

    判据单一源 = kernel ``bench_slots_healthy``;reader_source 分键
    = 写点 fail-fast 显影(早于对账层暴露既有污染)。
    只显影不拒写:本 helper 的两个调用点均为「只减不增」摘除腿(置 None),
    拒绝摘除会让已卖/已上场件滞留 tracked,两账分叉比污染本身更糟;
    布局修复归 reconcile 写回。

    容器形(BenchSlot)槽号由下标权威派生,结构性健康:读不到元素级
    槽号信息位按无槽号处理恒静默(显影分支保留作防线,健康输入零噪声)。"""
    from sr_od.application.currency_war.kernel.cw_exec_state import (
        bench_slots_healthy,
    )
    slots = [s for s in (getattr(b, 'slot', None)
                         for b in tracked if b is not None)
             if s is not None]
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
    """备战动作 op 执行环境(动作 op 重组批③;design.md §1.1 env 条款)。

    域依赖结构化包,op 构造时传入(原 execute 时刻注入改为构造时)。
    ``executor`` = 备战 runner 包络引用(坐标槽位表/机械原语/tracked 账
    同步的单一宿主;op 体经此消费,执行包络留守 runner)。``detail``/
    ``emitted`` = 历史 prep 域旁路字段(批③起消费面改 round 结果成功态
    与 status,op 体保留写以维持体迁移逐字性,字段值不再被包络消费);
    ``skip_substate`` 仍被包络消费(回执 extra 留证)。
    """

    op: SrOperation
    match: object            # CurrencyWarMatch(避免运行时导入环,注解宽松)
    config: object = None    # 协议公共面(备战动作执行面零 config 消费)
    executor: PrepActionExecutor | None = None
    detail: str = ''
    emitted: bool = False
    # 免战跳过子态标记(StartBattleOp 上报通道;op 写、runner 包络
    # _dispatch_action 读一次转发 game state 上报路径。False = 常规出战)
    skip_substate: bool = False


class PrepActionExecutor:
    """备战原子动作执行器(框架层;持 ctx + 宿主 op 复用截图/区域匹配/拖拽原语)。

    宿主 op = CwScreenPrep(SrOperation);机械执行(点击/拖拽/等待),落地
    判定归观察侧 reconcile(用户裁定 2026-09-10);拖拽统一走
    DragCwChar.drag_char(中心拖 + hold0,2026-08-13 实测验证)。
    """

    def __init__(self, op: SrOperation, ctx: SrContext) -> None:
        self._op = op
        self._ctx = ctx
        # 机械执行摘要(最近一次 execute 的 detail;登记件解析输入,非成败
        # 回执——端口无返回,摘经由本属性旁路供 on_outcome detail)。
        self.last_detail: str = ''
        # 出战点击事实(出战域重设计收缩语义,T-286):True = StartBattleOp
        # 点击序列已执行(含弹窗确认);False = 找不到按钮/area 缺失等
        # 未执行形态。消费方 = cw_loop 发射核(launch_prepared_battle 返回
        # 值旁路)。getattr 容缺(__new__ 桩形态)。
        self.last_launch_ok: bool | None = None
        # StartBattleOp 上报的免战跳过子态标记(op 写 env.skip_substate,
        # dispatch 后由本 runner 读取一次,只进回执 extra 留证——递减本体
        # = op 自上报)。getattr 容缺(__new__ 桩形态)。
        self._last_skip_substate: bool = False
        # 执行点金差显影(备战执行缝账务包络;写点 = execute 每次
        # 入口复位)。取值时机 = dispatch 后由 _executed_gold_delta 现算
        # 写入,None = 该动作执行点金差不可推算(诚实缺失,非 0);消费方
        # = 回执 extra 金差键与观察侧备战帧金对账。getattr 容缺
        # (__new__ 桩形态,execute 入口显式复位不依赖构造)。
        # (CwActionLevelUpParam 金腿已随批2b 翻转切 action.cost 直写——
        # apply_prep_action_logic 单一写点,本执行缝对 CwActionLevelUpParam 恒 0。)
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
        CW_ACTION_TYPES);② 静态可判参数(槽位越界/row 枚举)。席位域
        动作坐标系 = 容器槽位表下标 0 基
        (词表模块头声明);机械动作 row/slot = 画面物理槽位 1 基。
        """
        if not isinstance(action, CW_ACTION_TYPES):
            return f'未知动作类型 {type(action).__name__}(不在动作全集,§4)'
        if isinstance(action, CwActionSellBenchParam):
            if not (0 <= action.bench_idx < len(self._bench_pts)):
                return (f'CwActionSellBenchParam bench_idx={action.bench_idx} 越界'
                        f'(0-{len(self._bench_pts) - 1})')
        elif isinstance(action, CwActionSellDeployedParam):
            n = DEPLOYED_CAPACITY
            if not (0 <= action.deployed_idx < n):
                return f'CwActionSellDeployedParam deployed_idx={action.deployed_idx} 越界(0-{n - 1})'
        elif isinstance(action, CwActionDeployMoveParam):
            if not (0 <= action.bench_idx < len(self._bench_pts)):
                return (f'CwActionDeployMoveParam bench_idx={action.bench_idx} 越界'
                        f'(0-{len(self._bench_pts) - 1})')
            if action.to_row not in ('front', 'back'):
                return f'CwActionDeployMoveParam to_row={action.to_row!r} 非法(front/back)'
        elif isinstance(action, CwActionCollectOreParam):
            if not action.points:
                return 'CwActionCollectOreParam 载荷为空(挑选归决策侧 kernel,空载荷 = 无对象)'
            if len(action.points) > ORE_CLICK_HARD_CAP:
                return (f'CwActionCollectOreParam 载荷 {len(action.points)} '
                        f'超硬上限 {ORE_CLICK_HARD_CAP}(挑选越权)')
        elif isinstance(action, CwActionOpenBoxParam):
            if action.slot is not None and not (1 <= action.slot <= len(self._bench_pts)):
                return f'CwActionOpenBoxParam slot={action.slot} 越界(1-{len(self._bench_pts)})'
        elif isinstance(action, CwActionOpenTomeParam):
            if action.slot is not None and not (1 <= action.slot <= len(self._bench_pts)):
                return f'CwActionOpenTomeParam slot={action.slot} 越界(1-{len(self._bench_pts)})'
        elif isinstance(action, CwActionOpenBookcardParam):
            if action.slot is not None and not (1 <= action.slot <= len(self._bench_pts)):
                return f'CwActionOpenBookcardParam slot={action.slot} 越界(1-{len(self._bench_pts)})'
        elif isinstance(action, CwActionWearEquipParam):
            if action.row not in ('front', 'back'):
                return f'CwActionWearEquipParam row={action.row!r} 非法(front/back)'
            n = len(self._front_pts if action.row == 'front' else self._back_pts)
            if not (1 <= action.slot <= n):
                return f'CwActionWearEquipParam slot={action.slot} 越界(1-{n})'
        elif isinstance(action, (CwActionFurnaceUseParam, CwActionPrivilegeCardUseParam)):
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
        elif isinstance(action, CwActionObsParam):
            # scope 值域闭集校验(单一源 = cw_vocab.OBS_SCOPES;outer_loop
            # 口径在决策循环 F3 之前拦截,到不了这里——这里只拦 in_place
            # 路径的拼错值)。
            if action.scope not in OBS_SCOPES:
                return (f'CwActionObsParam scope={action.scope!r} 非法'
                        f'(值域闭集 OBS_SCOPES)')
        elif isinstance(action, (CwActionWrenchUseParam, CwActionPrecisionWrenchUseParam,
                                CwActionStaffProjectorUseParam, CwActionPerfectProjectorUseParam,
                                CwActionLuckyTokenUseParam)):
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

        ⚠️ W209j 刹车(纵深防御第二层):运行中被停 → 拒绝
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
                     '(W209j 刹车)', type(action).__name__)
            raise StopBrakeShortCircuit('已停止[W209j刹车]')
        # 执行点金差显影账每动作复位:上动作余量禁跨动作残留。
        # 落地门前捕获备战席占用(tracked 账现读):S1 路径 (ii) 翻正判读
        # 需要 pre/post 两点,post 点必须在 dispatch 之后读(dispatch 内
        # 卖出/部署 handler 会同步销账)。
        _pre_bench = self._bench_tracked_count()
        # 卖出对象 dispatch 前快照(执行点金差供给;dispatch 内 tracked
        # 已同步移除,事后复查恒落空)。
        _pre_sell_bc = self._pre_sell_tracked_bc(action)
        # 免战跳过子态标记每动作复位(上动作残留禁跨动作流入;op 上报经
        # _dispatch_action 写入,回执 extra 消费)。
        self._last_skip_substate = False
        detail, emitted = self._dispatch_action(action)
        self.last_detail = detail
        gold_delta = self._executed_gold_delta(action, emitted, _pre_sell_bc)
        self.last_gold_delta = gold_delta
        # (卖出回金的容器唯一写点 = 卖出 op 自上报
        #  (report_action_sell_*_param),防双记——执行缝与投影双腿各记
        #  一次的实机倒挂实证归 git。本处 gold_delta 仅进回执 extra 留证。)
        _gold_extra = ({'gold_delta': int(gold_delta)}
                       if gold_delta not in (None, 0) else None)
        if isinstance(action, CwActionStartBattleParam) and self._last_skip_substate:
            # 跳过子态标记进回执 extra(上报动作事实的遥测面;递减本体 =
            # op 自上报,回执只留证)。
            _gold_extra = {**(_gold_extra or {}), 'skip_substate': True}
        self._note_action_receipt(action, emitted, detail, extra=_gold_extra)
        if isinstance(action, CwActionStartBattleParam):
            # 出战点击事实(出战域重设计,T-286):真执行链 = 注册表分派
            # CwActionStartBattleOp 点击序列,round 结果成功态即发出事实
            # (round_fail = 找不到按钮/area 缺失,design.md §1.1);
            # 执行缝(假环境)不经真分派 = applied 真值(F11 双轨申报)。
            self.last_launch_ok = emitted
        if emitted:
            # S1 清键门(唯一写点 = mandate.mark_s1_route_
            # check,三路径封闭枚举)。批3a 跨批对齐写死:``landed`` 供给
            # 改观察侧 reconcile 落地事实(接口本批定、批5 E1 落地供给),
            # 过渡期恒传 False = fail-closed(宁「该清不清」不「乱清」,
            # 后者可无限重复——交替活锁形态;「该清不清」侧 wanted 滞留
            # 一拍自愈,非正确性损害,mandate docstring 在案)。部署类
            # (CwActionDeployMoveParam)(i)-deploy_launch 路径过渡期不清,防线语义
            # (no-op 不清)完整存活。发射位只读不写的同型纪律在此不适用
            # ——本门消费「已落地」事实,发射侧天然无此事实(猎点 8)。
            # CwActionOpenShopParam 分支不经本执行器(cw_screen_prep 流程层编排),开店
            # 落地不触清键面,与其置位语义(商店决策访问位)自洽。
            try:
                from sr_od.application.currency_war.kernel.cw_game_state import (
                    gs_of_ctx,
                )
                from sr_od.application.currency_war.strategies.impl.mandate_v1.mandate import (
                    mark_s1_route_check,
                )
                _m = self._ctx.cw_match
                _sess = _m.session if _m is not None else None
                if _sess is not None:
                    mark_s1_route_check(
                        _sess, gs_of_ctx(getattr(self, "ctx", None), _sess), action,
                        pre_bench_count=_pre_bench,
                        post_bench_count=self._bench_tracked_count(),
                        landed=False)
            except Exception as e:  # noqa: BLE001  记账失败不阻塞执行
                log.warning('[cw][s1-route] 清键门失败(不阻塞): %s', e)
        # (动作逻辑效果推进已随动作 op 重组批③ 收编进各 op 自上报
        #  (op 内直调自己的上报函数,design.md §1.1):原执行器
        #  apply_op_effect 调用删除 = 双记防线——op 已写,本处再写即双记。)
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
        - journal 常开(R5 W1 影子闸折叠)回执写入无条件;无局
          (session 缺)跳过;best-effort 不阻塞动作链。
        """
        try:
            from sr_od.application.currency_war.kernel.cw_game_state import (
                game_state_from_ctx,
                note_action_receipt,
            )
            gs = game_state_from_ctx(self._ctx)
            if gs is None:
                return
            note_action_receipt(
                gs, op=type(action).__name__, applied=bool(emitted),
                reason='' if emitted else detail, detail=detail,
                screen=SCREEN_NAME, actor=type(self).__name__, extra=extra)
        except Exception as e:  # noqa: BLE001  回执失败不阻塞执行
            log.warning('[cw][receipt] 动作回执写入失败(不阻塞): %s', e)

    def _pre_sell_tracked_bc(self, action: CwAction) -> Unit | None:
        """卖出对象 dispatch 前 tracked 快照(执行点金差供给;卖出外
        动作 = None)。

        [索引定义] CwActionSellBenchParam.bench_idx / CwActionSellDeployedParam.deployed_idx =
        容器槽位表下标 0 基(tracked 表 = 同构下标表,恒定长 9/10,
        )——按下标直接对位,零换算。取值时机 = execute()
        内 dispatch **前** tracked 账现读(卖出 handler 在 dispatch 内
        同步销账,dispatch 后按 tracked 复查恒落空);消费 = dispatch 后
        _executed_gold_delta 一次读用,不跨动作存活。P1 tracked 形状:
        bench 侧 = BenchSlot(kind='unit' → 内嵌 Unit;占位件无角色身份
        → None,占位件槽无角色身份)/ deployed 侧 = Unit。
        tracked 不可读(无局/形状异常)= None(金差诚实缺失,观察覆盖
        兜底)。
        """
        if not isinstance(action, (CwActionSellBenchParam, CwActionSellDeployedParam)):
            return None
        try:
            match = self._ctx.cw_match
            session = match.session if match is not None else None
            if session is None:
                return None
            _books = gs_of_ctx(getattr(self, "ctx", None),
                               session).tracked_books
            if isinstance(action, CwActionSellBenchParam):
                tracked = _books.bench or []
                if not (0 <= action.bench_idx < len(tracked)):
                    return None
                _s = tracked[action.bench_idx]
                if _s is None or getattr(_s, 'kind', None) != 'unit':
                    return None
                return _s.unit
            tracked = _books.deployed or []
            idx = action.deployed_idx
            return tracked[idx] if 0 <= idx < len(tracked) else None
        except Exception:   # noqa: BLE001  观测容缺,不阻塞执行链
            return None

    def _executed_gold_delta(self, action: CwAction, emitted: bool,
                             pre_sell_bc) -> int | None:
        """执行点金差显影(备战执行缝账务包络):gold 域备战动作在
        机械半边发出时点的金变化量。

        公式单一源与边界:
        - ``CwActionSellBenchParam``/``CwActionSellDeployedParam`` = +sell_refund(星×招募费;对象 =
          dispatch 前快照,费单一源 = kernel ``bench_char_cost``——与容器
          上报函数(report_action_sell_*)同式;身份不可辨 = None 诚实
          缺失,不做保守估值假账,观察覆盖兜底);
        - ``CwActionLevelUpParam`` = 0(批2b 翻转:金腿切 ``action.cost`` 直写,唯一
          写点 = 买经验自上报(report_action_level_up_param);原执行缝金差
          ``_last_levelup_spent`` 通道随翻转退役,防双记);
        - ``CwActionCollectOreParam`` = None(晶矿金通道随机,执行点不可推算——声明
          盲区,观察覆盖兜底,禁拍值);
        - 其余动作 = 0(发出零金动);未发出 = None(无金动无账)。
        ``None`` 与 0 的消费语义:仅非 None 非 0 进回执 extra 金差键
        (回执留证);**容器金账不经本值直推**——统一观察对账迭代
        (2026-09-16 归因批)退役执行缝直推腿,卖出/花金容器唯一写点 =
        卖出自上报(report_action_sell_*),防双腿双记(实机 −2 倒挂
        实证)。None = 该动作本拍金账留观察覆盖。
        """
        if not emitted:
            return None
        if isinstance(action, (CwActionSellBenchParam, CwActionSellDeployedParam)):
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
        if isinstance(action, CwActionCollectOreParam):
            return None
        return 0

    def _dispatch_action(self, action: CwAction) -> tuple[str, bool]:
        """动作分派(动作 op 重组批③:经注册表类级解析 + (ctx, param,
        env) 组装新壳 op ``CwActionXxxOp(SrOperation)``,执行取 round
        结果;design.md §1.3)。

        返回 ``(机械执行摘要, 是否实际发出)``。emitted = round 结果成功态
        (``round_success`` = 已发出;``round_fail`` = 定位失败等未发出
        通道,零重试即失败交回)。机械摘要 = round 结果 status。词表外
        类型 = 注册表 AssertionError 响亮暴露(生产不可达:F3 validate
        先拒)。
        """
        from sr_od.application.currency_war.operations.cw_op.cw_action_registry import (
            action_op_class_for,
        )
        env = PrepExecEnv(op=self._op, match=self._ctx.cw_match, config=None,
                          executor=self)
        op = action_op_class_for(action)(self._ctx, action, env=env)
        # 直调节点函数(单节点 op;不走 Operation.execute() 循环:重试/
        # 超时/停机查归本 runner 包络与交回面所有,动作层零重试语义——
        # 节点异常原样上抛 = 执行异常通道不变)
        result = op.run()
        if isinstance(action, CwActionStartBattleParam):
            # 免战跳过子态标记转发(op 写 env.skip_substate;递减本体 =
            # op 自上报,回执 extra 留证消费;getattr 容缺 = 桩 env 形态)
            self._last_skip_substate = bool(getattr(env, 'skip_substate',
                                                    False))
        return (result.status or ''), bool(result.is_success)

    # ===== 奖励域 =====

    def _collect_ore(self, action: CwActionCollectOreParam) -> tuple[str, bool]:
        """薄委托(体已迁 ``cw_collect_ore_action.CwActionCollectOreOp``,统一
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
            tracked = gs_of_ctx(getattr(self, "ctx", None), match.session).tracked_books.bench
            return sum(1 for bc in tracked if bc is not None)
        except Exception:   # noqa: BLE001  观测 best-effort
            return -1

    def _open_box(self, action: CwActionOpenBoxParam) -> tuple[str, bool]:
        """薄委托(体已迁 ``cw_open_box_action.CwActionOpenBoxOp``;批3 体迁 +
        薄委托,替身缝保留)。终结动作(R7):交回等待 = CwActionOpenBoxOp.
        terminal_wait(与 _OVERLAY_ANIM_WAIT_S 等价,等价锁在册)。"""
        return self._dispatch_action(action)

    def _open_tome(self, action: CwActionOpenTomeParam) -> tuple[str, bool]:
        """薄委托(体已迁 ``cw_open_tome_action.CwActionOpenTomeOp``;批3 体迁 +
        薄委托,替身缝保留)。"""
        return self._dispatch_action(action)

    def _open_bookcard(self, action: CwActionOpenBookcardParam) -> tuple[str, bool]:
        """薄委托(体已迁 ``cw_open_bookcard_action.CwActionOpenBookcardOp``;批3
        体迁 + 薄委托,替身缝保留——测试直调面沿此缝)。"""
        return self._dispatch_action(action)

    # ===== 席位域 =====

    def _sell_bench(self, action: CwActionSellBenchParam) -> tuple[str, bool]:
        """薄委托(体已迁 ``cw_prep_sell_bench_action.CwActionSellBenchOp``;
        批3 体迁 + 薄委托,替身缝保留)。"""
        return self._dispatch_action(action)

    def _sell_deployed(self, action: CwActionSellDeployedParam) -> tuple[str, bool]:
        """薄委托(体已迁 ``cw_sell_deployed_action.CwActionSellDeployedOp``;批3
        体迁 + 薄委托,替身缝保留)。"""
        return self._dispatch_action(action)

    def _deploy_move(self, action: CwActionDeployMoveParam) -> tuple[str, bool]:
        """薄委托(体已迁 ``cw_deploy_move_action.CwActionDeployMoveOp``;批3 体迁
        + 薄委托,替身缝保留)。"""
        return self._dispatch_action(action)

    # ===== 装备/工具原子域(R2 穿戴 / R8 工具按消耗品各立类;机械原语
    #       _equip_slot_drag_point/_owned_grid_locate
    #       留守本 runner,体迁 op 经 env.executor 消费)=====

    def _equip_slot_drag_point(self, row: str, slot: int) -> Point | None:
        """(row, slot) → avatar 拖拽点(与同文件拖点派生式同构:rect 中心
        x + y1+21;前排 = 前排-N rect 中心 x + y1+21(D-36 校准),后排 =
        布局选档前缀(select_back_layout 单一入口)同式派生)。缺失 → None
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
        from sr_od.application.currency_war.obs.cw_equipment import (
            ensure_equip_sift_templates,
            read_equips,
        )
        templates = ensure_equip_sift_templates(self._ctx)
        if templates is None:
            return None
        rect = _area_rect(self._ctx, '区域-道具装备', SCREEN_NAME)
        if rect is None:
            return None
        hits = read_equips(self._op.screenshot(), templates,
                           equip_rect=(rect.x1, rect.y1, rect.x2, rect.y2))
        entry = next(((n, p) for n, p, _ in hits if n == item_name), None)
        return Point(entry[1][0], entry[1][1]) if entry is not None else None

    def _wear_equip(self, action: CwActionWearEquipParam) -> tuple[str, bool]:
        """薄委托(体已迁 ``cw_wear_equip_action.CwActionWearEquipOp``;批3 体迁 +
        薄委托,替身缝保留)。"""
        return self._dispatch_action(action)

    def _use_tool(self, action: CwAction) -> tuple[str, bool]:
        """薄委托(体已迁 ``cw_tool_use_action.ToolUseOp``,工具原子七类
        共用;批3 体迁 + 薄委托,替身缝保留)。"""
        return self._dispatch_action(action)

    def _drag(self, src: Point, dst: Point) -> None:
        """统一拖拽原语(DragCwChar.drag_char:中心拖+hold0;机械执行,
        源槽像素验重试已拆除)。

        r10 review#2:失焦守卫下沉到本原语(所有拖拽路径共享)——窗口后台化时
        拖拽输入静默丢(r9 实证同机制:截图正常/输入丢/连环「源槽未变」假失败),
        拖前验焦点,失焦先激活。
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
        """卖出后备势跟踪同步(tracked 主账 = tracked_books.bench)。

        [索引定义] bench_idx = bench 槽位表下标 0-8(与动作字段同系);
        摘除 = 按下标置 None(权威槽位 = 下标,定长 9 保洞契约 ;
        旧紧凑重排会累积重复槽号——实机缺陷台账 slots=[1,3,4,5,6,7,8,9,9]
        等 4 局实证,保洞治本)。"""
        match = self._ctx.cw_match
        if match is None or match.session is None:
            return
        _books = gs_of_ctx(getattr(self, "ctx", None),
                           match.session).tracked_books
        tracked = list(_books.bench or [])
        _expose_unhealthy_tracked_slots(tracked)
        if 0 <= bench_idx < len(tracked):
            tracked[bench_idx] = None   # 置 None 不移位(保洞契约)
        _books.bench = tracked

    def _track_remove_deployed(self, row: str, slot: int) -> None:
        """卖场上后备势跟踪同步(tracked 主账 = tracked_books.deployed)。

        [索引定义] tracked deployed = 定长 10 下标表,下标 = deployed_idx
        恒稳;物理 (row, slot) → 下标换算单一函数 = deployed_idx_of
        (执行坐标边)。下标即权威(§2.1 排归属由下标派生),旧信息位
        position_pref 复核随形退役(下标写入天然行内一致)。"""
        match = self._ctx.cw_match
        if match is None or match.session is None:
            return
        from sr_od.application.currency_war.kernel.cw_exec_state import (
            deployed_idx_of,
        )
        _books = gs_of_ctx(getattr(self, "ctx", None),
                           match.session).tracked_books
        tracked = list(_books.deployed or [])
        idx = deployed_idx_of(row, slot)
        if 0 <= idx < len(tracked) and tracked[idx] is not None:
            tracked[idx] = None
        _books.deployed = tracked

    def _track_move_deployed(self, bench_idx: int, to_row: str, to_slot: int) -> None:
        """上阵后备势跟踪同步:bench 条目 → deployed 条目(载荷落位直写)。

        [索引定义] bench_idx = bench 槽位表下标 0-8(tracked 行按下标
        对位,保洞);to_slot = 载荷落位排内 1 基画面槽号(发射位生成期
        快照透传;tracked 写入下标 = ``deployed_idx_of(to_row, to_slot)``
        换算单一源,与执行拖点/容器写侧同源,单位槽号信息位 = to_slot)。
        bench 侧摘除 = 按下标置 None(保洞,同 _track_remove_bench)。

        拖拽语义镜像(游戏规则):目标槽空 = 放置;有人 = 交换——被占位
        单位回源 bench 槽(与容器写侧/``CwActionSwapDeployParam`` 换位
        契约同语义,装备随单位对象自然随行);禁静默换槽(不另寻空位),
        载荷槽越出定长表或跨排 = 不写(陈旧载荷,交观察对账)。"""
        match = self._ctx.cw_match
        if match is None or match.session is None:
            return
        from dataclasses import replace

        from sr_od.application.currency_war.kernel.cw_exec_state import (
            DEPLOYED_CAPACITY,
            deployed_idx_of,
            deployed_slot_no,
        )
        from sr_od.application.currency_war.kernel.cw_game_state import (
            BenchSlot,
        )
        _gs = gs_of_ctx(getattr(self, "ctx", None), match.session)
        _books = _gs.tracked_books
        tracked = list(_books.bench or [])
        _expose_unhealthy_tracked_slots(tracked)
        # tracked deployed = 定长 10 下标表;载荷 (to_row, to_slot) 经换算
        # 单一源直写下标(拖点同源;目标有人 = 交换,被占位者回源槽)。
        # 载荷槽非法 = 整笔不写(bench 摘除也不做,防陈旧载荷把单位写出账)。
        slot_no = int(to_slot)
        idx = deployed_idx_of(to_row, slot_no)
        if not (0 <= idx < DEPLOYED_CAPACITY) \
                or deployed_slot_no(idx) != slot_no:
            return
        moved = None
        if 0 <= bench_idx < len(tracked):
            _s = tracked[bench_idx]
            if _s is not None and getattr(_s, 'kind', None) == 'unit' \
                    and _s.unit is not None:
                moved = _s.unit
                tracked[bench_idx] = None   # 置 None 不移位(保洞契约)
        dep = list(_books.deployed or [])
        while len(dep) < DEPLOYED_CAPACITY:
            dep.append(None)
        if moved is not None:
            _occ = dep[idx]
            dep[idx] = replace(moved, slot=slot_no)
            if _occ is not None:
                tracked[bench_idx] = BenchSlot(
                    kind='unit',
                    unit=replace(_occ, slot=bench_idx + 1))
        _books.bench = tracked
        _books.deployed = dep

    # ===== 商店域 =====

    def _level_up(self, action: CwActionLevelUpParam | None = None) -> tuple[str, bool]:
        """薄委托(体已迁 ``cw_prep_level_up_action.CwActionLevelUpOp``;批3
        体迁 + 薄委托,替身缝保留)。

        ``action`` 形参 = 注册表分派载体(原签名无参——单击体不读动作
        字段;缺省补零价占位实例仅作类型解析,行为零变化)。"""
        return self._dispatch_action(
            action if action is not None else CwActionLevelUpParam(cost=0))

    # ===== 战斗域 =====
    # StartBattleOp 现体 = 点击出战和弹窗(零判效,点击序列已执行语义);
    # 本入口保留薄委托替身缝,返回序 (ok, detail)。

    def _start_battle(self) -> tuple[bool, str]:
        """薄委托(体已迁 ``cw_start_battle_action.CwActionStartBattleOp``;批3
        体迁 + 薄委托,替身缝保留)。"""
        detail, emitted = self._dispatch_action(CwActionStartBattleParam())
        return emitted, detail



