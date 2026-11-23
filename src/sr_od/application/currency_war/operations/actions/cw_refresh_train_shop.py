"""刷新开拓商店商品池 op(「全部刷新」钮,1 开拓力/次;MCP 面向原语)。
与 ``cw_op/`` 域耦合动作 op 的分界见包 ``__init__`` docstring。

**包纪律申报**:与 ``cw_buy_train_shop_card`` 同申报——带刷新生效验证
(余额扣减 / 槽带变化 / 帕姆推进任一),任务规格(挂账 ㊱)显式要求;
不重试不重点,未变化显式 fail 交还调用方。消费面 = MCP agent(实机),
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
    find_refresh_slot,
    read_pam_progress,
    read_trainshop_balance,
    read_trainshop_slot_line,
)
from sr_od.application.currency_war.operations.cw_operation_base import CwOperation
from sr_od.context.sr_context import SrContext

#: 点击后等池重摇渲染(同买卡补位窗)
_CLICK_SETTLE_WAIT_S: float = 1.2


class CwRefreshTrainShop(CwOperation):
    """刷新开拓商店商品池一次(点「全部刷新」钮,消耗 1 开拓力)。
    起点:货币战争-备战-开拓商店(面板展开,四槽带态);终点:刷新发出且生效
    验证通过(开拓力余额扣减 / 任一商品槽名行变化 / 帕姆王进度推进,任一命中),
    停留本画面;刷新后的池构成归调用方下一帧 analyze extras ``shop_cards`` 对账。
    消耗:1 开拓力/次,不可逆。

    面板态守卫与 ``CwBuyTrainShopCard`` 同源:中央展示卡态(四槽带不在场)
    显式失败——该态无刷新钮可点(守卫判据同帧同构,申报见该 op docstring)。
    刷新钮**轮转占位**(1-4 任一槽,槽 1/槽 4 实测;常态可不在场):守卫经
    extras 同源读链 ``find_refresh_slot`` 逐槽名行定位,点击随槽位;不在场
    显式 fail(候刷新钮出现帧再刷),不再误报中央展示卡态。

    :param expect_note: 语义备注(可选,仅进日志,不参与定位与校验)。
    """

    def __init__(self, ctx: SrContext, expect_note: str | None = None):
        CwOperation.__init__(self, ctx, op_name='CW刷新开拓商店',
                             need_check_game_win=False)
        self.expect_note: str | None = expect_note
        # 刷新钮物理槽号(守卫节点定位,点击节点消费;机械执行细节)
        self._refresh_slot: int | None = None
        self._pre_balance: int | None = None
        self._pre_lines: list[tuple[str, int | None]] = []
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
        # 四槽带在场守卫:详情按钮锚命中 ≥2(与买卡 op 同源判据,读层常量)。
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
                       '无刷新钮可点,不执行刷新;解锁 = 点中央展示卡'
                       f'(坐标经 extras {A_TS_SHOWCASE_CARD} 读数 cx/cy)')
        # 刷新钮定位(轮转占位):extras 同源读链逐槽名行锚;不在场显式 fail。
        self._refresh_slot = find_refresh_slot(self.ctx, screen)
        if self._refresh_slot is None:
            return self.round_fail(
                status='刷新钮不在场(常态可不在场,四槽全商品实拍):'
                       '候刷新钮出现帧再刷(对照 extras.refresh_slot)')
        return self.round_success(
            status=f'槽带态确认(详情锚命中 {hits}/4),'
                   f'刷新钮在槽{self._refresh_slot}',
            wait=0.3)

    @node_from(from_name='面板态守卫')
    @operation_node(name='读点击前快照')
    def snapshot(self) -> OperationRoundResult:
        screen = self.last_screenshot
        if screen is None:
            screen = self.screenshot()
        self._pre_balance = read_trainshop_balance(self.ctx, screen)
        self._pre_lines = [read_trainshop_slot_line(self.ctx, screen, i)
                           for i in range(1, 5)]
        self._pre_pam = read_pam_progress(self.ctx, screen)
        return self.round_success(
            status=f'快照:余额={self._pre_balance} 帕姆={self._pre_pam} '
                   f'池={[ln[0] for ln in self._pre_lines]}',
            wait=0.2)

    @node_from(from_name='读点击前快照')
    @operation_node(name='点击全部刷新')
    def click_refresh(self) -> OperationRoundResult:
        slot = self._refresh_slot
        if slot is None:
            return self.round_fail(
                status='刷新钮槽位缺失(守卫未定位,流程状态异常)')
        si = self.ctx.screen_loader.get_screen(PIONEER_SHOP_SCREEN_NAME)
        area = None
        if si is not None:
            area = next((a for a in si.area_list
                         if a.area_name == f'{A_TS_CARD_PREFIX}{slot}'), None)
        if area is None or area.pc_rect is None:
            return self.round_fail(
                status=f'商品卡-{slot} area 缺失(screen_info 建档漂移)')
        pt = area.pc_rect.center
        self.ctx.controller.click(pt)
        return self.round_success(
            status=f'已点击槽{slot}「全部刷新」(1 开拓力发出,待生效验证)'
                   f'{"" if self.expect_note is None else f"({self.expect_note})"}',
            data={'slot': slot, 'x': pt.x, 'y': pt.y},
            wait=_CLICK_SETTLE_WAIT_S)

    @node_from(from_name='点击全部刷新')
    @operation_node(name='验证刷新生效')
    def verify_refresh(self) -> OperationRoundResult:
        screen = self.screenshot()
        balance = read_trainshop_balance(self.ctx, screen)
        lines = [read_trainshop_slot_line(self.ctx, screen, i)
                 for i in range(1, 5)]
        pam = read_pam_progress(self.ctx, screen)
        # 生效证据三选一(任一):余额扣减 / 任一槽名行变化(双侧可读) /
        # 帕姆推进(双侧可读)。池重摇同 roll = 名行不变时靠余额/帕姆兜证。
        balance_down = (balance is not None and self._pre_balance is not None
                        and balance < self._pre_balance)
        lines_changed = any(new != old and bool(new[0])
                            for new, old in zip(lines, self._pre_lines,
                                                strict=True))
        pam_up = (pam is not None and self._pre_pam is not None
                  and pam[0] > self._pre_pam[0])
        if balance_down or lines_changed or pam_up:
            return self.round_success(
                status=f'刷新生效确认:余额 {self._pre_balance}→{balance},'
                       f'帕姆 {self._pre_pam}→{pam}',
                data={'balance_before': self._pre_balance,
                      'balance_after': balance,
                      'pam_before': (list(self._pre_pam)
                                     if self._pre_pam else None),
                      'pam_after': (list(pam) if pam else None)},
                wait=0.3)
        return self.round_fail(
            status=f'刷新未生效:余额({self._pre_balance}→{balance})/槽带/帕姆'
                   f'({self._pre_pam}→{pam})均未变化(点击被吞或余额不足;对照 '
                   'extras.balance 后重跑)')
