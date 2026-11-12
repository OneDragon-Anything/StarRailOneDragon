"""跃迁抽卡 op —— 在跃迁页执行跃迁 1 次 / 10 次。

⚠️ 消耗红线（skills/sr-od-game-consume）：跃迁按钮是消耗控件，点击即扣专票/
星票；本 op 只应在用户明确授权的抽卡请求下调用（agent 不得自行发起）。

流程（2026-11-12 实机探索建档）：
- 跃迁页点「跃迁1次/10次」→ 抽卡动画（数秒）→ 跃迁-结果画面（物品展示，
  点击画面任意处继续）→ 回跃迁页。10 连为逐件展示，需多次点击直至回到跃迁页。
- 专票不足时游戏会弹星琼兑换确认（160 星琼/张）——本 op **不自动兑换**
  （兑换 = 追加消耗决策），票不足直接 fail 由调用方裁决。
- 结果画面稀有度形态只实测过 4★ 光锥态；3★/5★ 展示差异未建档（5★ 有专属
  动画与展示时长），op 用「离开跃迁页→循环点击至跃迁页回归」的闭环设计，
  不依赖结果画面内部锚，形态差异天然兼容（超时兜底见节点预算）。

导航逻辑与 [ReadWarpStatusOp](read_warp_status.py) 同款（起点任意画面）。
"""

from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.i18_utils import gt
from sr_od.context.sr_context import SrContext
from sr_od.operations.back_to_normal_world_plus import BackToNormalWorldPlus
from sr_od.operations.sr_operation import SrOperation
from sr_od.screen_state.common_screen_state import is_normal_in_world

_WARP_SCREEN: str = '跃迁'
_WARP_SCREEN_RESULT: str = '跃迁-结果'
_NORMAL_WORLD: str = '大世界-普通'

WARP_TIMES_ONE: int = 1
WARP_TIMES_TEN: int = 10
_ALLOWED_TIMES: set[int] = {WARP_TIMES_ONE, WARP_TIMES_TEN}


class WarpOp(SrOperation):
    """在跃迁页当前选中卡池执行跃迁，抽完留在跃迁页（便于连抽/读数）。

    结果状态：
    - ``WARP_DONE``：抽卡完成并已回到跃迁页（结果画面已全部关闭）；
    - ``STAY_ENTRY``：times 非法（1/10 之外）直接返回；
    失败：当前池专票不足（不自动兑换星琼）、导航失败、抽卡后超时未回跃迁页。

    注意：调用前调用方负责选中目标卡池（跃迁页左侧列表）——本 op 不切池
    （切池判定依赖池子数量动态识别，见跃迁 doc），在哪个池点按钮就抽哪个池。
    """

    def __init__(self, ctx: SrContext, times: int = WARP_TIMES_ONE,
                 back_to_world: bool = False):
        """
        :param ctx: 上下文
        :param times: 跃迁次数，仅支持 1 / 10
        :param back_to_world: 抽完后是否回大世界收摊（默认 False 留在跃迁页，
            便于连续抽取或读数确认）
        """
        self._times: int = times
        self._back_to_world: bool = back_to_world
        self._clicked: bool = False
        """已点过跃迁按钮（结果处理节点据此分流：点前=点按钮，点后=关结果画面）"""
        SrOperation.__init__(self, ctx, op_name=gt('跃迁抽卡'),
                             node_max_retry_times=30)

    @operation_node(name='前往跃迁页', is_start_node=True)
    def go_to_warp(self) -> OperationRoundResult:
        """画面分发：跃迁页 → 校验并抽卡；大世界 → 点跃迁入口；其他 → 回大世界重判。"""
        if self.check_and_update_current_screen(
                screen_name_list=[_WARP_SCREEN]) == _WARP_SCREEN:
            return self.round_success(status='AT_WARP', wait=0.5)
        if is_normal_in_world(self.ctx, self.last_screenshot):
            return self.round_by_find_and_click_area(
                self.last_screenshot, _NORMAL_WORLD, '按钮-跃迁',
                until_find_all=[(_WARP_SCREEN, '文本-查看详情')],
                success_wait=2, retry_wait=2)
        op = BackToNormalWorldPlus(self.ctx)
        op_result = op.execute()
        if op_result.success:
            return self.round_retry('已回大世界,重新判定画面', wait=1)
        return self.round_fail(f'回大世界失败: {op_result.status}')

    @node_from(from_name='前往跃迁页', status='AT_WARP')
    @operation_node(name='点跃迁按钮')
    def click_warp(self) -> OperationRoundResult:
        """校验次数合法后点「跃迁1次/10次」，until 跃迁页按钮消失（动画开始）。

        专票不足的兜底：跃迁页顶栏读不到票数时无法预判，点击后游戏弹兑换
        确认弹窗——该弹窗未建档，fail 报告现场由调用方裁决（不自动兑换）。
        """
        if self._times not in _ALLOWED_TIMES:
            return self.round_fail(f'不支持的跃迁次数: {self._times}（仅支持 1/10）',
                                   status='STAY_ENTRY')
        area_name = '按钮-跃迁1次' if self._times == WARP_TIMES_ONE else '按钮-跃迁10次'
        # until 模式：框架内部「点击→重入本节点→先查 until（跃迁页离开=按钮文本
        # 消失）→满足即 success」已闭环；此处 success 分支必须 round_success 流转
        # 到下一节点——若误用 round_wait 会重跑本节点造成无限自环（实测 6s/圈）。
        result = self.round_by_find_and_click_area(
            self.last_screenshot, _WARP_SCREEN, area_name,
            until_not_find_all=[(_WARP_SCREEN, '文本-跃迁1次')],
            success_wait=2, retry_wait=2)
        if result.is_success:
            self._clicked = True
            return self.round_success(status='WARP_CLICKED', wait=4)
        return result

    @node_from(from_name='点跃迁按钮', status='WARP_CLICKED')
    @operation_node(name='处理结果画面', node_max_retry_times=40)
    def handle_result(self) -> OperationRoundResult:
        """循环点击结果画面中央区域关闭展示，until 跃迁页 id_mark 回归。

        10 连逐件展示需多次点击（含点击跳过抽卡动画，游戏允许）；每轮点击
        后 sleep 等翻页动画。回到跃迁页后中央点击无害（立绘区无 UI）。
        **点击必须带 press_time=0.1**：结果画面的「点击任意处继续」对
        press_time=0 的极短点击不响应（实测 controller.click 默认值点不动，
        手动带 0.1s 按压即生效）——故不走 round_by_click_area（内部固定
        press_time=0）。跃迁页回归超预算 = 可能停在未建档画面（5★ 展示
        形态未建档），fail 报告现场。
        """
        if not self._clicked:
            return self.round_retry('未点过跃迁按钮却进入结果处理(节点流异常)', wait=1)
        area = self.ctx.screen_loader.get_area(_WARP_SCREEN_RESULT, '点击-继续区域')
        self.ctx.controller.click(area.center, press_time=0.1)
        # 点了≠成了：跃迁页 id_mark 回归才算全部展示关闭
        if self.check_and_update_current_screen(
                screen_name_list=[_WARP_SCREEN]) == _WARP_SCREEN:
            return self.round_success(status='WARP_DONE', wait=1)
        return self.round_retry('结果展示未结束,继续点击', wait=1.5)

    @node_from(from_name='处理结果画面', status='WARP_DONE')
    @operation_node(name='回大世界')
    def back_to_world(self) -> OperationRoundResult:
        """按 back_to_world 参数收摊（默认留在跃迁页便于连抽/读数）。"""
        if not self._back_to_world:
            return self.round_success(status='STAY_WARP', wait=0.5)
        result = self.round_by_find_and_click_area(
            self.last_screenshot, _WARP_SCREEN, '按钮-关闭',
            until_find_all=[(_NORMAL_WORLD, '右上图标-角色详情')],
            success_wait=1.5, retry_wait=1.5)
        if result.is_success:
            return self.round_success(status=result.status, wait=0.5)
        return result
