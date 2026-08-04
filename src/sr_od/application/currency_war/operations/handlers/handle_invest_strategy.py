"""货币战争 投资策略 3 选 1 op(从主循环拆出)。

OCR 3 张投资策略卡名 → ``cw_decisions.decide_event`` 按事件白名单打分 → 点**最优**卡
+ 确认。替代原"盲点中卡"(无策略)。

卡名按行过滤(2026-08-04 snap 实测):标题「请选择投资策略」顶(y≈98)、卡名中(y≈490,
center)、描述下(y≈520+)、「刷新次数1」底(y≈841)、「确认」底(y≈983);取 y≈490 行
短文本(2-8 字)即 3 张卡名,按 center-x 排序左→右。

点击 mechanics(2026-08-04 实测):点卡名(y≈474)**不选中**(疑似开详情,bot 点名 540+ 次从没
选中 → 确认灰 → 卡死 18min)→ 点**描述区**(CARD_CLICK_Y=545)才选中(同 invest_env:name 不
选中、描述区选中)。选中 → 确认。decide_event 仅用 state.board,投资策略 overlay 时 board 不可
读 → 空 board stub。

bug#1 mitigation: 关键 click 前 mouse_move(零移动不被判 drag)。

TODO(task#20):CARD_CLICK_Y + 确认坐标进 screen_info(``currency_war_invest_strategy``)。
"""
import time
import types
from typing import ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.currency_war_config import CurrencyWarConfig
from sr_od.application.currency_war.cw_decisions import decide_event
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class HandleInvestStrategy(SrOperation):
    """投资策略 3 选 1:OCR 卡名 → decide_event 打分 → 点最优卡 + 确认。"""

    # 卡选中点击 Y(2026-08-04 实测修正):卡名 y≈474 **不选中**(bot 点名 540+ 次从没选中 → 确认灰 →
    # 卡死 18min);**描述区 y≈545 才选中**(卡名下方)。同 invest_env(name 不选中、描述区/卡身选中):
    # 投资策略/环境卡点名字都不触发选中(疑似开详情),点描述区才选中。手动验证:(952,549)选中武装支援
    # → 确认可点 → 推进。choose_x 用卡名 center-x(名/描述同卡 x 一致)。TODO(task#20):进 screen_info。
    CARD_CLICK_Y: ClassVar[int] = 545
    # 卡名行 center-y 过滤带(标题 y≈98 / 描述 y≈520+ / 刷新次数 y≈841 / 确认 y≈983)
    NAME_CY_LO: ClassVar[int] = 465
    NAME_CY_HI: ClassVar[int] = 505
    _EXCLUDE: ClassVar[set[str]] = {'请选择投资策略', '攻略', '返回备战界面', '图例', '确认', '刷新次数1'}
    # 确认按钮固定中心(snap 实测 OCR「确认」bbox center ≈ 978,983);TODO(task#20)进 screen_info
    CONFIRM: ClassVar[Point] = Point(978, 983)

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='货币战争-投资策略')

    def _read_options(self, screen) -> list[tuple[str, int, int]]:
        """OCR 3 张卡的 ``(名字, center-x, center-y)``,按卡名行 y 过滤 + 左→右排序。"""
        ocr_map = self.ctx.ocr_service.get_ocr_result_map(
            image=screen, rect=None, color_range=None, crop_first=False,
        )
        opts: list[tuple[str, int, int]] = []
        for text, mrl in ocr_map.items():
            if mrl.max is None:
                continue
            cy = mrl.max.center.y
            if (HandleInvestStrategy.NAME_CY_LO <= cy <= HandleInvestStrategy.NAME_CY_HI
                    and 2 <= len(text) <= 8 and text not in HandleInvestStrategy._EXCLUDE):
                opts.append((text, mrl.max.center.x, cy))
        opts.sort(key=lambda t: t[1])
        return opts

    @operation_node(name='投资策略', is_start_node=True, node_max_retry_times=10)
    def handle(self) -> OperationRoundResult:
        screen = self.last_screenshot
        if not self.round_by_ocr(screen, '投资策略').is_success:
            return self.round_fail('非投资策略屏')

        opts = self._read_options(screen)
        config = CurrencyWarConfig(self.ctx.current_instance_idx)
        names = [n for n, _x, _y in opts]
        pick = decide_event(names, config, types.SimpleNamespace(board={})) if names else None
        if pick is not None and 0 <= pick.option_idx < len(opts):
            chosen, choose_x, choose_y = opts[pick.option_idx]
            reason = pick.reason
        elif opts:
            chosen, choose_x, choose_y, reason = opts[0][0], opts[0][1], opts[0][2], 'fallback(no-decision)'
        else:
            chosen, choose_x, choose_y, reason = '?', 920, 490, 'fallback(no-ocr)'
        log.info(f'[cw-strat] options={names} chose={chosen!r}@({choose_x},{choose_y}) reason={reason}')

        # 点最优卡的**描述区**选中(2026-08-04 实测:卡名 y474 点了不选中 → 改描述区 CARD_CLICK_Y;同 invest_env)。
        # bug#1 mitigation:mouse_move(纯移动)+ click(零移动)→ 不被判 drag。
        target = Point(choose_x, HandleInvestStrategy.CARD_CLICK_Y)
        self.ctx.controller.mouse_move(target)
        time.sleep(0.3)
        self.ctx.controller.click(target)
        time.sleep(0.7)
        # 确认(bug#1 mitigation:mouse_move + click 固定确认按钮中心 ~978,983)
        self.ctx.controller.mouse_move(HandleInvestStrategy.CONFIRM)
        time.sleep(0.3)
        self.ctx.controller.click(HandleInvestStrategy.CONFIRM)
        return self.round_success(wait=2)
