"""买开拓商店指定槽商品卡 op(直购 + 补位验证;MCP 面向原语)。
与 ``cw_op/`` 域耦合动作 op 的分界见包 ``__init__`` docstring。

**包纪律申报**:本 op 在「零判效」包内**带补位验证**——任务规格(待跟进事项
㊱)显式要求「点商品卡直购无确认步→until 补位〔新卡出现或帕姆王进度推进〕」,
与包内机械点击惯例的差异在此显式声明;不重试不重点(补位与进度均未变化 =
显式 fail 带对照值交还调用方,防重复购买),消费面 = MCP agent(实机),
sim 未建模开拓商店(识别/点击走 screen_utils 直连,同 ``cw_toggle_shop_panel``
的 sim 边界申报)。
"""
from __future__ import annotations

from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.base.screen import screen_utils
from one_dragon.base.screen.screen_utils import FindAreaResultEnum
from sr_od.application.currency_war.kernel.cw_obs_core import (
    PIONEER_SHOP_SCREEN_NAME,
)
from sr_od.application.currency_war.obs.cw_trainshop_obs import (
    A_TS_CARD_PREFIX,
    A_TS_DETAIL_PREFIX,
    A_TS_SHOWCASE_CARD,
    PANEL_DETAIL_HIT_MIN,
    is_refresh_anchor,
    read_pam_progress,
    read_trainshop_slot_line,
)
from sr_od.application.currency_war.operations.cw_operation_base import CwOperation
from sr_od.context.sr_context import SrContext

#: 点击后等补位渲染(买一补一即时,实测帧间 ≈1s 内完成)
_CLICK_SETTLE_WAIT_S: float = 1.2


class CwBuyTrainShopCard(CwOperation):
    """买入开拓商店指定商品槽的一张卡。
    起点:货币战争-备战-开拓商店(面板展开,四槽带态);终点:点击直购指定槽
    (点商品卡直接购买、无确认步)且槽位补位验证通过(槽名行变化或帕姆王进度
    推进任一命中),停留本画面。
    消耗:支付该槽开拓力标价,不可逆。

    面板态守卫(玩家卡「首开空池软锁态」):中央展示卡态(四槽带不在场)显式
    失败不代买——守卫 = 详情按钮锚命中 ≥2(四槽带在场;展示卡态仅展示卡自带
    1 枚)。「槽 1 = 全部刷新」旧锚随刷新钮轮转占位作废(常态四槽全商品,
    1-6 实拍);解锁 = 点中央展示卡(坐标经 analyze extras ``showcase_card``.
    ``cx/cy`` 读当帧即点;实机三例口径)。恢复态死锁与首开空池帧画面同构
    (122630/013105 双帧实证),守卫只拦不处置,死锁买卡解锁法不主动用
    (游戏侧缺陷已登记,防线停机照旧)。

    :param slot: 商品槽物理槽号,1-4(= screen_info「商品卡-N」序号;
        extras.shop_cards 数组下标 + 1)。「全部刷新」钮轮转占位(槽 1/槽 4
        实测),占用槽执行期判出(名行锚)显式失败——买占用槽 = 误触发刷新,
        刷新走 CwRefreshTrainShop 或换商品槽(extras.refresh_slot 可先读);
        越界构造期拒绝(带可用值 ValueError)。
    :param expect_name: 期望商品名(可选语义参数,仅进日志与结果对照,
        不参与定位与校验)。
    """

    def __init__(self, ctx: SrContext, slot: int,
                 expect_name: str | None = None):
        CwOperation.__init__(self, ctx, op_name='CW买开拓商店商品卡',
                             need_check_game_win=False)
        if not 1 <= slot <= 4:
            raise ValueError(
                f'slot 越界: {slot}(可用值 1-4,商品槽物理槽号;'
                '「全部刷新」钮轮转占位,占用槽执行期判出,买前可对照'
                ' extras.refresh_slot)')
        self.slot: int = slot
        self.expect_name: str | None = expect_name
        # 点击前快照(名行/帕姆进度;补位验证对照源,执行期生成)
        self._pre_line: tuple[str, int | None] = ('', None)
        self._pre_pam: tuple[int, int] | None = None

    @operation_node(name='面板态守卫', is_start_node=True)
    def check_panel(self) -> OperationRoundResult:
        screen = self.last_screenshot
        if screen is None:
            screen = self.screenshot()
        current = self.check_and_update_current_screen(
            screen, screen_name_list=[PIONEER_SHOP_SCREEN_NAME])
        if current != PIONEER_SHOP_SCREEN_NAME:
            return self.round_fail(
                status=f'不在开拓商店面板(当前画面: {current or "未识别"})')
        # 四槽带在场守卫:详情按钮锚命中 ≥2(每槽卡底一枚;展示卡态仅展示卡
        # 自带 1 枚落「按钮-详情-3」)——与读层 slots 判定同源判据。
        si = self.ctx.screen_loader.get_screen(PIONEER_SHOP_SCREEN_NAME)
        hits = 0
        for idx in range(1, 5):
            area = (next((a for a in si.area_list
                          if a.area_name == f'{A_TS_DETAIL_PREFIX}{idx}'), None)
                    if si is not None else None)
            if area is None:
                return self.round_fail(
                    status=f'area 缺失:{A_TS_DETAIL_PREFIX}{idx}'
                           '(货币战争-备战-开拓商店)')
            r = screen_utils.find_area_in_screen(
                self.ctx, screen, area,
                screen_name=PIONEER_SHOP_SCREEN_NAME)
            if r == FindAreaResultEnum.AREA_NO_CONFIG:
                return self.round_fail(
                    status=f'area 配置异常:{A_TS_DETAIL_PREFIX}{idx}'
                           '(非文本区?)')
            if r == FindAreaResultEnum.TRUE:
                hits += 1
        if hits < PANEL_DETAIL_HIT_MIN:
            return self.round_fail(
                status='面板处中央展示卡态(首开空池软锁或恢复态死锁,画面同构):'
                       '四槽带不在场,不执行买槽;解锁 = 点中央展示卡'
                       f'(坐标经 extras {A_TS_SHOWCASE_CARD} 读数 cx/cy)')
        return self.round_success(
            status=f'槽带态确认(详情锚命中 {hits}/4)', wait=0.3)

    @node_from(from_name='面板态守卫')
    @operation_node(name='读点击前快照')
    def snapshot(self) -> OperationRoundResult:
        screen = self.last_screenshot
        if screen is None:
            screen = self.screenshot()
        self._pre_line = read_trainshop_slot_line(self.ctx, screen, self.slot)
        self._pre_pam = read_pam_progress(self.ctx, screen)
        if not self._pre_line[0]:
            return self.round_fail(
                status=f'槽{self.slot} 名行读空(面板态异常,先 analyze 对账)')
        if is_refresh_anchor([self._pre_line[0]]):
            return self.round_fail(
                status=f'槽{self.slot} 是「全部刷新」钮(轮转占位,执行期判出):'
                       '买该槽 = 误触发刷新;刷新走 CwRefreshTrainShop'
                       '或换商品槽(对照 extras.refresh_slot)')
        return self.round_success(
            status=f'快照:槽{self.slot}={self._pre_line[0]}'
                   f'(价{self._pre_line[1]})帕姆={self._pre_pam}',
            wait=0.2)

    @node_from(from_name='读点击前快照')
    @operation_node(name='点击商品卡直购')
    def click_card(self) -> OperationRoundResult:
        # 槽卡 rect 中心直点(直购无确认步;点卡即买,零判效由下一节点
        # 补位验证承担——直点绕 sim 端口,同 cw_toggle_shop_panel 边界申报)。
        si = self.ctx.screen_loader.get_screen(PIONEER_SHOP_SCREEN_NAME)
        area = None
        if si is not None:
            area = next((a for a in si.area_list
                         if a.area_name == f'{A_TS_CARD_PREFIX}{self.slot}'), None)
        if area is None or area.pc_rect is None:
            return self.round_fail(
                status=f'商品卡-{self.slot} area 缺失(screen_info 建档漂移)')
        pt = area.pc_rect.center
        self.ctx.controller.click(pt)
        return self.round_success(
            status=f'已点击商品卡{self.slot}槽'
                   f'{"" if self.expect_name is None else f"(期望 {self.expect_name})"}'
                   '(直购发出,待补位验证)',
            data={'slot': self.slot, 'x': pt.x, 'y': pt.y},
            wait=_CLICK_SETTLE_WAIT_S)

    @node_from(from_name='点击商品卡直购')
    @operation_node(name='验证补位')
    def verify_refill(self) -> OperationRoundResult:
        screen = self.screenshot()
        line = read_trainshop_slot_line(self.ctx, screen, self.slot)
        pam = read_pam_progress(self.ctx, screen)
        # 名行变化须以「新名行可读」为前提(瞬时读空 ≠ 补位;不猜);
        # 帕姆推进要求前后两读都可读(单侧缺失不构成证据)。
        refilled = ((bool(line[0]) and line != self._pre_line)
                    or (pam is not None and self._pre_pam is not None
                        and pam[0] > self._pre_pam[0]))
        if refilled:
            return self.round_success(
                status=f'补位确认:槽{self.slot} {self._pre_line[0]}→{line[0]},'
                       f'帕姆 {self._pre_pam}→{pam}',
                data={'slot': self.slot,
                      'old_name': self._pre_line[0], 'new_name': line[0],
                      'new_cost': line[1],
                      'pam_before': (list(self._pre_pam)
                                     if self._pre_pam else None),
                      'pam_after': (list(pam) if pam else None)},
                wait=0.3)
        return self.round_fail(
            status=f'买槽未生效:槽{self.slot} 名行({self._pre_line[0]}→{line[0]})'
                   f'与帕姆进度({self._pre_pam}→{pam})均未变化'
                   '(点击被吞或余额不足;对照 extras.balance 后重跑)')
