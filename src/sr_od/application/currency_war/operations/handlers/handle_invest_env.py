"""货币战争 投资环境 3 选 1 op(从主循环拆出)。

OCR 3 张投资环境卡名 → ``cw_decisions.decide_event`` 按事件白名单打分 → 点**最优**卡底
+ 确认。替代原"盲点中卡"(无策略)。

卡名按行过滤:标题「投资环境」在顶(y≈98)、卡名在中(y≈392)、描述在下(y≈432)、
「确认」在底(y≈982);取 y≈392 行的短文本(2-6 字)即 3 张卡名,按 center-x 排序
左→右。decide_event 仅用 ``state.board`` 做克制判定,投资环境常在开局/局内 overlay、
board 不可读 → 传空 board stub(dot_punish 为次要细化,白名单主策略不依赖 board)。

踩坑(bug#1,实测卡死):controller.click 紧跟 last_screenshot(移鼠标到角落)→ 判 drag
不落地 → 卡在投资环境屏超时。缓解:mouse_move(纯移动,无 drag 判定)+ click(零移动)。

TODO(task#20):卡底 Y + 确认按钮坐标进 screen_info(``currency_war_invest_env``)。
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


class HandleInvestEnv(SrOperation):
    """投资环境 3 选 1:OCR 卡名 → decide_event 打分 → 点最优卡底 + 确认。"""

    # 卡选中点击 Y(2026-08-04 实测修正):立绘在卡顶 y≈100-400(点立绘/name y390 开角色详情,
    # 非选中);**描述区 y≈450 才选中**(立绘下方);卡底 y700 无效。手动验证:(960,450)选中
    # 能量概念股 → 确认 → 推进到备战。区别 invest_strategy(name y476 选中)—— invest_env 立绘
    # 覆盖到 name,需点更下的描述区。
    # TODO(task#20):进 screen_info。
    CARD_CLICK_Y: ClassVar[int] = 450
    # 卡名行 center-y 过滤带(排除标题 y≈98 / 描述 y≈432 / 确认 y≈982)
    NAME_CY_LO: ClassVar[int] = 378
    NAME_CY_HI: ClassVar[int] = 408
    # 非卡名(同 y 行可能误入或已知 UI 文本)
    _EXCLUDE: ClassVar[set[str]] = {'投资环境', '攻略', '确认', '角色', '装备', '剩余次数：1'}
    # 确认按钮固定中心(实测 OCR「确认」bbox center ≈ 1082,982);TODO(task#20)进 screen_info
    CONFIRM: ClassVar[Point] = Point(1082, 982)

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='货币战争-投资环境')

    def _read_options(self, screen) -> list[tuple[str, int]]:
        """OCR 3 张卡的 ``(名字, 名字 center-x)``,按卡名行 y 过滤 + 左→右排序。"""
        ocr_map = self.ctx.ocr_service.get_ocr_result_map(
            image=screen, rect=None, color_range=None, crop_first=False,
        )
        opts: list[tuple[str, int]] = []
        for text, mrl in ocr_map.items():
            if mrl.max is None:
                continue
            cy = mrl.max.center.y
            if (HandleInvestEnv.NAME_CY_LO <= cy <= HandleInvestEnv.NAME_CY_HI
                    and 2 <= len(text) <= 6 and text not in HandleInvestEnv._EXCLUDE):
                opts.append((text, mrl.max.center.x))
        opts.sort(key=lambda t: t[1])
        return opts

    @operation_node(name='投资环境', is_start_node=True, node_max_retry_times=10)
    def handle(self) -> OperationRoundResult:
        screen = self.last_screenshot
        _hit = self.round_by_ocr(screen, '投资环境').is_success
        log.info(f'[cw-env] enter round_by_ocr(投资环境)={_hit}')
        if not _hit:
            return self.round_fail('非投资环境屏')

        opts = self._read_options(screen)
        config = CurrencyWarConfig(self.ctx.current_instance_idx)
        names = [n for n, _ in opts]
        # decide_event 仅用 state.board;投资环境 overlay 时 board 不可读 → 空 stub。
        pick = decide_event(names, config, types.SimpleNamespace(board={})) if names else None
        if pick is not None and 0 <= pick.option_idx < len(opts):
            chosen, choose_x = opts[pick.option_idx]
            reason = pick.reason
        elif opts:
            chosen, choose_x, reason = opts[0][0], opts[0][1], 'fallback(no-decision)'
        else:
            chosen, choose_x, reason = '?', 960, 'fallback(no-ocr)'
        log.info(f'[cw-env] options={names} chose={chosen!r}@x={choose_x} reason={reason}')

        # 点最优卡底(bug#1 mitigation:mouse_move + click)
        target = Point(choose_x, HandleInvestEnv.CARD_CLICK_Y)
        self.ctx.controller.mouse_move(target)
        time.sleep(0.3)
        self.ctx.controller.click(target)
        time.sleep(0.7)

        # 确认(bug#1 mitigation:mouse_move + click 固定确认按钮中心)
        self.ctx.controller.mouse_move(HandleInvestEnv.CONFIRM)
        time.sleep(0.3)
        self.ctx.controller.click(HandleInvestEnv.CONFIRM)
        return self.round_success(wait=2)
