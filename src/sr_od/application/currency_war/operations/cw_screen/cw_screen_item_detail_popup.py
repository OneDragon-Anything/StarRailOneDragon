"""货币战争 道具详情弹窗(聘用书类)op(空决策形态;ADR-0584,A3)。

获得道具(如 3 费聘用书)后自动弹介绍 modal(0e3)的处理迁移:点 × 关闭,
无验效。**入口观察用 OCR 回退**(本画面尚无 screen_info 档案,方案审 N9):
「聘用书」∧ 非祈愿屏,与外循环分发判定同源同参——祈愿试炼选项名含
「聘用书」(4 费聘用书)的截胡死循环修复(实机实锤单次 15min+)靠这道排他,
排他双写于外循环分支判定与本 op 入口(两处同参,建档含 id_mark 后 op 侧
可切 area 锚,切换属实施批内部对齐,ADR-0584 §2.2)。

形态(画面 op 两段式:观察 node → 决策动作 node,直继承 SrOperation;
推进型空决策骨架逐屏内联,无共享基类——模式一致即重复):观察 node =
入口门(OCR「聘用书」∧ 祈愿锚不命中,与外循环 0e3 分发判定同源同参;
miss 未发 = round_fail 交回外循环重判,「下一帧重判」是外循环职责)+
obs{on_screen} 挂实例属性(空决策形态无 report:本屏零容器写点,obs 类
住 kernel/cw_screen_report/item_detail_popup.py,import 构造即可)。
决策动作 node = 重入裁决顶部(点 × 已发 → 门 miss = 已离开本画面 →
success 交回——出口 = 入口观察的合法重判,非动作层判效;在 = 再推进)
→ area 读「按钮-关闭」+ mouse_move+click 单次推进(bug#1 缓解保留)→
round_wait 循环(不烧节点重试预算,不收敛 = 动作 bug 响亮暴露,无防御
上限;「推进动作未落地」= round_fail 如实交回)。本类入口信号 = 自有
OCR 排他判定(覆写形态),重入裁决有观察信号可用,无「免锚发出即
success」出口。
"""
from cv2.typing import MatLike

from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from sr_od.application.currency_war.kernel.cw_obs_core import area_center
from sr_od.application.currency_war.kernel.cw_screen_report.item_detail_popup import (
    CwScreenItemDetailPopupObs,
)
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class CwScreenItemDetailPopup(SrOperation):
    """道具详情弹窗:点 × 关闭;入口 = OCR「聘用书」∧ 非祈愿屏。"""

    CLOSE_AREA = '按钮-关闭'

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='货币战争-道具详情弹窗')
        # 画面档名(× 控件所在建档;实例属性)
        self._screen_name: str = '货币战争-道具详情弹窗'
        # 推进已发标志(验证废除形态):区分「首发 miss = 误分发 fail 交回」
        # 与「重入 miss = 已离开本画面 success 交回」(实例级,单 op 生命周期)。
        self._advanced_once: bool = False
        # 观察结果(观察 node 产物,决策动作 node 消费;空决策形态无 report)。
        self._obs: CwScreenItemDetailPopupObs | None = None

    def entry_ok(self, screen: MatLike | None) -> bool:
        """入口观察:OCR「聘用书」(lcs 0.8)∧ 祈愿锚不命中(与外循环
        0e3 分发判定同源同参;排他理由见模块头)。"""
        return (self.round_by_ocr(screen, '聘用书', lcs_percent=0.8).is_success
                and not self.round_by_find_area(
                    screen, '货币战争-祈愿试炼', '标识-祈愿试炼',
                    crop_first=False).is_success)

    @operation_node(name='观察', is_start_node=True)
    def observe(self) -> OperationRoundResult:
        """入口门 + obs{on_screen} 装载(空决策形态无 report)。

        门 miss = 首发误分发(分发判定帧命中 ∧ op 新帧门 miss 的过渡帧):
        fail 交回外循环重判,不在 op 内等待重探。"""
        screen = self.last_screenshot
        if not self.entry_ok(screen):
            return self.round_fail(
                f'{self.op_name}入口锚未命中(交回外循环重判)')
        self._obs = CwScreenItemDetailPopupObs(on_screen=True, screen=screen)
        return self.round_success()

    @node_from(from_name='观察')
    @operation_node(name='决策动作', node_max_retry_times=2)
    def act(self) -> OperationRoundResult:
        """重入裁决(顶部)→ 单次推进 → round_wait(预算 = 现役值 2 保留)。"""
        if self._advanced_once and not self.entry_ok(self.last_screenshot):
            # 重入裁决(验证废除形态):重入 miss = 已离开本画面 → success
            # 交回;旗标清(实例级,单 op 生命周期语义)。
            self._advanced_once = False
            return self.round_success(
                f'{self.op_name}已推进(重入观察:已离开本画面)', wait=1)
        if not self.progress_once():
            return self.round_fail(f'{self.op_name}推进动作未落地')
        self._advanced_once = True
        # 循环推进 = round_wait(不烧节点重试预算;不收敛 = 动作 bug 响亮
        # 暴露,无防御上限)。
        return self.round_wait(f'{self.op_name}推进已发,重入观察裁决', wait=1)

    def progress_once(self) -> bool:
        """推进处理:读「按钮-关闭」center → mouse_move+click(缺失 =
        False 如实交回;× 位于 (1862,65) 原 VLM 定位已 area 化,mouse_move
        bug#1 缓解保留)。"""
        close = area_center(self.ctx, self.CLOSE_AREA, self._screen_name)
        if close is None:
            return False
        self.ctx.controller.mouse_move(close)
        self.ctx.controller.click(close)
        return True
