"""货币战争 备战暗色锁定返回 op(空决策形态,A6)。

备战「锁定」暗色子态族的处理迁移:点右上「返回XX选择」按钮回对应
overlay,无验效(回 overlay 由下轮外循环重判)。一份 op 类服务两个画面档
(``货币战争-备战-策略锁定``/``货币战争-备战-遭遇锁定``),分发处传入命中
的那对(带参构造先例 = ``CwScreenBattleWait(ctx, st, config)``)。

背景(原分支注释):overlay 点「返回备战界面」→ 备战画面带暗色蒙层,
此态下备战双识别标志仍精准命中——不先分流会被当正常备战操作(读暗牌/暗 gold);
通用规则单一源 = screen_flow_timing.md #18(暗色态判别识别标志 = 右上按钮)。

形态(画面 op 两段式:观察 node → 决策动作 node,直继承 SrOperation;
推进型空决策骨架逐屏内联,无共享基类——模式一致即重复):观察 node =
入口识别标志门(命中的返回按钮识别标志,与外循环阶段一身份分发判定同源同参(分发判定单一源 = flow/outer_loop.md §2.2);miss 未发 =
round_fail 返回主循环重新判定,「下一帧重判」是外循环职责)+ obs{on_screen}
挂实例属性(空决策形态无 report:本屏零状态容器写点,obs 类住
kernel/cw_screen_report/prep_locked_return.py,import 构造即可)。决策
动作 node = 落地复查顶部(点返回已发 → 识别标志 miss = 已离开本画面 → success
结束本次访问——出口 = 入口观察的合法重判,非动作层判效;识别标志在场 = 再推进)→ 点
「返回XX选择」单次推进(success_wait=1.5 同原分支内联值)→ round_wait
循环(不烧节点重试预算,不收敛 = 动作 bug 响亮暴露,无防御上限;
「推进动作未落地」= round_fail 如实结束本次访问)。本类 = 默认 area 识别标志形态的
参数化变体:空 area 构造即免识别标志形态(无「已离开」观察信号,发出即
success,原无验效出口;有界性归外循环重派/分发)。
"""
from cv2.typing import MatLike

from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from sr_od.application.currency_war.kernel.cw_screen_report.prep_locked_return import (
    CwScreenPrepLockedReturnObs,
)
from sr_od.application.currency_war.operations.cw_operation_base import CwOperation
from sr_od.context.sr_context import SrContext


class CwScreenPrepLockedReturn(CwOperation):
    """备战暗色锁定子态:点「返回XX选择」按钮(画面档参数化)。"""

    def __init__(self, ctx: SrContext, screen_name: str, area_name: str):
        """:param screen_name: 命中的画面档(策略锁定/遭遇锁定二选一)
        :param area_name: 该画面的返回按钮识别标志(入口与点击同识别标志)"""
        CwOperation.__init__(self, ctx, op_name='货币战争-备战暗色锁定')
        # 画面档名/返回按钮识别标志(构造参数化,入口与点击同识别标志)
        self._screen_name: str = screen_name
        self._entry_area: str = area_name
        # 推进已发标志(零验证形态(用户裁定:动作层不做效果验证,判效归下一帧观察)):区分「首发识别标志 miss = 误分发 失败结束本次访问」
        # 与「重入识别标志 miss = 已离开本画面 success 结束本次访问」(实例级,单 op 生命周期)。
        self._advanced_once: bool = False
        # 观察结果(观察 node 产物,决策动作 node 消费;空决策形态无 report)。
        self._obs: CwScreenPrepLockedReturnObs | None = None

    def entry_ok(self, screen: MatLike | None) -> bool:
        """入口观察:返回按钮识别标志校验(area 键原语,与分发判定同源同参)。

        空识别标志构造(免识别标志形态)无观察信号,恒过(缺省缺位语义,与骨架
        缺省 area 键原语逐位同)。"""
        if not self._entry_area:
            return True
        return self.round_by_find_area(
            screen, self._screen_name, self._entry_area,
            crop_first=False).is_success

    @operation_node(name='观察', is_start_node=True)
    def observe(self) -> OperationRoundResult:
        """入口识别标志门 + obs{on_screen} 装载(空决策形态无 report)。

        门 miss = 首发误分发(分发判定帧命中 ∧ op 新帧识别标志 miss 的过渡帧):
        失败结束本次访问,返回主循环重新判定,不在 op 内等待重探。免识别标志形态(空识别标志)门恒过。"""
        screen = self.last_screenshot
        if not self.entry_ok(screen):
            return self.round_fail(
                f'{self.op_name}入口锚未命中(交回外循环重判)')
        self._obs = CwScreenPrepLockedReturnObs(on_screen=True, screen=screen)
        return self.round_success()

    @node_from(from_name='观察')
    @operation_node(name='决策动作', node_max_retry_times=2)
    def act(self) -> OperationRoundResult:
        """落地复查(顶部)→ 单次推进 → 出口(预算 = 现役值 2 保留)。"""
        if self._advanced_once and not self.entry_ok(self.last_screenshot):
            # 落地复查(零验证形态):重入识别标志 miss = 已离开本画面 → success
            # 结束本次访问;旗标清(实例级,单 op 生命周期语义)。
            self._advanced_once = False
            return self.round_success(
                f'{self.op_name}已推进(重入观察:已离开本画面)', wait=1)
        if not self.progress_once():
            return self.round_fail(f'{self.op_name}推进动作未落地')
        self._advanced_once = True
        # 空识别标志 = 免识别标志出口(无「已离开」观察信号,发出即 success;原无验效
        # 形态;有界性归外循环重派/分发,bail 计数消费零漂移)。否则循环
        # 推进 = round_wait(不烧节点重试预算;不收敛 = 动作 bug 响亮暴露,
        # 无防御上限)。
        if not self._entry_area:
            return self.round_success(f'{self.op_name}推进已发(免锚)')
        return self.round_wait(f'{self.op_name}推进已发,重入观察裁决', wait=1)

    def progress_once(self) -> bool:
        """推进处理:点「返回XX选择」(success_wait=1.5 同原分支内联值;
        入口与点击同一按钮识别标志)。"""
        return self.round_by_find_and_click_area(
            self.last_screenshot, self._screen_name, self._entry_area,
            success_wait=1.5).is_success
