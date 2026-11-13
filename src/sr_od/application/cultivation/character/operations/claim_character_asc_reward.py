"""领取角色详情页晋阶奖励 operation。

角色养成系列 op 第四步(与负责人对齐的四步分工):前三步进详情/选角色/
切「详情」TAB 后,本步领取等级突破(晋阶)后的奖励。

交互模型(2026-11-13 实机霍霍样本 + 负责人机制补充):
- 详情 TAB「等级」栏右侧红点(通用 ui_alert 感叹号模板)= 有晋阶奖励可领;
  无红点 = 本无可领,直接结束;
- 点红点宿主按钮 → 「角色晋阶预览」窗口:左侧 6 菱形 = 6 次晋阶阶段,
  红 ! 标记「该阶段已晋阶但奖励未领」;
- 负责人机制保证:窗口打开默认选中一定在有奖励可领的阶段;多级奖励时,
  点「领取」后游戏自动切换到下一级可领阶段——本 op 循环只判「领取」
  按钮(OCR 全词比对,防「已领取」灰字 lcs 误命中),不定位菱形、不切阶段;
- 领取后弹「获得物品」浮层(点击空白处关闭),关后回到晋阶预览窗口;
- 按钮消失 → 点右上关闭 → 回详情页。

红线:零消耗——纯领取;永不点右下「晋阶」按钮(消耗材料执行晋阶)、
永不点刷取类控件。

前置:角色详情画面·详情 TAB·列表已收起(前三步保证);本 op 不选角色、
不切页签——起点不符显式失败,组合编排归调用方。
"""

from cv2.typing import MatLike

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.i18_utils import gt
from one_dragon.utils.log_utils import log
from sr_od.context.sr_context import SrContext
from sr_od.operations.menu.phone_menu_utils import get_alert_pos
from sr_od.operations.sr_operation import SrOperation

_DETAIL_SCREEN: str = '角色-详情'
_PREVIEW_SCREEN: str = '角色-晋阶预览'

_AREA_ASC_REWARD_BTN: str = '按钮-晋阶奖励红点'  #: 详情页红点宿主按钮(纯定位 rect,检测与点击共用)
_AREA_CLAIM_BTN: str = '按钮-领取'
_AREA_OBTAIN_MARK: str = '文本-获得物品'
_AREA_CLOSE_OBTAIN: str = '点击区-关闭获得弹窗'
_AREA_CLOSE: str = '按钮-关闭'

# 点领取后游戏自动切下一级可领阶段(含切换动画),重入分类前的等待
_CLAIM_SETTLE_SEC: float = 2.0


class ClaimCharacterAscReward(SrOperation):
    """领取当前角色的全部晋阶奖励(等级突破后红点标记的奖励)。
    起点:角色-详情画面·详情 TAB·列表已收起;终点:角色-详情画面(详情 TAB)。

    结果状态:NO_REWARD(本无可领)/ CLAIMED(已领取完毕,≥1 次领取成功)。

    消耗:零——只领取,永不执行晋阶/刷取。
    """

    def __init__(self, ctx: SrContext):
        """
        :param ctx: 上下文
        """
        SrOperation.__init__(self, ctx, op_name=gt('领取角色晋阶奖励'),
                             node_max_retry_times=24)  # 领取循环多轮重入(≤6 阶 × 领取+弹窗关闭),默认 1 次必中途夭折
        self._claim_count: int = 0  #: 本次运行已领取次数(日志统计)

    #------------------- 识别辅助 -------------------#

    def _has_asc_reward_alert(self, screen: MatLike) -> bool:
        """等级栏右侧红点检测(ui_alert 模板,rect 取自红点宿主按钮)。

        get_alert_pos 返回裁剪后局部坐标,此处只判命中与否;点击点用 area 中心。"""
        area = self.ctx.screen_loader.get_area(_DETAIL_SCREEN, _AREA_ASC_REWARD_BTN)
        return get_alert_pos(self.ctx, screen, area.rect).max is not None

    def _find_claim_btn(self, screen: MatLike) -> Point | None:
        """「领取」按钮定位:按钮区域 OCR 全词比对。

        「已领取」灰字与按钮文本仅差一字,lcs 子串会误命中(末级领取后灰字
        残留的帧被误判 = 空转到预算耗尽),必须严格全词相等。
        :return: 命中框中心(点击点);未命中 None
        """
        area = self.ctx.screen_loader.get_area(_PREVIEW_SCREEN, _AREA_CLAIM_BTN)
        results = self.ctx.ocr_service.get_ocr_result_list(
            image=screen, rect=area.rect, crop_first=True)
        for r in results:
            text = str(r.data or '').strip()
            if text == '领取':
                return Point(r.x + r.w / 2, r.y + r.h / 2)
        return None

    #------------------- 节点图 -------------------#

    @operation_node(name='入口核对', is_start_node=True, node_max_retry_times=5)
    def check_entry(self) -> OperationRoundResult:
        """入口核对:须在详情 TAB(属性详情锚);按红点有无分流。

        列表开着等遮挡态不在本 op 范围(遮挡检测同 UpgradeCharacterOp)。"""
        screen = self.last_screenshot

        if self.round_by_find_area(screen, '角色-列表', '标题-角色列表').is_success:
            return self.round_fail('列表浮层开着(遮挡态):先由调用方收列表')

        if not self.round_by_find_area(screen, _DETAIL_SCREEN, '按钮-属性详情').is_success:
            return self.round_fail('不在角色详情·详情 TAB(前置:前三步 op 保证)')

        if self._has_asc_reward_alert(screen):
            return self.round_success(status='HAS_REWARD')
        return self.round_success(status='NO_REWARD')

    @node_from(from_name='入口核对', status='NO_REWARD')
    @operation_node(name='无奖励收尾')
    def no_reward(self) -> OperationRoundResult:
        """无红点 = 本无可领:成功结束。"""
        log.info('晋阶奖励: 无可领红点,直接结束')
        return self.round_success(status='NO_REWARD')

    @node_from(from_name='入口核对', status='HAS_REWARD')
    @operation_node(name='打开晋阶预览', node_max_retry_times=6)
    def open_preview(self) -> OperationRoundResult:
        """点红点宿主按钮 → 晋阶预览窗口(until = 标题锚)。

        窗口关闭动画余韵期内点击会被吞(实机:首次点击无效、第二次才开),
        本节点 until 不满足自动重试覆盖该场景。"""
        screen = self.last_screenshot
        return self.round_by_find_and_click_area(
            screen, _DETAIL_SCREEN, _AREA_ASC_REWARD_BTN,
            until_find_all=[(_PREVIEW_SCREEN, '标题-晋阶预览')],
            pre_delay=0.5, success_wait=1.5, retry_wait=2,
        )

    @node_from(from_name='打开晋阶预览')
    @operation_node(name='领取循环', node_max_retry_times=24)
    def claim_loop(self) -> OperationRoundResult:
        """flat loop:弹窗关闭 → 画面锚 → 领取按钮 → 领完收尾。

        round_retry 内建重入本节点,不设自环出边——本节点发出的
        round_success(ALL_CLAIMED) 有出边匹配到关闭收尾。

        每轮分类(优先级):
        ① 「获得物品」浮层在 → 点空白关掉(上轮领取的收尾);
        ② 晋阶预览标题锚不在 → 等画面稳定(异常画面由预算耗尽显式失败);
        ③ 「领取」按钮全词命中 → 点击(游戏自动切下一级可领阶段);
        ④ 按钮消失 = 全部领完 → 转关闭收尾。"""
        screen = self.last_screenshot

        # ① 获得物品浮层(上轮领取的收尾)
        if self.round_by_find_area(screen, _PREVIEW_SCREEN, _AREA_OBTAIN_MARK).is_success:
            result = self.round_by_find_and_click_area(
                screen, _PREVIEW_SCREEN, _AREA_CLOSE_OBTAIN,
                until_not_find_all=[(_PREVIEW_SCREEN, _AREA_OBTAIN_MARK)],
                pre_delay=0.5, success_wait=1, retry_wait=1.5,
            )
            if result.is_success:
                return self.round_retry('获得物品弹窗已关,重入分类', wait=1.5)
            return result

        # ② 画面锚核对(过渡帧等待;预算耗尽 = 显式失败带截图)
        if not self.round_by_find_area(screen, _PREVIEW_SCREEN, '标题-晋阶预览').is_success:
            return self.round_retry('不在晋阶预览窗口,等画面稳定', wait=1.5)

        # ③ 领取按钮(全词比对)
        claim_point = self._find_claim_btn(screen)
        if claim_point is not None:
            self.ctx.controller.click(claim_point)
            self._claim_count += 1
            return self.round_retry(f'已点领取(第{self._claim_count}次),游戏自动切下一级',
                                    wait=_CLAIM_SETTLE_SEC)

        # ④ 按钮消失 = 全部领完
        return self.round_success(status='ALL_CLAIMED', wait=1)

    @node_from(from_name='领取循环', status='ALL_CLAIMED')
    @operation_node(name='关闭收尾', node_max_retry_times=6)
    def close_preview(self) -> OperationRoundResult:
        """点右上关闭 → 回详情页(until = 属性详情锚)。

        成功时显式转 CLAIMED(round 系点击默认 status=area 名,不转则
        op 对外契约的最终 status 会变成 area 名)。"""
        log.info('晋阶奖励: 领取完成,共领取 %d 次', self._claim_count)
        screen = self.last_screenshot
        result = self.round_by_find_and_click_area(
            screen, _PREVIEW_SCREEN, _AREA_CLOSE,
            until_find_all=[(_DETAIL_SCREEN, '按钮-属性详情')],
            pre_delay=0.5, success_wait=1.5, retry_wait=2,
        )
        if result.is_success:
            return self.round_success(status='CLAIMED', wait=1)
        return result
