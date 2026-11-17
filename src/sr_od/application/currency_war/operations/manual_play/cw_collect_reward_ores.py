"""拾取场上晶矿 op(识别+逐个点击;MCP 手动游玩纯动作)。
与 ``cw_op/`` 域耦合动作 op 的分界见包 ``__init__`` docstring。
"""
from __future__ import annotations

import time

from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from sr_od.application.currency_war.obs.cw_identity_obs import read_ore_sights
from sr_od.application.currency_war.operations.cw_operation_base import CwOperation
from sr_od.context.sr_context import SrContext


class CwCollectRewardOres(CwOperation):
    """拾取备战画面右侧奖励区的晶矿奖励球(识别 → 逐个点击)。
    起点:货币战争-备战(奖励节点通关后晶矿落在右侧区域);终点:逐个点击
    拾取,停留原画面(拾取结果归下一帧 analyze_screen 对账:extras.reward_ores
    应清空,开出物入 owned_equips)。
    消耗:零(奖励领取;晶矿开出装备/道具为正向收益)。

    识别 = ``read_ore_sights``(HoughCircles,纯读);点击 = 球心坐标。
    **商店展开态守卫**:商店面板开着时卡面/装备栏圆形图标会被误判为晶矿
    (实机误购实证),此时本 op 直接 round_fail 提示先收店,不点击。
    席满时部分奖励(武装箱/角色)可能无法领取(游戏侧拒绝)——机械点击
    不判断,对账以 extras 为准。

    :param max_clicks: 单次最多点击球数上限,1-12(防识别噪声导致连环误点;
        缺省 8 = 实测单波晶矿上限附近)。
    """

    def __init__(self, ctx: SrContext, max_clicks: int = 8):
        CwOperation.__init__(self, ctx, op_name='CW拾取晶矿',
                             need_check_game_win=False)
        if not 1 <= max_clicks <= 12:
            raise ValueError(f'max_clicks 越界: {max_clicks}(可用值 1-12)')
        self.max_clicks: int = max_clicks

    @operation_node(name='识别并拾取晶矿', is_start_node=True)
    def collect(self) -> OperationRoundResult:
        screen = self.last_screenshot
        if screen is None:
            screen = self.screenshot()
        # 商店展开态守卫(两局实机误报实证):商店卡面/右栏装备栏的圆形图标
        # 会被 HoughCircles 误判为晶矿,点击即误购商品(首局曾误购符玄/花火)。
        # 开商店画面档的「按钮-收起」命中 = 商店展开 → 拒绝执行并提示先收店。
        shop_open = self.round_by_find_area(
            screen, '货币战争-备战-开商店', '按钮-收起')
        if shop_open.is_success:
            return self.round_fail(
                status='商店面板展开中,晶矿识别会误报(先调 CwToggleShopPanel 收店再拾取)')
        sights = read_ore_sights(self.ctx, screen)
        if not sights:
            return self.round_success(status='场上无晶矿(无需拾取)', data={'collected': 0})
        clicked: list[dict] = []
        for color, pt, _r in sights[:self.max_clicks]:
            self.ctx.controller.click(pt)
            clicked.append({'color': color, 'x': pt.x, 'y': pt.y})
            time.sleep(1.2)
        return self.round_success(
            status=f'已点击晶矿×{len(clicked)}(机械发出,零判效)',
            data={'collected': len(clicked), 'ores': clicked}, wait=1)
