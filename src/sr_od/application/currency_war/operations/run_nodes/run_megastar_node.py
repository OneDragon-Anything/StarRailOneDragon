# 未验证(货币战争自主推进期代码,需进对应画面按 od-dev-screen-onboarding 等 skill review 重审后才能信)

"""货币战争 巨星节点 RunNode(位面首领 round6 的巨星选择 overlay)。

实机(2026-08-04):强化角色**可选**,不选也能确认推进 —— 点确认后 overlay 消失、回备战 1-6
出战。套 RunNode 验证(overlay 消失=完成)+ 预算(点不动 bail,不再无限烧预算)。

TODO(策略):候选按 target_comp 选(现默认左=花火);强化角色可后续接(可选,不影响推进)。
TODO(task#20):候选/确认坐标进 screen_info。
"""
import time
from typing import ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.currency_war_config import CurrencyWarConfig
from sr_od.application.currency_war.cw_node_obs import read_megastar_options
from sr_od.application.currency_war.cw_state import GameState
from sr_od.application.currency_war.operations.run_nodes.run_node import RunNode
from sr_od.context.sr_context import SrContext


class RunMegastarNode(RunNode):
    """巨星节点:read 候选 → decide_megastar(select_megastar 按 target.core_chars)→ 点选中候选 + 确认。"""

    # 左候选(花火)位 —— 实机 bot 点 (822,333) 已选中花火(金边);名位置 = 卡身选中区。
    CANDIDATE_LEFT: ClassVar[Point] = Point(822, 333)
    # 右候选(星期日)位 —— OCR 名 @x1061 y334(cw_megastar 实测 2026-08-07);同 y。
    CANDIDATE_RIGHT: ClassVar[Point] = Point(1061, 333)
    # 「确认选择」钮中心(OCR 确认选择 x1442y548;钮中心 ~1490,560)。
    CONFIRM: ClassVar[Point] = Point(1490, 560)

    def __init__(self, ctx: SrContext):
        RunNode.__init__(self, ctx, op_name='货币战争-巨星节点')

    @operation_node(name='巨星节点', is_start_node=True, node_max_retry_times=8)
    def handle(self) -> OperationRoundResult:
        return self._run_node()

    def _in_node(self, screen) -> bool:
        # 巨星 overlay:有「确认选择」且非「选择伙伴」(选择伙伴候选是 stage 立绘,由 RunSelectPartner 接)。
        # lcs 0.7:防「确认选择」与「请选择投资策略」共享「选择」(2/4=0.5)误匹配。
        return (self.round_by_ocr(screen, '确认选择', lcs_percent=0.7).is_success
                and not self.round_by_ocr(screen, '选择伙伴', lcs_percent=0.7).is_success)

    def _do_action(self, screen) -> None:
        # D-97:候选只点**一次**(防 RunNode retry re-click 把候选 toggle 反选 → confirm 无候选失效 → 卡死)。
        # 2026-08-07 实测:星期日选中(金边)后 confirm@(1490,560) **即关 overlay** —— step2「强化角色」**可选**,
        # 直接跳过。旧 D-96 误判 step2 必需(实为 toggle bug 致 confirm 无候选失效);根因是 RunNode retry re-click。
        # megastar 选中态是**视觉**(金边,非 OCR「已选择」)→ 用 flag 保证候选只点一次(类 partner「已选择」守卫)。
        if not getattr(self, '_candidate_clicked', False):
            # D-95:read 候选 → decide_megastar(select_megastar 按 target.core_chars)→ 点选中 idx。bug#1 mouse_move。
            options = read_megastar_options(self.ctx, screen)
            match = self.ctx.cw_match
            idx = 0
            if match is not None and options:
                _state = match.session.last_state or GameState()   # overlay 时用上次备战快照
                _cfg = CurrencyWarConfig(self.ctx.current_instance_idx)
                pick = match.strategy.decide_megastar(options, _state, match.session, _cfg)
                if 0 <= pick.idx < len(options):
                    idx = pick.idx
                log.info(f'[cw-megastar] candidates={[o.char_id for o in options]} pick=idx{idx} {pick.reason}')
            else:
                log.info(f'[cw-megastar] options={len(options)} match={match is not None} → default idx0')
            candidate = RunMegastarNode.CANDIDATE_LEFT if idx == 0 else RunMegastarNode.CANDIDATE_RIGHT
            self.ctx.controller.mouse_move(candidate)
            self.ctx.controller.click(candidate)
            self._candidate_clicked = True   # 只点一次(防 retry toggle 反选)
            time.sleep(0.6)
        # confirm(候选已选一次 → confirm 跳过 step2(可选)→ overlay 关;retry 重 confirm 防 bug#1 落空)。
        self.ctx.controller.mouse_move(RunMegastarNode.CONFIRM)
        self.ctx.controller.click(RunMegastarNode.CONFIRM)
        time.sleep(0.9)
        # D-96 step2 安全网:正常 candidate-confirm 已关 overlay;若罕见仍在 + 有「请选择强化角色」→ 再 confirm。
        if self.round_by_ocr(self.screenshot(), '请选择强化角色', lcs_percent=0.7).is_success:
            log.info('[cw-megastar] step2 请选择强化角色 仍在(罕见)→ 再 confirm(安全网)')
            self.ctx.controller.mouse_move(RunMegastarNode.CONFIRM)
            self.ctx.controller.click(RunMegastarNode.CONFIRM)
            time.sleep(0.9)
