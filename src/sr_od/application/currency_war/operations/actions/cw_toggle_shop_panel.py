"""开/收商店面板 op(备战/开商店点右下角面板开关;开拓商店点左缘浮动徽记;公用底层动作原语)。
与 ``cw_op/`` 域耦合动作 op 的分界见包 ``__init__`` docstring。
"""
from __future__ import annotations

from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.base.screen import screen_utils
from one_dragon.base.screen.screen_utils import OcrClickResultEnum
from sr_od.application.currency_war.kernel.cw_obs_core import (
    PIONEER_SHOP_SCREEN_NAME,
    SCREEN_NAME,
    SHOP_SCREEN_NAME,
    area_center,
)
from sr_od.application.currency_war.operations.cw_operation_base import CwOperation
from sr_od.context.sr_context import SrContext

#: 面板开关按钮 area(v4.7 实测可点击面 = 面板主体;旧「按钮-商店/按钮-收起」
#: 文本区中心点击实测偶发不生效,实锤点 = 面板中部 (1622,945)。两画面档
#: (备战/开商店)各建同名 area,矩形一致,op 按当前画面档取用)。
_TOGGLE_AREA: str = '按钮-商店开关'

#: 开拓商店收店徽记 area(与备战档同名同构:带状搜索域 + 模板 cw_rail_shop_badge;
#: 开拓档新建同名 area 供本 op 取用,非 id_mark 不进画面精准判定面)。
_BADGE_AREA: str = '标识-银轨商店徽记'


class CwToggleShopPanel(CwOperation):
    """切换商店面板开/收状态。
    起点:货币战争-备战(面板收起态,点击展开)或 货币战争-备战-开商店
    (面板展开态,点击收起)或 货币战争-备战-开拓商店(开拓银轨商店浮层,
    点击左缘徽记收回备战);终点:面板/浮层状态翻转,停留备战族画面
    (翻转结果归调用方下一帧 analyze_screen 对账:画面命中在哪个 screen_name)。
    消耗:零(纯界面开关)。

    零消耗承诺(高消耗风险画面纪律):本 op 只点面板开关或收店徽记,永不触碰
    商店牌 / 刷新 / 购买经验等扣费控件。

    收店控件按画面分支:「货币战争-备战」/「货币战争-备战-开商店」= 右下角
    面板开关,静态矩形中心直点;「货币战争-备战-开拓商店」= 左缘开拓银轨徽记
    (y 随羁绊面板布局浮动,静态中心会点空),带内模板匹配命中位直点;
    徽记未命中显式失败(status 带可操作提示,零引擎重试,重跑由调用方决定)。

    :param screen_name: 当前所在画面档:「货币战争-备战」(收起态)/
        「货币战争-备战-开商店」(展开态)/「货币战争-备战-开拓商店」
        (开拓银轨商店浮层);决定从哪个画面档取收店控件。传其它值构造期拒绝
        (带可用值 ValueError)。
    """

    def __init__(self, ctx: SrContext, screen_name: str):
        CwOperation.__init__(self, ctx, op_name='CW开关商店面板',
                             need_check_game_win=False)
        if screen_name not in (SCREEN_NAME, SHOP_SCREEN_NAME,
                               PIONEER_SHOP_SCREEN_NAME):
            raise ValueError(
                f'screen_name 非法: {screen_name}'
                f'(可用值: {SCREEN_NAME} | {SHOP_SCREEN_NAME}'
                f' | {PIONEER_SHOP_SCREEN_NAME})')
        self.screen_name: str = screen_name

    @operation_node(name='点击面板开关', is_start_node=True)
    def click_toggle(self) -> OperationRoundResult:
        if self.screen_name == PIONEER_SHOP_SCREEN_NAME:
            screen = self.last_screenshot
            if screen is None:
                screen = self.screenshot()
            # 开拓商店收店:徽记 y 随羁绊面板布局浮动 → 带内模板匹配达标才点、
            # 点命中位置中心(非带中心);直调底层助手绕过 sim 端口覆写
            # (sim 未建模开拓商店,哨兵帧恒 miss → 显式 fail 干净失败形态;
            # 本 op 属实机 MCP 原语,sim 路径不在消费面)。
            r = screen_utils.find_and_click_area(
                self.ctx, screen, PIONEER_SHOP_SCREEN_NAME, _BADGE_AREA)
            if r == OcrClickResultEnum.OCR_CLICK_SUCCESS:
                return self.round_success(
                    status='已点击开拓商店徽记(带内模板命中位,机械发出,零判效)',
                    wait=1.5)
            if r == OcrClickResultEnum.AREA_NO_CONFIG:
                return self.round_fail(
                    status=f'area 缺失:{_BADGE_AREA}({PIONEER_SHOP_SCREEN_NAME})')
            if r == OcrClickResultEnum.OCR_CLICK_FAIL:
                return self.round_fail(status='开拓商店徽记点击未生效(点击发出失败)')
            # miss 即显式 fail 零引擎重试:自定义失败 status 只有该写法能透出
            # (框架 round 系 miss 返回 round_retry,重试耗尽后 status 是通用文案);
            # 徽记在已确认面板开启态恒在场是识别器三态实证,瞬时 miss 概率低,
            # 放弃引擎级重试的自愈窗口,重跑由调用方决定。
            return self.round_fail(
                status='开拓商店徽记未识别(带内模板未命中;先核对开拓银轨≥2 开张)',
                wait=0.5)
        pt = area_center(self.ctx, _TOGGLE_AREA, screen_name=self.screen_name)
        if pt is None:
            return self.round_fail(
                status=f'area 缺失:{_TOGGLE_AREA}({self.screen_name})')
        self.ctx.controller.click(pt)
        return self.round_success(
            status='已点击商店面板开关(机械发出,零判效)',
            data={'x': pt.x, 'y': pt.y}, wait=1.5)
