"""货币战争 投资策略 3 选 1 op(从主循环拆出)。

OCR 3 张投资策略卡名 → ``cw_decisions.decide_event`` 按事件白名单打分 → 点**最优**卡
+ 确认。替代原"盲点中卡"(无策略)。

卡名按行过滤(2026-08-04 snap 实测):标题「请选择投资策略」顶(y≈98)、卡名中(y≈490,
center)、描述下(y≈520+)、「刷新次数1」底(y≈841)、「确认」底(y≈983);取 y≈490 行
短文本(2-8 字)即 3 张卡名,按 center-x 排序左→右。

点击 mechanics(保留原 proven 逻辑,只把卡 X 换成最优卡):点 body(y550)→ 若「确认」
被遮(detail 开了)→ ESC + 点卡底(y815)→ 确认。decide_event 仅用 state.board,投资策略
overlay 时 board 不可读 → 空 board stub。

bug#1 mitigation: 关键 click 前 mouse_move(零移动不被判 drag)。

TODO(task#20):body/bottom Y + 确认坐标进 screen_info(``currency_war_invest_strategy``)。
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

    # 卡身/卡底点击 Y(snap 实测:卡名 y≈476,body 550 部分变体开 detail,卡底 815 安全选中)。
    # TODO(task#20):进 screen_info。
    CARD_BODY_Y: ClassVar[int] = 550
    CARD_BOTTOM_Y: ClassVar[int] = 815
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

        # 点最优**卡名**选中(2026-08-04 实测:body 550/bottom 815 都不选中,只有卡名 y≈476 区域选中)。
        # bug#1 mitigation:mouse_move(纯移动)+ click(零移动)→ 不被判 drag。
        name_pos = Point(choose_x, choose_y)
        self.ctx.controller.mouse_move(name_pos)
        time.sleep(0.3)
        self.ctx.controller.click(name_pos)
        time.sleep(0.7)
        # 确认(bug#1 mitigation:mouse_move + click 固定确认按钮中心 ~978,983)
        self.ctx.controller.mouse_move(HandleInvestStrategy.CONFIRM)
        time.sleep(0.3)
        self.ctx.controller.click(HandleInvestStrategy.CONFIRM)
        return self.round_success(wait=2)
