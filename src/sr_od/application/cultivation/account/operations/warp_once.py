"""跃迁抽卡 op —— 在跃迁页执行跃迁 1 次 / 10 次，抽完停在结果总览页供用户看出货。

⚠️ 消耗红线（skills/sr-od-game-consume）：跃迁按钮是消耗控件，点击即扣专票/
星票；本 op 只应在用户明确授权的抽卡请求下调用（agent 不得自行发起）。
票不足时的星琼兑换（160/张）是追加消耗决策，``allow_jade_exchange=True``
同样必须先获用户明确授权。

流程（2026-11-12 实机探索建档）：
- 跃迁页点「跃迁1次/10次」→ 抽卡动画（数秒）→ 跃迁-结果画面逐件展示（点
  击任意处翻页）→ 10 连推进到「跃迁-结果总览」页（全部出货汇总）后**停止**，
  用户直接在总览页看出货；单抽展示自动结束回跃迁页（单抽无总览页）。
- 逐件展示中点击转化卡面会误入角色详情页（养成系统既有屏「角色-详情」）——
  处理节点检测到即点其关闭按钮自愈。
- 专票不足时游戏会弹星琼兑换确认（160 星琼/张，跃迁-兑换确认屏已建档）——
  由「兑换确认闸」节点按 allow_jade_exchange 分流；确认后星琼仍不足会**接着
  弹古老梦华兑换确认**（1 梦华=1 星琼按需补差额，跃迁-梦华兑换屏已建档）——
  按 allow_dream_exchange 分流。两者都是追加消耗决策，传 True 前必须获用户
  明确授权；任一未授权则点取消干净失败。

「结束抽卡」收摊（用户明示后）：跑 ReadWarpStatusOp {back_to_world: true}，
其导航链从结果总览页/跃迁页回大世界。

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
_WARP_EXCHANGE_SCREEN: str = '跃迁-兑换确认'
_WARP_DREAM_SCREEN: str = '跃迁-梦华兑换'
_CHAR_DETAIL_SCREEN: str = '角色-详情'
_WARP_RESULT_SUMMARY: str = '跃迁-结果总览'
_NORMAL_WORLD: str = '大世界-普通'

WARP_TIMES_ONE: int = 1
WARP_TIMES_TEN: int = 10
_ALLOWED_TIMES: set[int] = {WARP_TIMES_ONE, WARP_TIMES_TEN}


class WarpOp(SrOperation):
    """在跃迁页当前选中卡池执行跃迁，抽完**停在结果总览页**供用户看出货。

    结果状态：
    - ``WARP_AT_SUMMARY``：10 连完成，停在「跃迁-结果总览」页（用户直接看
      全部出货；用户要求结束抽卡时由收摊流程返回大世界）；
    - ``WARP_DONE``：单抽完成回到跃迁页（单抽无总览页，展示自动结束）；
    - ``STAY_ENTRY``：times 非法（1/10 之外）直接返回；
    失败：当前池票不足且未授权星琼兑换（已点取消干净退出）、导航失败、
    抽卡后超时未推进。

    注意：调用前调用方负责选中目标卡池（跃迁页左侧列表）——本 op 不切池
    （切池判定依赖池子数量动态识别，见跃迁 doc），在哪个池点按钮就抽哪个池。
    """

    def __init__(self, ctx: SrContext, times: int = WARP_TIMES_ONE,
                 allow_jade_exchange: bool = False,
                 allow_dream_exchange: bool = False):
        """
        :param ctx: 上下文
        :param times: 跃迁次数，仅支持 1 / 10
        :param allow_jade_exchange: 票不足时是否允许消耗星琼自动兑换补票
            （160 星琼/张，游戏弹窗确认）。False = 点取消干净失败；True =
            点确认继续抽。**兑换是追加消耗决策，调用方必须先获用户明确授权**
            才能传 True。
        :param allow_dream_exchange: 星琼也不足时是否允许使用古老梦华按需兑换
            （1 星梦华=1 星琼，游戏二次弹窗确认）。False = 点取消干净失败。
            **古老梦华只能充值/月卡类途径获取，部分玩家专门囤积兑换皮肤**——
            消耗它同样必须先获用户明确授权。
        """
        self._times: int = times
        self._allow_jade_exchange: bool = allow_jade_exchange
        self._allow_dream_exchange: bool = allow_dream_exchange
        self._clicked: bool = False
        """已点过跃迁按钮（结果处理节点据此分流：点前=点按钮，点后=关结果画面）"""
        SrOperation.__init__(self, ctx, op_name=gt('跃迁抽卡'),
                             node_max_retry_times=80)

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

        票不足时游戏弹星琼兑换确认——由「兑换确认闸」节点按授权分流处理。
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
    @operation_node(name='兑换确认闸')
    def exchange_gate(self) -> OperationRoundResult:
        """票不足的二级弹窗链，按授权逐级分流。

        - 一级「跃迁-兑换确认」（星轨专票不足，N 星琼买 M 张）：
          allow_jade_exchange=True 点确认；False 点取消干净失败。
        - 确认后星琼不足会**接着弹二级「跃迁-梦华兑换」**（古老梦华按需兑换）：
          allow_dream_exchange=True 点确认继续抽；False 点取消干净失败。
        - 两个弹窗都不在 = 票足直接进抽卡动画，放行。

        点击必须带 press_time=0.1（游戏弹窗按钮对极短点击不响应,与结果画面
        同款坑）——显式点击+手动验证弹窗消失才算生效(框架 until 曾被 OCR
        偶发漏检误满足造成假成功)。
        """
        screen = self.check_and_update_current_screen(screen_name_list=[
            _WARP_EXCHANGE_SCREEN, _WARP_DREAM_SCREEN])
        if screen == _WARP_EXCHANGE_SCREEN:
            if not self._allow_jade_exchange:
                return self._click_and_verify_closed(_WARP_EXCHANGE_SCREEN, '按钮-取消',
                                                     fail_status='票不足且未授权星琼兑换,已点取消(跃迁未执行)')
            return self._click_and_verify_closed(_WARP_EXCHANGE_SCREEN, '按钮-确认',
                                                 success_status='JADE_EXCHANGED', wait=2)
        if screen == _WARP_DREAM_SCREEN:
            if not self._allow_dream_exchange:
                return self._click_and_verify_closed(_WARP_DREAM_SCREEN, '按钮-取消',
                                                     fail_status='星琼不足且未授权古老梦华兑换,已点取消(跃迁未执行)')
            return self._click_and_verify_closed(_WARP_DREAM_SCREEN, '按钮-确认',
                                                 success_status='DREAM_EXCHANGED', wait=4)
        return self.round_success(status='NO_EXCHANGE', wait=1)

    def _click_and_verify_closed(self, screen_name: str, button: str,
                                 success_status: str | None = None,
                                 fail_status: str | None = None,
                                 wait: float = 1.5) -> OperationRoundResult:
        """点击弹窗按钮（press_time=0.1）并验证弹窗消失。

        消失 → success_status 非 None 时返回 round_success（流转下一节点），
        否则返回 round_fail（fail_status 即失败文案）；未消失 → round_retry。
        """
        area = self.ctx.screen_loader.get_area(screen_name, button)
        self.ctx.controller.click(area.center, press_time=0.1)
        if self.check_and_update_current_screen(
                screen_name_list=[screen_name]) != screen_name:
            if success_status is not None:
                return self.round_success(status=success_status, wait=wait)
            return self.round_fail(status=fail_status)
        return self.round_retry('弹窗点击未生效,重试', wait=1.5)

    @node_from(from_name='兑换确认闸', status='EXCHANGED')
    @node_from(from_name='兑换确认闸', status='JADE_EXCHANGED')
    @node_from(from_name='兑换确认闸', status='DREAM_EXCHANGED')
    @node_from(from_name='兑换确认闸', status='NO_EXCHANGE')
    @operation_node(name='处理结果画面', node_max_retry_times=80)
    def handle_result(self) -> OperationRoundResult:
        """循环处理抽卡展示，10 连推进到结果总览页后**停在总览页**供用户看出货。

        画面形态分流（10 连实测）：
        - 跃迁-结果总览（逐件看完后的汇总页）→ ``WARP_AT_SUMMARY`` 停止——
          用户直接看全部出货；后续收摊归「结束抽卡」场景（用户明示结束后
          跑 ReadWarpStatusOp，其导航链从总览页回大世界）。
        - 跃迁页：单抽展示自动结束直接回跃迁页（单抽无总览页）→ ``WARP_DONE``。
        - 角色-详情（**点击转化卡面会误入此页**——游戏展示流程本身不弹详情，
          是中央点击落在可点击的转化卡面上导致的）：点其「按钮-关闭」自愈
          返回展示流。
        - 其他（普通逐件结果画面/抽卡动画）：点中央继续区域翻页。

        ⚠️ 点击必须带 press_time=0.1（展示类画面普遍对极短点击不响应）。
        跃迁页/总览页回归超预算 = 停在未建档画面，fail 报告现场。
        """
        if not self._clicked:
            return self.round_retry('未点过跃迁按钮却进入结果处理(节点流异常)', wait=1)
        current = self.check_and_update_current_screen(screen_name_list=[
            _WARP_SCREEN, _CHAR_DETAIL_SCREEN, _WARP_RESULT_SUMMARY])
        if current == _WARP_RESULT_SUMMARY:
            return self.round_success(status='WARP_AT_SUMMARY', wait=1)
        if current == _WARP_SCREEN:
            return self.round_success(status='WARP_DONE', wait=1)
        if current == _CHAR_DETAIL_SCREEN:
            self._click_area_center(_CHAR_DETAIL_SCREEN, '按钮-关闭')
        else:
            self._click_area_center(_WARP_SCREEN_RESULT, '点击-继续区域')
        # 点了≠成了：下一轮 check 确认画面推进；本轮先等待过渡
        return self.round_retry('结果展示未结束,继续处理', wait=1.5)

    def _click_area_center(self, screen_name: str, area_name: str) -> None:
        """点指定 area 中心（press_time=0.1，点击有效性由调用方轮询验证）。"""
        area = self.ctx.screen_loader.get_area(screen_name, area_name)
        self.ctx.controller.click(area.center, press_time=0.1)
