"""货币战争 投资环境 3 选 1 op(从主循环拆出)。

OCR 3 张投资环境卡名 → ``cw_decisions.decide_event`` 按事件白名单打分 → 点**最优**卡底
+ 确认。替代原"盲点中卡"(无策略)。

卡名按行过滤:标题「投资环境」在顶(y≈98)、卡名在中(y≈392)、描述在下(y≈432)、
「确认」在底(y≈982);取 y≈392 行的短文本(2-6 字)即 3 张卡名,按 center-x 排序
左→右。decide_event 仅用 ``state.board`` 做克制判定,投资环境常在开局/局内 overlay、
board 不可读 → 传空 board stub(dot_punish 为次要细化,白名单主策略不依赖 board)。

卡底 Y + 确认坐标进 screen_info(``currency_war_invest_env``):``区域-卡牌描述行``(给 Y)
+ ``按钮-确认``(给 center),task#20 已完成;本 op 经 ``cw_observation.area_center`` 读,
缺失才用兜底常量。
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
from sr_od.application.currency_war.cw_observation import area_center
from sr_od.application.currency_war.cw_state import GameState
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class HandleInvestEnv(SrOperation):
    """投资环境 3 选 1:OCR 卡名 → decide_event 打分 → 点最优卡底 + 确认。"""

    SCREEN_NAME: ClassVar[str] = '货币战争-投资环境'   # screen_info 画面(currency_war_invest_env.yml)
    # 卡选中点击 Y:screen_info「区域-卡牌描述行」center.y(task#20);常量=screen_info 缺失兜底。
    # 实测(2026-08-04):立绘在卡顶 y≈100-400(点立绘/name y390 开角色详情,非选中);
    # **描述区 y≈450 才选中**(立绘下方);卡底 y700 无效。区别 invest_strategy(描述区 y545)。
    CARD_CLICK_Y: ClassVar[int] = 450   # 兜底;首选 area_center('区域-卡牌描述行')
    # 卡名行 center-y 过滤带(排除标题 y≈98 / 描述 y≈419+ / 确认 y≈982)。
    # 卡名 y 随立绘变(实机见过 375-378 / 392),放宽 [360,410] 容变;原 [378,408] 漏 y<378 的卡名。
    NAME_CY_LO: ClassVar[int] = 360
    NAME_CY_HI: ClassVar[int] = 410
    # 非卡名(同 y 行可能误入或已知 UI 文本)
    _EXCLUDE: ClassVar[set[str]] = {'投资环境', '攻略', '确认', '角色', '装备', '剩余次数：1'}
    # 确认按钮:screen_info「按钮-确认」center(task#20);常量=兜底。
    CONFIRM: ClassVar[Point] = Point(1082, 982)   # 兜底;首选 area_center('按钮-确认')

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
                    and 2 <= len(text) <= 8 and text not in HandleInvestEnv._EXCLUDE):
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
        # D-34:走策略 decide_invest(kind='env';default 委托 decide_event,行为等价)。overlay 叠备战时
        # board 不可读 → 传空 GameState(decide_event 只用 board 判 DoT 克制,空 board = 不惩罚,安全)。
        match = self.ctx.cw_match
        if names:
            if match is not None:
                pick = match.strategy.decide_invest('env', names, GameState(), match.session, config)
            else:
                pick = decide_event(names, config, types.SimpleNamespace(board={}))  # 防御:无 match(局外独立跑)
        else:
            pick = None
        if pick is not None and 0 <= pick.option_idx < len(opts):
            chosen, choose_x = opts[pick.option_idx]
            reason = pick.reason
        elif opts:
            chosen, choose_x, reason = opts[0][0], opts[0][1], 'fallback(no-decision)'
        else:
            chosen, choose_x, reason = '?', 960, 'fallback(no-ocr)'
        log.info(f'[cw-env] options={names} chose={chosen!r}@x={choose_x} reason={reason}')
        # D-58:存已选 env 到 session → update_target copy 到 state.active_env → env_fit(T0 env 近乎硬绑)生效。
        # 原 bug:chosen 只点不存 → state.active_env 恒空 → env_fit 全 0.5 → T0 env 绑定静默失效。
        if match is not None and chosen != '?':
            match.session.active_env = chosen

        # 点最优卡底(task#20:Y 从 screen_info「区域-卡牌描述行」center 读;缺失兜底 CARD_CLICK_Y)。
        _sel = area_center(self.ctx, '区域-卡牌描述行', HandleInvestEnv.SCREEN_NAME)
        _click_y = _sel.y if _sel is not None else HandleInvestEnv.CARD_CLICK_Y
        target = Point(choose_x, _click_y)
        self.ctx.controller.click(target)
        time.sleep(0.7)

        # 确认(task#20:center 从 screen_info「按钮-确认」读;缺失兜底 CONFIRM)。
        _confirm = area_center(self.ctx, '按钮-确认', HandleInvestEnv.SCREEN_NAME) or HandleInvestEnv.CONFIRM
        self.ctx.controller.click(_confirm)
        return self.round_success(wait=2)
