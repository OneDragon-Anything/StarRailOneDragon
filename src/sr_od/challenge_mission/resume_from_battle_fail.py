from typing import ClassVar

from cv2.typing import MatLike

from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.i18_utils import gt
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation

# 连等封顶:同一形态点击后挑战锚 5 轮未回归即转试另一态/判失败。
# 「点击区-空白继续」是纯定位区(无文本无模板),点击恒成功,until 语义对它是
# 无界等待,必须靠轮数计数封顶。轮数坐标系 = 本节点函数的重入轮次(执行期计数,
# 非 retry 预算——round_wait 不消耗预算,故封顶只能自己数)。
SAME_FORM_MAX_ROUNDS: int = 5

# 兜底窗:点空白与旧结算锚均失效时的最终出口(节点 timeout_seconds)
RESUME_TIMEOUT_SECONDS: int = 3 * 60


class ResumeFromBattleFail(SrOperation):
    """把画面从「战斗失败画面」交还到「挑战画面」。
    起点:战斗失败画面(版本更新新形态或旧结算形态均可);终点:挑战画面(挑战按钮可见)。
    只做画面恢复,不做重试/退出决策——决策归调用方(各 op 的重试预算与退出落点是真差异)。
    """

    STATUS_RESUMED: ClassVar[str] = '已回挑战画面'
    STATUS_NOT_LEFT: ClassVar[str] = '失败画面未能离开'

    # 挑战态锚:通用几何对花萼/周本两形态失败画面帧均命中
    # (fixture 标定:sr-od-test/screens/大世界-战斗失败/战斗失败-历战余响.webp
    #  与 sr-od-test/screens/挑战副本-历战余响/挑战面板.webp)
    CHALLENGE_ANCHOR: ClassVar[tuple[str, str]] = ('挑战副本', '挑战按钮')

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name=gt('失败画面继续'))
        # 尝试态:False=先试新形态(点空白,版本更新后形态);True=回退旧结算形态
        # (点退出关卡)。新形态优先:当前主战场(花萼/周本)已全部是新形态。
        self._trying_old_form: bool = False
        # 当前形态已等待的轮数(连等封顶计数;每轮重入 +1,转态/成功时语义随之切换)
        self._same_form_rounds: int = 0

    @operation_node(name='失败画面继续', is_start_node=True,
                    node_max_retry_times=5, timeout_seconds=RESUME_TIMEOUT_SECONDS)
    def resume(self) -> OperationRoundResult:
        """
        入口两态分流(新形态与旧形态并存防误伤) + 连等封顶
        :return:
        """
        screen: MatLike = self.screenshot()

        # 每轮先查目标:挑战锚回归即成功(两形态点击后的统一出口)
        if self.round_by_find_area(screen, *self.CHALLENGE_ANCHOR).is_success:
            return self.round_success(ResumeFromBattleFail.STATUS_RESUMED, wait=1)

        new_form: bool = self.round_by_find_area(
            screen, '大世界-战斗失败', '标题-战斗失败').is_success
        old_form: bool = self.round_by_find_area(
            screen, '战斗画面', '退出关卡按钮').is_success

        if not self._trying_old_form and not new_form and old_form:
            # 入口两态分流(设计态B):新形态不在场而旧结算锚在场 → 直接走旧形态,
            # 不做连等空等
            self._trying_old_form = True
            self._same_form_rounds = 0

        if not self._trying_old_form and self._same_form_rounds >= SAME_FORM_MAX_ROUNDS:
            # 连等封顶:转试旧结算形态;转态前先验其锚在场,不在场直接失败
            # (防转态后按「未找到按钮」路径耗尽预算、status 落框架默认文案)
            self._trying_old_form = True
            self._same_form_rounds = 0
            if not old_form:
                return self.round_fail(ResumeFromBattleFail.STATUS_NOT_LEFT)

        if self._trying_old_form:
            if self._same_form_rounds >= SAME_FORM_MAX_ROUNDS:
                # 旧形态也连等封顶:两态均未能离开失败画面
                return self.round_fail(ResumeFromBattleFail.STATUS_NOT_LEFT)
            self._same_form_rounds += 1
            if old_form:
                click_result = self.round_by_find_and_click_area(
                    screen, '战斗画面', '退出关卡按钮', success_wait=2, retry_wait=1)
                if not click_result.is_success:
                    return click_result
            # 锚不在场(画面过渡中):不点击纯等待,计入连等封顶
            return self.round_wait('等待挑战画面回归', wait=2)
        else:
            self._same_form_rounds += 1
            if new_form:
                # 纯定位区点击恒成功,结果只看是否可点;等待由 round_wait 重入承担
                click_result = self.round_by_find_and_click_area(
                    screen, '大世界-战斗失败', '点击区-空白继续')
                if not click_result.is_success:
                    return click_result
            return self.round_wait('等待挑战画面回归', wait=2)
