"""出战 op(纯机械:定位出战按钮→点击;公用底层动作原语)。
与 ``cw_op/`` 域耦合动作 op 的分界见包 ``__init__`` docstring。
"""
from __future__ import annotations

from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from sr_od.application.currency_war.operations.cw_operation_base import CwOperation
from sr_od.context.sr_context import SrContext

_PREP_SCREEN: str = '货币战争-备战'


class CwStartBattleByClick(CwOperation):
    """点击出战按钮(盲点机械一段;零校验零特殊处理,用户裁定)。
    起点/终点:货币战争-备战画面自身(点击后是否转场归调用方下一帧观察)。
    消耗:进入战斗(败局扣小队生命值;战斗本身无直接货币消耗)。

    动作 op 契约(用户裁定):只管机械执行——**盲点形态**:坐标从画面档
    「按钮-出战」静态解析后直接点击,无 OCR 可见性门、无重试、无任何
    画面状态判断;状态前置(收店/弹窗/软锁)与误触代价全部由调用方负责
    (编排层保证或 agent 按 skill 画面文档自查)。

    :param none: 无参数。
    """

    def __init__(self, ctx: SrContext):
        CwOperation.__init__(self, ctx, op_name='CW出战',
                             need_check_game_win=False)

    @operation_node(name='点击出战', is_start_node=True)
    def click_start(self) -> OperationRoundResult:
        # 盲点机械:画面档坐标静态解析 → 直接点击(无 OCR 门/无重试;用户裁定)
        si = self.ctx.screen_loader.get_screen(_PREP_SCREEN)
        area = None
        if si is not None:
            area = next((a for a in si.area_list
                         if a.area_name == '按钮-出战'), None)
        if area is None or area.pc_rect is None:
            return self.round_fail(
                status='area 缺失:按钮-出战(货币战争-备战)')
        self.ctx.controller.click(area.pc_rect.center)
        return self.round_success(
            status='已点击出战(盲点机械发出,零判效)', wait=1)
