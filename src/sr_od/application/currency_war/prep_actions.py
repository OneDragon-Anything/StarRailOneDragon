"""货币战争 备战决策环 执行器(P1;strategy/03 §13)。

框架层:本模块**不含玩法判断**(何时收晶矿/卖谁/何时出战 = 策略层 CwStrategy.decide_prep_screen),
只负责「机械执行一个动作」(用户裁定:动作 op 只管机械执行,
禁止做任何验证——点击/拖拽后不读屏判「是否生效」,落地判定完全归观察侧
reconcile 对账;执行回执 ``(progressed, detail)`` 已停用,
``execute`` 无返回,发出即职责完成)。失败路径(§13.2 修订):
- 参数非法 → 对应动作 op 内守卫断言 AssertionError(集中式 validate
  已退役进各 op,flow/action_ops.md §1 决策侧参数现算契约;异常上抛
  通道 = 执行异常同款);
- 执行前输入契约拒绝(晶矿/箱/按钮等目标不在,执行前观察,M6 边界面)→
  本动作未发出,机械部分完成后返回主循环重观察重决策;
- 执行异常 → 异常上抛(Director 上抛 = 本环 fail,外层 op retry 接管)。

slot 语义(unified-action-factory 统一后):席位域动作(CwActionSellBenchParam/
CwActionSellDeployedParam/CwActionMoveUnitParam)携**状态容器槽位表下标**(0 基,词表单一源 =
kernel/cw_vocab,坐标系裁定见其模块头);本执行器 = **执行坐标边**——
状态容器下标 → screen_info 槽位中心的换算单点(bench 侧 = 备战栏-N area 序
直取;deployed 侧 = 下标→(排,排内槽号)固定双射内联算术,0-3=前排
1-4 / 4-9=后排 1-6;tracked 第二账停用后旧换算族已删)。坐标参数化
机械动作(CwActionWearEquipParam/工具原子类/CwActionOpenBoxParam/CwActionOpenTomeParam/CwActionOpenBookcardParam)的
row/slot 字段 = 画面物理排槽位 1 基(动作参数定义,拖点直取 area,
不经换算)。
统一动作工厂并入:动作级
机械执行体已逐字迁入 ``operations/cw_op/`` 备战 op 类(一 op 一文件),
分派改查单一注册表 ``action_op_for``(_dispatch_action);本模块保留
runner 包络(刹车/回执登记与机械原语)与薄委托族(替身函数的接缝(stub seam):八桩零调用
已删,``_open_bookcard`` 因单帧测试直调面保留)。
"""
from __future__ import annotations

import time
from dataclasses import dataclass

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_obs_core import (
    SCREEN_NAME,
    _area_rect,
    area_center,
)
from sr_od.application.currency_war.kernel.cw_vocab import (
    CwAction,
    CwActionLevelUpParam,
    CwActionOpenBookcardParam,
    CwActionStartBattleParam,
)
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation

#: overlay 弹出/关闭的固定动画等待(等待归产生动画的操作)。
#: 值依据:单局耗时审计报告
#: .debug/temp/currency_war/w417_duration_audit/REPORT.md
#: 「需验证·出战链」的最坏耗时上界(判效已拆,用户裁定动作 op 只机械
#: 执行);弹窗就位与否交下一帧观察。
_OVERLAY_ANIM_WAIT_S: float = 1.8

#: 商店收起动画时长(操作完成自等动画;实测口径 screen_flow_timing
#: #15「收起过场动画 ~1s 即备战画面稳定」,用户口述。op 完成后显式等待,替代
#: 测量驱动 gate——画面状态判断已外移建档识别层,等待时长归产生动画的操作声明)。
SHOP_CLOSE_ANIM_S: float = 1.0
#: 商店打开动画时长(固定时长自等;用户口述定值 2026-09-02「干净的备战
#: 里打开商店,只要等 1 秒就够了」。开态判定由下一帧观察侧 0n 三个识别标志承载。
#: 自动开店场景不经此处——cw_loop 备战分支按「备战阶段」识别)。
SHOP_OPEN_ANIM_S: float = 1.0
#: 穿戴拖前固定等待(等备战面板/上件 reflow 动画收尾,非判效)。取值 =
#: 被替换的稳帧轮询典型检测档 0.3s 向上取整(与 pick 确认 0.6-1.2s 固定
#: 等待族同量级);后随动作的动画由拖后固定等待覆盖,极端 reflow 未收尾
#: 致按压抓空 = 未发出形态,由下一入口观察对账暴露 + 决策环自然重派
#: (按「不存在偶发丢失」纪律查根因调常量,禁恢复轮询)。
PREP_DRAG_SETTLE_WAIT_S: float = 0.5


# ============================================================ 回执受阻码(统一口 round_fail status 闭集映射)

#: round_fail status 前缀 → 回执受阻码(闭集映射;词表暂住本表,权威版本家 =
#: game_state/fields.md 回执契约节)。表项 = (status 前缀, 受阻码):
#: 受阻码自带族前缀——``未执行:`` = 点击前失败(定位缺失/无对象/
#: 输入契约拒绝,动作没发出)。映射键 = 各动作 op round_fail status 的
#: 首段字面前缀(status 由 op 固定字面量产出);**新 round_fail status
#: 必须同步登记本表**——漏登走 :func:`_prep_receipt_block_code` 原文
#: 兜底(受阻事实不静默,复盘以原样 status 在日志里暴露促登记)。特定前缀先于
#: 泛化前缀(表序 = 匹配序,首中即返)。
#: (terminal-fail-status 迭代收缩:参数违法类三口(BuyCard 槽解析/槽号
#: 越界、DeployMove 落位越界)改 op 内守卫断言、建档缺失类检查段
#: (LevelUp/StartBattle 主口与弹窗/WearEquip 槽位坐标)删除 = 自然
#: 异常报错——上述形态零 round_fail 供给,对应映射行随批退役;
#: ``未生效:*`` 族(StartBattle 弹窗收尾)随之零供给退役。开件三动作
#: (箱/典籍/书册卡)执行前识别读门随状态容器槽位直点形态拆除:判空 fail
#: (无简易武装箱/无秘密典籍/无书册卡)零 round_fail 供给,映射行退役
#: ——状态容器陈旧「件不在」的治理归观察对账域,非动作 op 失败分支。)
_PREP_RECEIPT_BLOCK_CODES: tuple[tuple[str, str], ...] = (
    # —— 出战(点击前):按钮定位失败 = 动作没发出 ——
    ('未执行:找不到按钮', '未执行:定位缺失(按钮-出战)'),
    ('area 缺失:按钮-出战', '未执行:定位缺失(按钮-出战)'),
    ('area 缺失:按钮-跳过', '未执行:定位缺失(按钮-跳过)'),
    # —— 穿戴/工具原子:owned 网格定位失败(拖拽前,现读落空族)——
    ('owned 网格未定位到工具', '未执行:定位缺失(工具)'),
    ('owned 网格未定位到目标件', '未执行:定位缺失(目标件)'),
    ('owned 网格未定位到', '未执行:定位缺失(owned 网格)'),
)


def _prep_receipt_block_code(status: str) -> str:
    """round_fail status → 回执受阻码(闭集映射单一源
    = :data:`_PREP_RECEIPT_BLOCK_CODES`)。

    未登记 status = 原文兜底(``未执行:<status>``):机械事实
    「没发出」由 round_fail 通道保证,受阻细节以原样 status 进子码槽
    不丢真;出现兜底形态 = 词表漏登,登记义务见词表注释。
    """
    for prefix, code in _PREP_RECEIPT_BLOCK_CODES:
        if status.startswith(prefix):
            return code
    return f'未执行:{status}'


class StopBrakeShortCircuit(RuntimeError):
    """停机短路异常(纵深防御第二层)。

    语义 = 运行中被停 → 拒绝执行任何动作(run 27 实证:director 环在
    Deploy 钩子 stop_running 后仍发 CwActionStartBattleParam 点出战——环顶检查(第一层)
    之外,本入口兜底覆盖绕环路径)。表达 = 本异常:执行器抛出,
    调用方(cw_screen_prep 决策环 / cw_loop 动作发出核)捕获后返回主循环,
    下轮 loop 顶见 STOP 退出。判据 = last_run_result 非空(start 清
    None/stop 写入;run_state STOP 是 idle 初始态不能直接用)。
    """


def row_area_centers(ctx: SrContext, prefix: str,
                     screen_name: str = SCREEN_NAME) -> list[Point]:
    """从 screen_info 读全部 prefix-N 区域中心(N 升序)。

    逐区现读、不硬编码(后排 >6 时 screen_info 补区后自动跟上);
    prep_actions 执行器 / cw_screen_prep 观察共用。``screen_name`` =
    坐标权威画面(缺省备战画面;商店域传商店开画面——底栏 area
    商店画面档自备,跨屏坐标不共用文件)。
    """
    si = ctx.screen_loader.get_screen(screen_name)
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


def sell_point(ctx: SrContext, screen_name: str = SCREEN_NAME) -> Point:
    """出售区落点(单一源):screen_info「区域-出售区」中心
    (游戏机制 = 拖到左下区域即出售,无按钮)。

    ``screen_name`` = 坐标权威画面(缺省备战画面;商店域传商店开画面)。
    area 缺失 = 建档漂移/档案损坏 → RuntimeError 显式上抛(信息带 area
    名),禁回退硬编码坐标静默点击(坐标单一真相源)。消费面含
    卖上阵 off-target 拖拽,落点直入 drag 原语 → None 不可流入,
    直取 + 上抛是唯一兼容形态。
    """
    pt = area_center(ctx, '区域-出售区', screen_name=screen_name)
    if pt is None:
        raise RuntimeError(
            f'area 缺失:区域-出售区({screen_name}),出售区落点不可派生,禁兜底坐标')
    return pt


def drag_bench_to_sell(op: SrOperation, ctx: SrContext, bench_idx: int,
                       screen_name: str = SCREEN_NAME) -> None:
    """拖备战槽(槽位下标 0-8)→ 出售区(共享卖原语,设计章 2.10)。

    d2 卖通道生产接入调用(shop.py prefix 循环 CwActionSellBenchParam 分支)与 prep_actions
    ``_sell_bench`` 共用本 helper:「拖→出售区」机械一段(拆源槽
    像素验重试:发出即职责完成,落地事实归观察侧 reconcile 对账);
    tracking 同步由调用方各自做。失焦守卫同 ``PrepActionExecutor._drag``
    语义(窗口后台化时拖拽输入静默丢,r9 实证)。

    Args:
        op: 调用方 op(取 ctx.controller 操作)。
        ctx: SrContext。
        bench_idx: 槽位下标 0-8(列表下标 = 物理备战栏槽位 1-9 减一);
            越界 = 调用方 bug,响亮上抛(守卫非判效)。
        screen_name: 拖拽两端的坐标权威画面(缺省备战画面;商店域
            传商店开画面——该画面档自备 备战栏/出售区 area)。
    """
    from sr_od.application.currency_war.sim.cw_sim_ports import (
        sim_backend_installed,
    )
    if sim_backend_installed():
        # sim 模式:机械执行分支(焦点守卫+真实拖拽)静默成功,自上报照走
        # (直连 controller 旁路 port 检查;落位事实由后端状态副本承接)
        return
    pts = row_area_centers(ctx, '备战栏', screen_name=screen_name)
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
    DragCwChar.drag_char(op, pts[bench_idx], sell_point(ctx,
                                                        screen_name=screen_name))


# (装备穿戴计划构造单一源 = kernel/cw_equip_wear_plan(原子通路);
#  动作发出点(mandate M7)直接消费同一构造函数,无第二源。)
# (tracked 写点槽号健康暴露 _expose_unhealthy_tracked_slots 已随
#  tracked 第二账停用而删除:其两个调用点均为 tracked 摘除分支,分支删则
#  helper 无消费面;状态容器形槽号 = 下标权威结构性健康。)


@dataclass
class PrepExecEnv:
    """备战动作 op 执行环境(域依赖结构化包)。

    域依赖结构化包,op 构造时传入(原 execute 时刻注入改为构造时)。
    ``executor`` = 备战 runner 包络引用(坐标槽位表/机械原语/tracked 账
    同步的单一宿主;op 体经此消费,执行包络留在 runner)。``detail`` =
    prep 域遗留旁路字段(机械执行摘要,字段值不再被包络消费);发出
    事实归 round 结果成功态(executor 局部派生,不经 env 字段承载);
    ``skip_substate`` 仍被包络消费(回执 extra 保留证据)。
    """

    op: SrOperation
    match: object            # CurrencyWarMatch(避免运行时导入环,注解宽松)
    config: object = None    # 协议公共面(备战动作执行面零 config 消费)
    executor: PrepActionExecutor | None = None
    detail: str = ''
    # 免战跳过子态标记(StartBattleOp 上报通道;op 写、runner 包络
    # _dispatch_action 读一次转发 game state 上报路径。False = 常规出战)
    skip_substate: bool = False


class PrepActionExecutor:
    """备战原子动作执行器(框架层;持 ctx + 宿主 op 复用截图/区域匹配/拖拽原语)。

    宿主 op = CwScreenPrep(SrOperation);机械执行(点击/拖拽/等待),落地
    判定归观察侧 reconcile(用户裁定);拖拽统一走
    DragCwChar.drag_char(中心拖 + hold0,2026-08-13 实测验证)。
    """

    def __init__(self, op: SrOperation, ctx: SrContext) -> None:
        self._op = op
        self._ctx = ctx
        # 机械执行摘要(最近一次 execute 的 detail;登记件解析输入,非成败
        # 回执——端口无返回,摘经由本属性旁路供 on_outcome detail)。
        self.last_detail: str = ''
        # 出战点击事实(出战域重设计收缩语义):True = StartBattleOp
        # 点击序列已执行(含弹窗确认);False = 找不到按钮/area 缺失等
        # 未执行形态。消费方 = cw_loop 动作发出核(launch_prepared_battle 返回
        # 值旁路)。getattr 容缺(__new__ 桩形态)。
        self.last_launch_ok: bool | None = None
        # 最近一次分派的动作 op round 结果(QC 终结口失败透传的取数口;
        # 逐分派覆盖 = 恒本拍动作,防上拍残留误透传)。消费方 =
        # cw_screen_prep._act_execute_default 终结口入参;非终结动作
        # 零消费。getattr 容缺(__new__ 桩形态)。
        self.last_round_result: OperationRoundResult | None = None
        # StartBattleOp 上报的免战跳过子态标记(op 写 env.skip_substate,
        # dispatch 后由本 runner 读取一次,只进回执 extra 保留证据——递减本体
        # = op 自上报)。getattr 容缺(__new__ 桩形态)。
        self._last_skip_substate: bool = False
        # 槽位中心(screen_info 静态,构造时读一次;op 内参数守卫与拖拽坐标共用)
        self._bench_pts: list[Point] = row_area_centers(ctx, '备战栏')
        self._front_pts: list[Point] = row_area_centers(ctx, '前排')
        self._back_pts: list[Point] = row_area_centers(ctx, '后排')

    # ===== 执行入口(机械执行,无返回;参数守卫已收拢各动作 op 内
    #       守卫断言,flow/action_ops.md §1 决策侧参数现算契约)=====

    def execute(self, action: CwAction) -> None:
        """机械执行一个动作(无返回;发出即职责完成,落地判定归
        观察侧 reconcile)。

        ⚠️ 停机刹车(纵深防御第二层):运行中被停 → 拒绝
        执行任何动作(点击/拖拽/出战),抛 :class:`StopBrakeShortCircuit`
        停机短路(语义与触发判据见类 docstring;run 27 实证覆盖绕环路径)。
        调用方捕获后返回主循环,下轮 loop 顶见 STOP 退出。

        发出即登记(期望态推进门/标志/清键门 = 发出即登记 + 对账纠偏,
        不按回执门控;执行前输入契约拒绝 = 动作未发出,不登记)。
        """
        _rc = getattr(self._ctx, 'run_context', None)
        if _rc is not None and getattr(_rc, 'last_run_result', None) is not None:
            log.info('[cw][battle] 停机标志已设 → 拒绝执行 %s'
                     '(W209j 刹车)', type(action).__name__)
            raise StopBrakeShortCircuit('已停止[W209j刹车]')
        # 免战跳过子态标记每动作复位(上动作残留禁跨动作流入;op 上报经
        # _dispatch_action 写入,回执 extra 消费)。
        self._last_skip_substate = False
        detail, op_success = self._dispatch_action(action)
        self.last_detail = detail
        _extra = None
        if isinstance(action, CwActionStartBattleParam) and self._last_skip_substate:
            # 跳过子态标记进回执 extra(上报动作事实的遥测面;递减本体 =
            # op 自上报,回执只保留证据)。
            _extra = {'skip_substate': True}
        self._note_action_receipt(action, op_success, detail, extra=_extra)
        if isinstance(action, CwActionStartBattleParam):
            # 出战点击事实(出战域重设计):真执行链 = 注册表分派
            # CwActionStartBattleOp 点击序列,round 结果成功态即发出事实
            # (round_fail = 找不到按钮/area 缺失,已登记例外 =
            # action_ops.md §2.3);
            # 执行缝(假环境)不经真分派 = round 成功态原值透传。
            self.last_launch_ok = op_success
        # (S1 清键执行侧落地门已随迭代 2026-10-12-prep-shop-workflow-
        # redesign 停用删除——备战期开店标志废止,清键门无对象。)
        # (动作逻辑效果推进已并入各 op 自上报
        #  (op 内直调自己的上报函数,op-layer.md §1.2):原执行器
        #  apply_op_effect 调用删除 = 双记防线——op 已写,本处再写即双记。)
        log.info('[cw][exec] %s → %s', type(action).__name__,
                 detail or '(无摘要)')

    def _note_action_receipt(self, action: CwAction, op_success: bool,
                             detail: str,
                             extra: dict | None = None) -> None:
        """动作执行回执 → GameState receipts 域
        (渠道② logic_action,唯一写点 = kernel note_action_receipt)。

        - **纯动作事实簿记,不是验证**(R2 报告重构期的『发出即簿记非
          验证』裁定):本写点零成败判定——不读屏、不做落地推断
          (「拖3次源槽未变」类像素验回执已停用),落地判定归观察侧
          reconcile;
        - reason = 动作事实码:op_success(round 结果成功态,局部派生事实)
          为真 = ``''``(已正常发出);为假 = round_fail status 经
          :func:`_prep_receipt_block_code` 闭集映射取受阻码
          (收缩后词表 = ``未执行:*`` 现读落空族,词表见映射表注释与
          fields.md 回执契约节;异常终止的分派在本口之前抛出 = 不产行)。
          op_success 的在役消费两管道 = ①锁定恢复局守卫
          (``last_launch_ok``)②本口受阻码供给;
        - 回执行以分派为单位:每分派恰一条 logic_action 行(受阻
          动作也产行 = reason 非空受阻码;停机短路在分派之前抛出 =
          执行被拒不产行——停机非动作);
        - ``extra`` = 执行面结构化字段透传(§3.2.1 质量词表执行面;
          现役唯一项 = 免战跳过子态 ``skip_substate``);
        - journal 常开(影子闸折叠)回执写入无条件;无局
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
                gs, op=type(action).__name__,
                reason='' if op_success else _prep_receipt_block_code(detail),
                detail=detail,
                screen=SCREEN_NAME, actor=type(self).__name__, extra=extra)
        except Exception as e:  # noqa: BLE001  回执失败不阻塞执行
            log.warning('[cw][receipt] 动作回执写入失败(不阻塞): %s', e)

    def _dispatch_action(self, action: CwAction) -> tuple[str, bool]:
        """动作分派(经注册表类级解析 + (ctx, param,
        env) 组装新壳 op ``CwActionXxxOp(SrOperation)``,执行取 round
        结果;op 形态权威版本 = flow/action_ops.md §1)。

        返回 ``(机械执行摘要, 是否实际发出)``。op_success = round 结果成功态
        (``round_success`` = 已发出;``round_fail`` = 定位失败等未发出
        通道,零重试即失败结束本次访问)。机械摘要 = round 结果 status。词表外
        类型 = 注册表 AssertionError 响亮暴露(参数守卫单一形态 =
        守卫断言,op 内/注册表两静态域同款)。
        """
        from sr_od.application.currency_war.operations.cw_op.cw_action_registry import (
            action_op_class_for,
        )
        env = PrepExecEnv(op=self._op, match=self._ctx.cw_match, config=None,
                          executor=self)
        op = action_op_class_for(action)(self._ctx, action, env=env)
        # 直调节点函数(单节点 op;不走 Operation.execute() 循环:重试/
        # 超时/停机查归本 runner 包络与结束本次访问的出口面所有,动作层零重试语义——
        # 节点异常原样上抛 = 执行异常通道不变)
        result = op.run()
        # op round 结果留档(QC 终结口失败透传取数口;逐分派覆盖)
        self.last_round_result = result
        if isinstance(action, CwActionStartBattleParam):
            # 免战跳过子态标记转发(op 写 env.skip_substate;递减本体 =
            # op 自上报,回执 extra 保留证据消费;getattr 容缺 = 桩 env 形态)
            self._last_skip_substate = bool(getattr(env, 'skip_substate',
                                                    False))
        return (result.status or ''), bool(result.is_success)

    # ===== 奖励域 =====

    def _open_bookcard(self, action: CwActionOpenBookcardParam) -> tuple[str, bool]:
        """薄委托(体已迁 ``cw_open_bookcard_action.CwActionOpenBookcardOp``;
        替身函数的接缝(stub seam)保留——真实保留理由 = 单帧测试直调面:
        ``sr-od-test/test/sr_od/application/currency_war/operations/cw_op/
        test_prep_action_ops.py::test_open_bookcard_executor_mechanical``
        以本方法为入口驱动 op 机械行为;src 生产面零调用,分派单一形态
        = 注册表 ``action_op_for``)。其余八桩(_collect_ore/_open_box/
        _open_tome/_sell_bench/_sell_deployed/_deploy_move/_wear_equip/
        _use_tool)全仓零调用含测试,已删。"""
        return self._dispatch_action(action)

    # ===== 装备/工具原子域(穿戴 / 工具按消耗品各立类;机械原语
    #       _equip_slot_drag_point/_owned_grid_locate
    #       留在本 runner,体迁 op 经 env.executor 消费)=====

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

        名字定位是唯一稳定识别标志(网格 reflow 使快照坐标失真);miss → None
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

    def _drag(self, src: Point, dst: Point) -> None:
        """统一拖拽原语(DragCwChar.drag_char:中心拖+hold0;机械执行,
        源槽像素验重试已拆除)。

        r10 review#2:失焦守卫下沉到本原语(所有拖拽路径共享)——窗口后台化时
        拖拽输入静默丢(r9 实证同机制:截图正常/输入丢/连环「源槽未变」假失败),
        拖前验焦点,失焦先激活。
        """
        from sr_od.application.currency_war.sim.cw_sim_ports import (
            sim_backend_installed,
        )
        if sim_backend_installed():
            # sim 模式:机械执行分支静默成功,自上报照走(直连 controller 旁路
            # port 检查;部署/卖上阵落位事实由后端状态副本承接)
            return
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

    # (tracked 随动同步三条分支(备战摘除/场上摘除/上阵落位)已随
    #tracked 第二账停用删除:动作写主域(逻辑
    #  通道)即同步,第二账无可同步;落地事实归观察边界 reconcile 对账。)

    # ===== 商店域 =====

    def _level_up(self, action: CwActionLevelUpParam | None = None) -> tuple[str, bool]:
        """薄委托(体已迁 ``cw_prep_level_up_action.CwActionLevelUpOp``;替身函数的接缝(stub seam)保留)。

        ``action`` 形参 = 注册表分派载体(原签名无参——单击体不读动作
        字段;缺省补零价占位实例仅作类型解析,行为零变化)。"""
        return self._dispatch_action(
            action if action is not None else CwActionLevelUpParam(cost=0))

    # ===== 战斗域 =====
    # StartBattleOp 现体 = 点击出战和弹窗(零判效,点击序列已执行语义);
    # 本入口保留薄委托替身函数的接缝(stub seam),返回序 (ok, detail)。

    def _start_battle(self) -> tuple[bool, str]:
        """薄委托(体已迁 ``cw_start_battle_action.CwActionStartBattleOp``;替身函数的接缝(stub seam)保留)。"""
        detail, op_success = self._dispatch_action(CwActionStartBattleParam())
        return op_success, detail




