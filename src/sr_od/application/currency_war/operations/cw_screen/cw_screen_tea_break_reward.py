"""货币战争 茶歇奖励推进 op(极简推进型;迭代 2026-11-20-cw-p0-chain
design §2.1 op2)。

茶歇奖励页点「开启」= 节点完成触发器(玩家卡明示:未点开启节点不推进),
做完锚定切回备战,交回主循环。结构照 CwScreenPrepLockedReturn 观察 +
决策动作两段;**无 report 形态**(推进型空决策——obs 构造即弃零保留,
门判定布尔直接驱动节点流转,零 game state 写点;完备测试分侧断言
report 函数不在场)。

失配兜底语义:开启后实际落点无帧证(design §2.7 存疑 1,推定回备战)
——若落点非备战(如过渡动画帧),双锚 until 超时 = round_fail 交回
主循环,主循环下帧按实际画面分发(安全网天然存在,不做 op 内二次
猜测);实机验证任务核对落点并回填玩家卡。
"""
from __future__ import annotations

from cv2.typing import MatLike

from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from sr_od.application.currency_war.kernel.cw_screen_report.tea_break_reward import (
    CwScreenTeaBreakRewardObs,
)
from sr_od.application.currency_war.operations.cw_operation_base import (
    CwOperation,
)
from sr_od.context.sr_context import SrContext

_SCREEN: str = '货币战争-茶歇奖励'
A_TITLE: str = '标识-奖励标题'
A_OPEN: str = '按钮-开启'
#: 回备战标志(op2 主锚 = 节点推进证据;area 在备战档)。
A_PREP_BACK: str = '备战标识-购买经验'
#: 点开启连等封顶(含首发;until 等待在框架里是 round_wait 无界——
#: 点击恒成功锚恒不出现时框架不设限,节点自设封顶,先例 =
#: CwScreenPrep.SELECT_HERO_CLICK_MAX 同款;超限 = 落点失配形态
#: design §2.7 存疑 1,fail 交回主循环安全网)。
OPEN_CLICK_MAX: int = 3


class CwScreenTeaBreakReward(CwOperation):
    """茶歇奖励页:点「开启」→ 双锚判效(备战标志出现 ∧ 奖励标题消失)。
    起点:货币战争-茶歇奖励;终点:已点开启,画面切回货币战争-备战
    (交回主循环)。"""

    def __init__(self, ctx: SrContext):
        CwOperation.__init__(self, ctx, op_name='货币战争-茶歇奖励')
        # 推进已发标志(零验证形态):区分「首发门 miss = 误分发 fail」与
        # 「重入门 miss = 已离开本画面 success」(先例 =
        # CwScreenPrepLockedReturn._advanced_once)。
        self._advanced_once: bool = False
        # 点开启轮次计数(round_wait 原样重跑每轮 +1;连等封顶见
        # OPEN_CLICK_MAX,实例级单 op 生命周期)。
        self._open_rounds: int = 0

    def entry_ok(self, screen: MatLike | None) -> bool:
        """入口观察:奖励标题锚(area 键原语,与分发判定同源同参)。"""
        return self.round_by_find_area(
            screen, _SCREEN, A_TITLE, crop_first=False).is_success

    @operation_node(name='观察', is_start_node=True)
    def observe(self) -> OperationRoundResult:
        """入口门 + obs 装载(推进型无 report,构造即弃零保留)。

        门 miss = 首发误分发(分发判定帧命中 ∧ op 新帧锚 miss 的过渡帧):
        失败交回主循环重新判定,不在 op 内等待重探。"""
        screen = self.last_screenshot
        if not self.entry_ok(screen):
            return self.round_fail('茶歇奖励入口锚未命中(交回外循环重判)')
        # obs 构造即弃(推进型空决策;on_screen 门布尔直接驱动流转)。
        CwScreenTeaBreakRewardObs(on_screen=True, screen=screen)
        return self.round_success(wait=0)

    @node_from(from_name='观察')
    @operation_node(name='决策动作', node_max_retry_times=2)
    def act(self) -> OperationRoundResult:
        """落地复查(顶部)→ 点「开启」→ 双锚判效出口(连等封顶
        OPEN_CLICK_MAX,超限 = 落点失配 fail 交回主循环——until 等待
        在框架里是 round_wait 无界,画面不变时落地复查恒不过,节点自设
        封顶防无界;失配兜底语义见模块 docstring)。"""
        if self._advanced_once and not self.entry_ok(self.last_screenshot):
            # 落地复查(零验证形态):重入锚 miss = 已离开本画面 → success。
            self._advanced_once = False
            return self.round_success('茶歇奖励已开启(重入观察:已离开本画面)',
                                      wait=1)
        self._open_rounds += 1
        if self._open_rounds > OPEN_CLICK_MAX:
            return self.round_fail(
                f'点开启后未切屏(双锚恒不满足,>{OPEN_CLICK_MAX}轮;'
                f'落点失配形态交回主循环按实际画面分发)')
        rr = self.round_by_find_and_click_area(
            self.last_screenshot, _SCREEN, A_OPEN,
            until_find_all=[('货币战争-备战', A_PREP_BACK)],
            until_not_find_all=[(_SCREEN, A_TITLE)],
            success_wait=2.0, retry_wait=1.0)
        if rr.is_success:
            self._advanced_once = True
            return self.round_success('已点开启,画面回备战(交回主循环)',
                                      wait=0.5)
        self._advanced_once = True
        return rr
