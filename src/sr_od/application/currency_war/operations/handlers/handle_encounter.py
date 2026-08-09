# 未验证(货币战争自主推进期代码,需进对应画面按 od-dev-screen-onboarding 等 skill review 重审后才能信)

"""货币战争 遭遇节点 二选一处理 op(从主循环 ``CurrencyWarRunLoop`` 拆出)。

检测「遭遇其一」+ 底部「选择」→ 点卡身选中 + 点选择确认。2026-08-04 实测交互模型
(见 ``docs/game/screens/currency_war_encounter.md``):
  点卡身(选中)→ 点选择(确认),**中间不要插空白点击**(会取消选中 → 死循环)。

TODO(Stage C2):接 ``cw_decisions.decide_encounter``(待实现,design 08§遭遇)按 comp 成型度 +
  遭遇词缀选卡(避开急速制冷/正当防卫等克 comp 的),替代当前默认选左卡(难度低、稳)。
TODO(task#20):卡身/选择坐标进 screen_info(遭遇屏 ``currency_war_encounter`` 未建模)。
"""
import time
from typing import ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.currency_war_config import CurrencyWarConfig
from sr_od.application.currency_war.cw_node_obs import read_encounter_options
from sr_od.application.currency_war.cw_state import GameState
from sr_od.application.currency_war.operations.handlers._overlay_confirm import (
    confirm_and_verify,
    safe_click,
)
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class HandleEncounter(SrOperation):
    """遭遇节点二选一:点卡选中 + 选择确认。"""

    # 遭遇卡卡身中心。左卡=遭遇其一(难度低,金币×2);右卡=遭遇其四(难度高,随机4费角色×3)。
    CARD_LEFT: ClassVar[Point] = Point(665, 500)
    CARD_RIGHT: ClassVar[Point] = Point(1288, 550)
    # 底部「选择」按钮中心(未选中卡时灰置禁用,选中后才可点)。
    SELECT_BTN: ClassVar[Point] = Point(1082, 898)

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='货币战争-遭遇节点')

    @operation_node(name='遭遇节点', is_start_node=True, node_max_retry_times=10)
    def handle(self) -> OperationRoundResult:
        screen = self.last_screenshot
        if not self.round_by_ocr(screen, '遭遇其一', lcs_percent=0.9).is_success:  # 0.9 防备战屏「遭遇」误匹配(见 battle_loop 0c)
            return self.round_fail('非遭遇节点屏')
        # (difficulty + comp 成型度:formed→高难度拿好奖励,未成型→低难度保生存)→ 选 idx。替代硬编码「选左」。
        options = read_encounter_options(self.ctx, screen)
        match = self.ctx.cw_match
        idx, reason = 0, 'default(no-options/match)'
        if match is not None and options:
            _state = match.session.last_state or GameState()   # overlay 时 board 不可读 → 用上次备战快照
            _cfg = CurrencyWarConfig(self.ctx.current_instance_idx)
            pick = match.strategy.decide_encounter(options, _state, match.session, _cfg)
            if 0 <= pick.idx < len(options):
                idx = pick.idx
            reason = pick.reason
        log.info(f'[cw-encounter] options={[(o.difficulty, o.rewards) for o in options]} pick=idx{idx} {reason}')
        card = HandleEncounter.CARD_LEFT if idx == 0 else HandleEncounter.CARD_RIGHT
        safe_click(self, card, tag='cw-encounter')
        time.sleep(0.8)
        # 选择 + 验关(遭遇其一 消失 = overlay 关)。原「点了就 success」不验 → bug#1/隐藏多步 flat-loop
        # (partner reset 根因同类;write-operation「点了≠成了」;docstring 已记「插空白点击取消选中→死循环」风险)。
        return confirm_and_verify(self, confirm_point=HandleEncounter.SELECT_BTN,
                                  entry_keyword='遭遇其一', lcs_percent=0.9, tag='cw-encounter')
