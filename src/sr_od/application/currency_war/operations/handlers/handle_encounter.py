
"""货币战争 遭遇节点 二选一处理 op(从主循环 ``CurrencyWarRunLoop`` 拆出)。

检测「遭遇其一」+ 底部「选择」→ 点卡身选中 + 点选择确认。2026-08-04 实测交互模型
(见 ``docs/game/screens/currency_war_encounter.md``):
  点卡身(选中)→ 点选择(确认),**中间不要插空白点击**(会取消选中 → 死循环)。

✅ Stage C2 已接(L55):调 ``decide_encounter``(已实现,按 comp 成型度选:未成型→低难保生存 /
  成型+词缀利→高难拿奖励 / 全分支克→刷新换批;用 pick.idx 选卡,**非默认选左**)。原「待实现/默认选左」
  过期已撤回。⚠️ affix 避开分支 N/A(选项 UI 不显词缀,战后才显)。
坐标(screen_info 化债):卡身/选择经 ``cw_obs_core.area_center`` 读 screen_info
  ``currency_war_encounter``(``遭遇卡-其一/其二`` + ``按钮-选择``);缺失才用兜底常量。
  档案帧回验:sr-od-test/screens/货币战争-遭遇节点/default.webp 上 标识-遭遇节点 /
  按钮-选择 均 conf≈0.999 命中。卡身 rect center 未单独实锤(历史实测点 (665,500)/(1288,550)
  保留作兜底;rect 覆盖同卡身带)。
"""
import time
from typing import ClassVar

from one_dragon.base.geometry.point import Point
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.application.currency_war.currency_war_config import CurrencyWarConfig
from sr_od.application.currency_war.cw_node_obs import read_encounter_options
from sr_od.application.currency_war.cw_obs_core import area_center
from sr_od.application.currency_war.cw_state import GameState
from sr_od.application.currency_war.cw_telemetry import record_event_choice
from sr_od.application.currency_war.operations.handlers._overlay_confirm import (
    confirm_and_verify,
    safe_click,
)
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class HandleEncounter(SrOperation):
    """遭遇节点二选一:点卡选中 + 选择确认。"""

    SCREEN_NAME: ClassVar[str] = '货币战争-遭遇节点'   # screen_info 画面(currency_war_encounter.yml)
    # 遭遇卡卡身中心。左卡=遭遇其一(难度低,金币×2);右卡=遭遇其四(难度高,随机4费角色×3)。
    # 常量=screen_info 缺失兜底;首选 area_center('遭遇卡-其一/其二')。
    CARD_LEFT: ClassVar[Point] = Point(665, 500)
    CARD_RIGHT: ClassVar[Point] = Point(1288, 550)
    # 底部「选择」按钮中心(未选中卡时灰置禁用,选中后才可点)。常量=兜底;首选 area_center('按钮-选择')。
    SELECT_BTN: ClassVar[Point] = Point(1082, 898)

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='货币战争-遭遇节点')

    @operation_node(name='遭遇节点', is_start_node=True, node_max_retry_times=10)
    def handle(self) -> OperationRoundResult:
        screen = self.last_screenshot
        # live 2026-08-15:改 id_mark area(标识-遭遇节点)—— OCR「遭遇其一」在截断帧(「遭遇其」)miss;
        # 独立屏实锤(返回备战界面右上,同补给/投资策略)。
        if not self.round_by_find_area(screen, HandleEncounter.SCREEN_NAME,
                                       '标识-遭遇节点', crop_first=False).is_success:
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
        # 遥测:选项选择落账本(exogenous kind='event_choice')。
        # 此前只 log——「选了其几/两卡奖励/reason」跨局归因在遥测上断链。
        record_event_choice('encounter',
                            [{'difficulty': o.difficulty, 'rewards': o.rewards}
                             for o in options],
                            idx, reason)
        # 卡身/选择坐标从 screen_info 读;缺失走历史实测兜底常量。
        card_left = area_center(self.ctx, '遭遇卡-其一', HandleEncounter.SCREEN_NAME) or HandleEncounter.CARD_LEFT
        card_right = area_center(self.ctx, '遭遇卡-其二', HandleEncounter.SCREEN_NAME) or HandleEncounter.CARD_RIGHT
        select_btn = area_center(self.ctx, '按钮-选择', HandleEncounter.SCREEN_NAME) or HandleEncounter.SELECT_BTN
        card = card_left if idx == 0 else card_right
        safe_click(self, card, tag='cw-encounter')
        time.sleep(0.8)
        # 选择 + 验关(遭遇其一 消失 = overlay 关)。原「点了就 success」不验 → bug#1/隐藏多步 flat-loop
        # (partner reset 根因同类;write-operation「点了≠成了」;docstring 已记「插空白点击取消选中→死循环」风险)。
        # 验关用标题「遭遇节点」(4 字 vs 备战「遭遇」标签 2 字,LCS 0.5<0.8 不误匹配;live 2026-08-15)
        return confirm_and_verify(self, confirm_point=select_btn,
                                  entry_keyword='遭遇节点', lcs_percent=0.8, tag='cw-encounter')
