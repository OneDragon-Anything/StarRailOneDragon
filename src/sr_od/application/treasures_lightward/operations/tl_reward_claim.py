"""逐光捡金奖励领取:选关屏礼物盒入口 → 永劫/终局祭礼弹窗一键全领 → 关闭返回。

交互模型(2026-11-07 实机建档,详见 docs/game/screens/末日幻影-祭礼奖励.md):
- 领取形态 = **一键全领**:点任一「领取」按钮即发放该 tab 全部可领档位,
  无确认弹窗;领取后弹「获得物品」覆盖页,点空白处关闭;
- 奖励行三态:可领 = 金色「领取」按钮;已领取 = 灰色对勾圆圈;未达成 = 「进行中」;
  无可领判定 = 按钮列区域无「领取」文本;
- 两个 tab(**永劫祭礼** = 期次星数累计 / **终局祭礼** = 各难度首通)需分别各领一次;
- 「奇珍琳琅」袋子入口打开的是兑换商店(消耗代币),与本 op 无关,勿混淆。

起点 = 末日幻影-选关(或已在祭礼弹窗);终点 = 末日幻影-选关(两 tab 均无可领)。
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from sr_od.operations.sr_operation import SrOperation

if TYPE_CHECKING:

    from sr_od.context.sr_context import SrContext

_SELECT_SCREEN: str = '末日幻影-选关'
_GIFT_SCREEN: str = '末日幻影-祭礼奖励'

#: 「领取」点击预算(整个 op 共享):一键全领语义下两 tab 各只需 1 次点击,
#: 上限 6 仅防「领取按钮反复出现但获得物品页一直不出现」的异常重试死循环。
_CLAIM_CLICK_LIMIT: int = 6


class TlRewardClaimOp(SrOperation):
    """领取逐光捡金期次奖励(永劫祭礼 + 终局祭礼,一键全领)。

    入口 = 末日幻影-选关屏左下礼物盒(或在祭礼弹窗内直接接续);
    不在选关屏时显式失败,不自行长途导航(入口链由 GotoTreasuresLightward 负责)。
    """

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='逐光捡金 领取奖励')
        self._claim_clicks: int = 0  #: 「领取」成功点击计数(预算守卫,见 _CLAIM_CLICK_LIMIT)

    @operation_node(name='进入祭礼弹窗', is_start_node=True, node_max_retry_times=6)
    def _enter_dialog(self) -> OperationRoundResult:
        """入口分派:已在弹窗直接接续 / 在选关屏点礼物盒并等弹窗锚出现。

        选关屏判定用「标题+难度-01」双锚(与 GotoTreasuresLightward 到达验证
        同口径);until 用弹窗双 tab 锚 —— 点击落地且弹窗真弹出才算成功。"""
        screen = self.last_screenshot
        if (self.round_by_find_area(screen, _GIFT_SCREEN, 'tab-永劫祭礼').is_success
                or self.round_by_find_area(screen, _GIFT_SCREEN, 'tab-终局祭礼').is_success):
            return self.round_success('已在祭礼弹窗', wait=1)
        if (self.round_by_find_area(screen, _SELECT_SCREEN, '标题-末日幻影行').is_success
                and self.round_by_find_area(screen, _SELECT_SCREEN, '难度-01').is_success):
            return self.round_by_find_and_click_area(
                screen, _SELECT_SCREEN, '入口-祭礼奖励',
                pre_delay=0.5, success_wait=2,
                until_find_all=[(_GIFT_SCREEN, 'tab-永劫祭礼')],
            )
        return self.round_fail('不在末日幻影选关屏(前置:先到逐光捡金选关)')

    @node_from(from_name='进入祭礼弹窗')
    @operation_node(name='领取永劫祭礼', node_max_retry_times=16)
    def _claim_eternal(self) -> OperationRoundResult:
        """永劫祭礼(默认 tab)领取循环:关获得物品页 → 点领取 → 无可领推进。"""
        return self._claim_round('永劫祭礼')

    @node_from(from_name='领取永劫祭礼')
    @operation_node(name='切换终局祭礼', node_max_retry_times=6)
    def _switch_final(self) -> OperationRoundResult:
        """切到终局祭礼 tab,转移验证 = 终局列表「难度」行锚出现。

        为什么不用 tab 文字验证切换:两 tab 文字同屏恒在,OCR 分不出选中态;
        终局列表行含期名+「难度0N」(期名随期轮换,「难度」为 UI 固定词,
        永劫列表行只有「累计获得N」与奖励图标,无「难度」字样)——列表区
        rect 限定下的「难度」锚跨期稳定且永劫态天然不命中。"""
        screen = self.last_screenshot
        if self.round_by_find_area(screen, _GIFT_SCREEN, '列表-终局难度行').is_success:
            return self.round_success('已在终局祭礼', wait=1)
        return self.round_by_find_and_click_area(
            screen, _GIFT_SCREEN, 'tab-终局祭礼',
            pre_delay=0.5, success_wait=2,
            until_find_all=[(_GIFT_SCREEN, '列表-终局难度行')],
        )

    @node_from(from_name='切换终局祭礼')
    @operation_node(name='领取终局祭礼', node_max_retry_times=16)
    def _claim_final(self) -> OperationRoundResult:
        """终局祭礼领取循环,逻辑同永劫(列表内容不同,领取/关闭交互一致)。"""
        return self._claim_round('终局祭礼')

    @node_from(from_name='领取终局祭礼')
    @operation_node(name='关闭返回选关', node_max_retry_times=6)
    def _exit_back(self) -> OperationRoundResult:
        """点关闭X 回选关屏,until 双锚验证真转移(点了 ≠ 关了)。"""
        return self.round_by_find_and_click_area(
            self.last_screenshot, _GIFT_SCREEN, '按钮-关闭X',
            pre_delay=0.5, success_wait=2,
            until_find_all=[
                (_SELECT_SCREEN, '标题-末日幻影行'),
                (_SELECT_SCREEN, '难度-01'),
            ],
        )

    def _claim_round(self, tab_label: str) -> OperationRoundResult:
        """单 tab 领取循环的一轮:覆盖页 → 领取 → 无可领收口。

        三分支是同一弹窗的状态机轮转(获得物品覆盖页/可领列表/无可领),
        不是多画面 if-elif;每轮只推进一小步,由 round_wait 重入收敛。"""
        screen = self.last_screenshot
        # 获得物品覆盖页判定必须在「领取」之前:覆盖页盖住列表,若 OCR 仍从
        # 暗化背景误读出「领取」,先关覆盖页再领取,避免点在覆盖页上
        if self.round_by_find_area(screen, _GIFT_SCREEN, '按钮-点击空白处关闭').is_success:
            result = self.round_by_find_and_click_area(
                screen, _GIFT_SCREEN, '按钮-点击空白处关闭',
                pre_delay=0.5, success_wait=1.5,
                until_not_find_all=[(_GIFT_SCREEN, '按钮-点击空白处关闭')],
            )
            if result.is_success:
                return self.round_wait(f'{tab_label} 关闭获得物品页', wait=1)
            return result
        # 领取按钮 y 位置随可领行漂移(列表自动定位到第一个可领行),
        # OCR 在按钮列 rect 内找「领取」并点命中位置,不锁单行坐标
        claim_area = self.ctx.screen_loader.get_area(_GIFT_SCREEN, '按钮-领取')
        result = self.round_by_ocr_and_click(
            screen, '领取', area=claim_area, lcs_percent=0.7,
            pre_delay=0.5, success_wait=2,
        )
        if result.is_success:
            self._claim_clicks += 1
            if self._claim_clicks > _CLAIM_CLICK_LIMIT:
                return self.round_fail(
                    f'领取点击超过预算 {_CLAIM_CLICK_LIMIT} 次(获得物品页未出现?)')
            # 一键全领:一次点击发放全部可领档;重入本节点处理获得物品页
            # 并复查是否有新可领(正常应无),不直接 success(点了 ≠ 领到了)
            return self.round_wait(f'{tab_label} 已点领取({self._claim_clicks})', wait=2)
        # ocr_and_click 的失败分两种,语义不同不可合并:「找不到 领取」 = 本 tab
        # 无可领(正常收口);「点击 领取 失败」 = 找到了但点击没生效,重试
        if '找不到' in (result.status or ''):
            return self.round_success(f'{tab_label} 无可领项', wait=1)
        return result
