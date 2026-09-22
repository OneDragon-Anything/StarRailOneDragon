"""货币战争 详情弹窗(可合成列表/角色详情)op(空决策形态,A7)。

点卡/点角色触发的详情弹窗的处理:点面板外空白关,验「装备推荐」消失。
关闭机制建档先例:装备详情浮窗 2026-08-14 live 验「点画面空白处→关闭回备战,
无关闭按钮」;角色详情大面板 2026-08-13 live 验「点面板外空白→回备战」。
替代 ESC 的理由:ESC 在浮窗已自关时落备战会误弹「中断挑战」(bug#2 三次
实锤),空白点在 overlay 未开时是无害空点。

入口判据(双锚锚化,原全屏 OCR「可合成列表」∨「角色详情」退役):迁移
archive 双锚——「按钮-装备推荐」(角色详情变体,4 张归档 fixture 全命中)
∨「装备详情-合成公式」(可合成列表变体,该变体 fixture 命中)。退役理由
(outer_loop.md §2.1「优先 area 化」的存量欠账清偿):全屏「角色详情」与
商店卡牌详情弹窗底部的「角色详情」按钮(x560-930)全等共享(LCS 1.0,
收紧 lcs 无济于事)→ 实机事故中该弹窗被角色详情判据垄断 26 分钟。位置约束的
area 锚天然区分两变体(本弹窗底部按钮不在右侧面板锚区内)。

验效退役(验证废除批,用户裁定 2026-09-10:动作 op 禁验证):原 VERIFY_AREA
= 按钮-装备推荐 的「点后验消失」半拆除——落地判定归重入观察裁决
(点空白零效果时锚仍在 → 重入再做一次,卡死从不可见变分钟级可见失败;
出口裁决 = entry_ok 双锚其一的合法观察)。

形态(画面 op 两段式:观察 node → 决策动作 node,直继承 SrOperation;
推进型空决策骨架逐屏内联,无共享基类——模式一致即重复):观察 node =
入口门(双锚其一,见上;miss 未发 = round_fail 交回外循环重判,「下一
帧重判」是外循环职责)+ obs{on_screen} 挂实例属性(空决策形态无 report:
本屏零容器写点,obs 类住 kernel/cw_screen_report/role_detail_overlay.py,
import 构造即可)。决策动作 node = 重入裁决顶部(点空白已发 → 双锚
miss = 已离开本画面 → success 交回——出口 = 入口观察的合法重判,非
动作层判效;在 = 再推进)→ 点「区域-空白关闭」单次推进(success_wait=1.5
同 0a4/0t 家族口径)→ round_wait 循环(不烧节点重试预算,不收敛 = 动作
bug 响亮暴露,无防御上限;「推进动作未落地」= round_fail 如实交回)。
本类入口信号 = 自有双锚判定(覆写形态),重入裁决有观察信号可用,无
「免锚发出即 success」出口。
"""
from cv2.typing import MatLike

from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from sr_od.application.currency_war.kernel.cw_screen_report.role_detail_overlay import (
    CwScreenRoleDetailOverlayObs,
)
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class CwScreenRoleDetailOverlay(SrOperation):
    """详情弹窗:双锚其一(装备推荐/合成公式)命中,点面板外空白关+重入裁决交回。"""

    #: 关闭点击位:备战前后排之间的真空白(面板外,两 overlay 家族共用)
    BLANK_SCREEN = '货币战争-备战'
    BLANK_AREA = '区域-空白关闭'

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='货币战争-详情弹窗')
        # 画面档名(双锚所在建档,与外循环身份分发同画面档;实例属性)
        self._screen_name: str = '货币战争-备战-角色详情'
        # 推进已发标志(验证废除形态):区分「首发锚 miss = 误分发 fail 交回」
        # 与「重入锚 miss = 已离开本画面 success 交回」(实例级,单 op 生命周期)。
        self._advanced_once: bool = False
        # 观察结果(观察 node 产物,决策动作 node 消费;空决策形态无 report)。
        self._obs: CwScreenRoleDetailOverlayObs | None = None

    def entry_ok(self, screen: MatLike | None) -> bool:
        """入口观察:双锚其一(与外循环分发 = 同画面档,门形态见 screens/role_detail_overlay.md §1):
        装备推荐 ∨ 合成公式(锚化理由见模块头)。"""
        return (self.round_by_find_area(screen, self._screen_name,
                                        '按钮-装备推荐',
                                        crop_first=False).is_success
                or self.round_by_find_area(screen, self._screen_name,
                                           '装备详情-合成公式',
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
        self._obs = CwScreenRoleDetailOverlayObs(on_screen=True, screen=screen)
        return self.round_success()

    @node_from(from_name='观察')
    @operation_node(name='决策动作', node_max_retry_times=2)
    def act(self) -> OperationRoundResult:
        """重入裁决(顶部)→ 单次推进 → round_wait(预算 = 现役值 2 保留)。"""
        if self._advanced_once and not self.entry_ok(self.last_screenshot):
            # 重入裁决(验证废除形态):重入锚 miss = 已离开本画面 → success
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
        """推进处理:点「区域-空白关闭」(success_wait=1.5 同 0a4/0t 家族
        口径:点空白后等关闭动画再进裁决;裸 click 无等待 →
        截图落在动画窗口 → 假失败自愈循环;区域-空白关闭为纯定位区,
        find_and_click 走 else 分支点建档中心,点击语义等价且自带等待)。"""
        return self.round_by_find_and_click_area(
            self.last_screenshot, self.BLANK_SCREEN, self.BLANK_AREA,
            success_wait=1.5).is_success
