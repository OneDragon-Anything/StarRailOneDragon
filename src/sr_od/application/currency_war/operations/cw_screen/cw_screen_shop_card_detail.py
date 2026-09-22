"""货币战争 商店卡牌详情弹窗 op(空决策形态;合同)。

奖励节点采晶矿误触开的「角色 offer 购买页」弹窗(实机事故第三例同族:
0e2 概率表/1d 星徽详情之后),中央角色大面板 + 底部五牌条 + 角色详情/购买
双按钮 + 右上 X。建档 = 货币战争-商店卡牌详情(id_mark = 弹窗前景独有
双锚「按钮-购买」+「按钮-角色详情」,禁取衬底透出的底层锚)。

处理 = 点 X 关闭(弹窗内坐标,1d 先例「永远安全」;不点购买——买不买的
决策归商店域,关闭动作不得代替购买决策)→ 机械交回(验证废除批,用户
裁定 2026-09-10:动作 op 禁验证;原「验 X 消失」判效半拆除,落地由
重入观察裁决承载——X 点击零效果时锚仍在 → 重入再做一次,事故 26 分钟
放大器的防线语义由重入裁决保持)→ 交回外循环全分支重判(店开 → 0n
商店访问接管购买;备战 → 备战环)。**X 复用大厅同族模板** cw_lobby_close
(同款关闭控件,失败帧实测 conf 0.98;备战右上数据统计按钮与 X 区重叠但
模板实测零误配,见建档对拍)。

序位:0 系(先于 0n 开商店与备战双锚)——弹窗暗色衬底会遮蔽底层全部
锚(实证:开商店三锚与备战双锚在该衬底下 OCR 全灭),不先分流
则只剩变体不敏感的关键词兜底接住 = 事故形态。

形态(画面 op 两段式:观察 node → 决策动作 node,直继承 SrOperation;
推进型空决策骨架逐屏内联,无共享基类——模式一致即重复):观察 node =
入口门(双 id_mark 锚「按钮-购买」∧「按钮-角色详情」,与外循环 0t 分发
判定同源同参,双锚全中才接管——单锚形态(如其他弹窗带购买按钮)不放行;
miss 未发 = round_fail 交回外循环重判,「下一帧重判」是外循环职责)+
obs{on_screen} 挂实例属性(空决策形态无 report:本屏零容器写点,obs 类
住 kernel/cw_screen_report/shop_card_detail.py,import 构造即可)。决策
动作 node = 重入裁决顶部(点 X 已发 → 双锚 miss = 已离开本画面 →
success 交回——出口 = 入口观察的合法重判,非动作层判效;在 = 再推进)
→ 点「按钮-关闭」单次推进(success_wait=1.5 同 0a4 位面详情口径)→
round_wait 循环(不烧节点重试预算,不收敛 = 动作 bug 响亮暴露,无防御
上限;「推进动作未落地」= round_fail 如实交回)。本类入口信号 = 自有
双锚判定(覆写形态),重入裁决有观察信号可用,无「免锚发出即 success」
出口。
"""
from cv2.typing import MatLike

from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from sr_od.application.currency_war.kernel.cw_screen_report.shop_card_detail import (
    CwScreenShopCardDetailPopupObs,
)
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class CwScreenShopCardDetailPopup(SrOperation):
    """商店卡牌详情弹窗:双 id_mark 锚入口,点 X → 重入裁决交回(验证废除)。"""

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='货币战争-商店卡牌详情')
        # 画面档名(双锚与 × 所在建档;实例属性)
        self._screen_name: str = '货币战争-商店卡牌详情'
        # 推进已发标志(验证废除形态):区分「首发锚 miss = 误分发 fail 交回」
        # 与「重入锚 miss = 已离开本画面 success 交回」(实例级,单 op 生命周期)。
        self._advanced_once: bool = False
        # 观察结果(观察 node 产物,决策动作 node 消费;空决策形态无 report)。
        self._obs: CwScreenShopCardDetailPopupObs | None = None

    def entry_ok(self, screen: MatLike | None) -> bool:
        """入口观察:双 id_mark 锚全中才接管(与外循环 0t 分发判定同源
        同参;单锚形态不放行,理由见模块头)。"""
        return (self.round_by_find_area(screen, self._screen_name, '按钮-购买',
                                        crop_first=False).is_success
                and self.round_by_find_area(screen, self._screen_name,
                                            '按钮-角色详情',
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
        self._obs = CwScreenShopCardDetailPopupObs(
            on_screen=True, screen=screen)
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
        """推进处理:点「按钮-关闭」(success_wait=1.5:点 X 后等关闭动画
        再交回裁决,同 0a4 位面详情口径)。"""
        return self.round_by_find_and_click_area(
            self.last_screenshot, self._screen_name, '按钮-关闭',
            success_wait=1.5).is_success
