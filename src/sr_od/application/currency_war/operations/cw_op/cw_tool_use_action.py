"""工具消耗动作 op(CwActionToolUseOp)——坐标参数化机械动作(工具原子
七类;显式坐标源/目标,op 机械面零读屏零定位:拖拽起点 = 参数
tool_cx/tool_cy,目标 = equip 模式 tgt_cx/tgt_cy 显式坐标 / char 模式
槽位参数 + back_slot_count 静态解析)。机械执行后 **op 内直调自己的
上报函数**(七工具参数共用机械半,上报 = 各自状态容器写函数,按 param
类型一行解析;零分派语义 = op-layer.md §1.2;记账 = 坐标反查,字段写
权威版本 = ``kernel/cw_action_report/tool_use``)。非终结。

一个 op 类覆盖工具原子七类(R8 按消耗品各立词表类,机械半同构)。
注册表七行(每词表类一行)同指本 op,消费语义逐类一致。零消耗确认
交叉核对(裁决 3:消耗交叉核对由观察承接)。"""
from __future__ import annotations

import time
from collections.abc import Callable
from typing import TYPE_CHECKING, ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.kernel.cw_action_report.tool_use import (
    report_action_furnace_use_param,
    report_action_lucky_token_use_param,
    report_action_perfect_projector_use_param,
    report_action_precision_wrench_use_param,
    report_action_privilege_card_use_param,
    report_action_staff_projector_use_param,
    report_action_wrench_use_param,
)
from sr_od.application.currency_war.kernel.cw_game_state import (
    ChannelSig,
    game_state_from_ctx,
)
from sr_od.application.currency_war.kernel.cw_vocab import (
    CwAction,
    CwActionFurnaceUseParam,
    CwActionLuckyTokenUseParam,
    CwActionPerfectProjectorUseParam,
    CwActionPrecisionWrenchUseParam,
    CwActionPrivilegeCardUseParam,
    CwActionStaffProjectorUseParam,
    CwActionWrenchUseParam,
)
from sr_od.application.currency_war.operations.cw_operation_base import CwOperation
from sr_od.application.currency_war.prep_actions import (
    PREP_DRAG_SETTLE_WAIT_S,
    row_drag_points,
)
from sr_od.application.currency_war.sim import cw_sim_ports
from sr_od.context.sr_context import SrContext

if TYPE_CHECKING:
    from sr_od.application.currency_war.prep_actions import PrepExecEnv


class CwActionToolUseOp(CwOperation):
    """工具消耗单步(工具原子七类共用机械半;显式坐标源/目标)。
    起点:货币战争-备战画面(动作执行时);终点:拖曳工具图标到目标使用;
    动作已发出并上报逻辑态,停留原画面(判效归下一帧观察)。
    非终结(terminal=False);机械执行零判效:发出即记账,拖后零读屏,
    落地归下一入口 heavy 实读对账,重派 = 决策循环按新观察自然承接。

    参数面三分法(词表 cw_vocab 各工具类为单一源):
    - 动态坐标源(七类通用):tool_cx/tool_cy = owned 工具条目格心
      (1080p),从最近一帧 analyze_screen extras.owned_equips 元素 cx/cy
      取(读完立刻用);记账 = 按此坐标反查工具名(用户裁定「动作 op
      上报坐标,game state 根据坐标找到内容」);
    - 动态坐标目标(equip 模式,冶金炉/特权赋予卡双模类):tgt_cx/tgt_cy
      = owned 目标件格心(extras.owned_equips 同源取);0 = 未传哨兵
      (守卫断言拒零);
    - 半固定槽位(char 模式):row('front'|'back') + slot(排内画面物理
      槽位 1 基,前排 1-4/后排 1-N) + back_slot_count(后排槽数 6-9,
      来源 = extras deploy_cap−4,front 行可省);
    - 语义参数(纯日志,机械面与记账面均零消费,可省):item_name(equip
      目标件名)/char_name(目标角色名)仅进日志与 round detail。

    [记账反查契约(三条;正文 = flow/action-op.md「记账路径总契约」条款)]
    1. 反查时序不变式:上报反查消费拖前快照;重观察刷新必须晚于上报;
    2. 记账后→重观察前的坐标伴随域陈旧条目窗口禁消费(框架侧由装备网格
       新鲜度交替标志 cw4_equip_xy_pending 保证,穿装与工具共用);
    3. 反查唯一性前提:同一快照内坐标↔装备一一对应(观察路径 = 单格单件
       逐格分类保证);反查不到 = 记账拒单(源键 ``tool_xy_unresolved`` /
       equip 目标键 ``tool_target_xy_unresolved``,拖拽已发生、账未落;
       round detail 会带拒单码)。**拒单后禁止补拖**(拖拽已发生,再拖 =
       二次拖拽)——处置 = 交还框架决策循环(由框架观察链刷新对照表后
       自然重派),勿自行换坐标重试(重读 extras 取新坐标解不了对照表
       陈旧,恒拒单)。直调方无对照表刷新手段(观察工具只读不写状态)→
       **按单件会话使用**(一坐标一调用一观察对账,连用交还框架决策
       循环)。

    MCP run_operation 示例(冶金炉 equip 模式):
      args={"target_kind":"equip","tool_cx":1660,"tool_cy":120,
            "tgt_cx":1740,"tgt_cy":210,"item_name":"量产型装甲"}
    MCP run_operation 示例(拆装扳手 char 模式):
      args={"tool_cx":1620,"tool_cy":120,"row":"front","slot":2,
            "back_slot_count":6,"char_name":"银狼"}

    守卫断言清单(AssertionError 响亮暴露零拖拽,禁兜底坐标):
    - 双模类 target_kind 非法(值域 equip/char);
    - equip 模式缺目标件坐标(tgt_cx/tgt_cy 为 0 哨兵)/ 源与目标同格;
    - char 模式 row 非法 / back_slot_count 布局档键域外(6-9)/ slot
      越界(拖点表现读)。

    :param param: 工具动作参数(词表七类之一;字段语义与取值时机见词表
        类 docstring)。
    :param env: 备战域执行环境(代码内组装传入;可省 = 缺省 None,本 op
        机械半自持后零 env 消费,形参保留 = 注册表构造签名兼容)。
    """

    #: 非终结动作(每类显式声明,无基类缺省)。
    terminal = False
    terminal_wait = 0.0

    #: 工具词表类 → 注册名(round detail 日志前缀;机械定位职责已随显式
    #: 坐标消失,本表不参与定位)。
    _TOOL_NAME_BY_CLASS: ClassVar[dict[type, str]] = {
        CwActionFurnaceUseParam: '冶金炉',
        CwActionPrivilegeCardUseParam: '特权赋予卡',
        CwActionWrenchUseParam: '拆装扳手',
        CwActionPrecisionWrenchUseParam: '精密拆装扳手',
        CwActionStaffProjectorUseParam: '员工投影仪',
        CwActionPerfectProjectorUseParam: '完美投影仪',
        CwActionLuckyTokenUseParam: '好运令牌',
    }

    #: 工具词表类 → 自身上报函数(每动作一个具名接口;op 组装后按自身
    #: param 类型一行解析,零分派语义 = 直调自己的上报,op-layer.md §1.2)。
    _REPORT_BY_CLASS: ClassVar[dict[type, Callable]] = {
        CwActionFurnaceUseParam: report_action_furnace_use_param,
        CwActionPrivilegeCardUseParam: report_action_privilege_card_use_param,
        CwActionWrenchUseParam: report_action_wrench_use_param,
        CwActionPrecisionWrenchUseParam: report_action_precision_wrench_use_param,
        CwActionStaffProjectorUseParam: report_action_staff_projector_use_param,
        CwActionPerfectProjectorUseParam: report_action_perfect_projector_use_param,
        CwActionLuckyTokenUseParam: report_action_lucky_token_use_param,
    }

    def __init__(self, ctx: SrContext, param: CwAction,
                 env: PrepExecEnv | None = None):
        CwOperation.__init__(self, ctx, op_name='CwActionToolUseOp',
                             need_check_game_win=False)
        self.param = param
        self.env = env

    @operation_node(name='tool_use', is_start_node=True)
    def run(self) -> OperationRoundResult:
        """工具消耗单步(七类共用机械半:显式坐标起点 → 目标拖曳)。

        流程 = 守卫断言 → 拖点静态解析(equip = 显式 tgt 坐标;char =
        row/slot/back_slot_count → 布局档 area 表,零截图零定位)→ 实机
        机械段(mouse_move 防吞点击 → 拖前固定等待 → 单次拖拽 → 拖后
        固定等待;拖拽链参数与穿装批统一,D-36 校准申报继承)→
        park_cursor → 自上报(记账侧坐标反查,反查不到 = 拒单进 round
        detail)。机械执行零判效:发出即记账,拖后零读屏零落地判定;
        拖拽静默不生效由下一入口观察对账暴露,重派 = 决策循环按新观察
        自然承接。

        [索引定义] 拖拽坐标 = tool_cx/tool_cy(参数显式传入,owned 工具
        条目格心 1080p)→ 目标 = equip 模式 tgt 显式坐标 / char 模式
        screen_info 建档派生拖点(slot = 排内画面物理槽位 1 基)。
        """
        action: CwAction = self.param
        tool_name = self._TOOL_NAME_BY_CLASS[type(action)]
        # —— 参数守卫(参数语义唯一所有者 = op,flow/action-op.md §1
        # 校验落点契约;违法响亮暴露零拖拽,禁兜底坐标/禁负下标回环)——
        from sr_od.application.currency_war.obs.cw_back_layout import (
            _layout_prefixes,
        )
        dual_mode = isinstance(action, (CwActionFurnaceUseParam,
                                        CwActionPrivilegeCardUseParam))
        if dual_mode:
            if action.target_kind not in ('equip', 'char'):
                raise AssertionError(
                    f'{type(action).__name__} target_kind='
                    f'{action.target_kind!r} 非法(equip/char)')
        is_equip = dual_mode and action.target_kind == 'equip'
        if is_equip:
            if action.tgt_cx == 0 or action.tgt_cy == 0:
                raise AssertionError(
                    f'{type(action).__name__} equip 分支缺目标件坐标'
                    '(tgt_cx/tgt_cy=0 为未传哨兵,1080p 真实坐标恒非零)')
            if (action.tgt_cx, action.tgt_cy) == \
                    (action.tool_cx, action.tool_cy):
                raise AssertionError(
                    f'{type(action).__name__} 源与目标同格'
                    '((tool_cx,tool_cy)==(tgt_cx,tgt_cy),同格自拖非法)')
            end = Point(int(action.tgt_cx), int(action.tgt_cy))
            tgt_desc = f'equip({action.tgt_cx},{action.tgt_cy})'
        else:
            # char 模式行槽直取布局档拖点列:row 非法会静默落到错误档,
            # back_slot_count 键域外禁静默按 6 兜底(穿装批同款守卫),
            # slot 越界按拖点表现读闭合(负下标回环同族)。
            if action.row not in ('front', 'back'):
                raise AssertionError(
                    f'{type(action).__name__} row={action.row!r} '
                    '非法(front/back)')
            if action.row == 'back' \
                    and action.back_slot_count not in _layout_prefixes():
                raise AssertionError(
                    f'{type(action).__name__} back_slot_count='
                    f'{action.back_slot_count} 域外(6-9,布局档键域)')
            prefix = ('前排' if action.row == 'front'
                      else _layout_prefixes()[action.back_slot_count])
            pts = row_drag_points(self.ctx, prefix)
            if not (1 <= action.slot <= len(pts)):
                raise AssertionError(
                    f'{type(action).__name__} slot={action.slot} '
                    f'越界(1-{len(pts)};row={action.row} '
                    f'back_slot_count={action.back_slot_count})')
            end = pts[action.slot - 1]
            tgt_desc = f'{action.row}-{action.slot}'
        start = Point(int(action.tool_cx), int(action.tool_cy))
        if cw_sim_ports.mechanical_io_allowed():
            # 实机机械段(拖拽链 = 穿装批权威链:mouse_move → 拖前固定
            # 等待 → 单次拖拽 duration 1.5 → 拖后固定等待;等待全部固定
            # 时长常量,非判效)。
            self.ctx.controller.mouse_move(start)   # 防吞点击(截图前移光标)
            time.sleep(PREP_DRAG_SETTLE_WAIT_S)   # 拖前固定等待(非判效)
            self.ctx.controller.drag_to(start=start, end=end,
                                        hold_time=0.5, duration=1.5)
            time.sleep(1.5)   # MCP drag 异步落地(memory mcp-click-async-sleep-rule)
        else:
            # sim:显式坐标(实读格心/占位哨兵)不被机械消费,机械拖拽
            # 静默跳过(直连旁路 port 检查,sim-design.md §6.5);自上报
            # 照走(占位坐标反查记账,穿装批已申报语义)。
            pass
        self.park_cursor(after_wait=0.1)
        # —— 自上报(机械发出后;记账侧坐标反查,op 零感知)——
        outcome = None
        gs = game_state_from_ctx(self.ctx)
        if gs is not None:
            outcome = self._REPORT_BY_CLASS[type(action)](
                gs, action,
                ChannelSig(family='logic_action',
                           actor=type(self).__name__, mode='compute'))
        # 名称唯一机械面消费 = 日志(语义参数;记账面零消费)。
        names = '/'.join(n for n in (getattr(action, 'item_name', ''),
                                     getattr(action, 'char_name', '')) if n)
        detail = f'{tool_name}' + (f'({names})' if names else '') + \
            f' → {tgt_desc} 拖曳已发(发出即记账,落地归观察对账)'
        if outcome is not None and not outcome.applied:
            # 记账拒单如实进 round detail(直调方经 round 结果感知拒单;
            # 机械成功语义不变——拖拽确实已发生;不分支重试、不读屏验证,
            # 零判效/零重试纪律不受触及)。
            detail += f'；记账拒单:{outcome.reason}(拖拽已发生,账未落)'
        log.info(f'[cw][tool] {detail}')
        return self.round_success(detail)
