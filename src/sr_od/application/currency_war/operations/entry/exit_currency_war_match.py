"""从货币战争对局中退出(放弃+结算)回大厅。

高频重复操作(测试/刷开局/回滚),手动做很繁琐(Esc→放弃→结算3页→大厅)→ 建成 op 一键调用。
支持入口:备战阶段 / 战斗中 / **事件 overlay**(投资策略/环境/补给/遭遇/巨星 —— 先 escape 回备战)
(任何有 Esc 放弃提示的态)→ 放弃并结算 → 结算 3 页 → 大厅。
"""
from typing import ClassVar

from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.context.sr_context import SrContext
from sr_od.operations.sr_operation import SrOperation


class ExitCurrencyWarMatch(SrOperation):
    """放弃当前货币战争对局,返回大厅。"""

    STATUS_AT_LOBBY: ClassVar[str] = '已返回货币战争大厅'

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='退出货币战争对局')

    @operation_node(name='退出对局', is_start_node=True, node_max_retry_times=30)
    def exit_match(self) -> OperationRoundResult:
        screen = self.last_screenshot

        # 已在大厅 → 完成
        if self.round_by_find_area(screen, '货币战争-大厅', '标识-创业指南').is_success:
            return self.round_success(ExitCurrencyWarMatch.STATUS_AT_LOBBY)

        # 放弃提示 → 放弃并结算
        if self.round_by_ocr_and_click(screen, '放弃并结算', success_wait=3).is_success:
            log.info('[cw-exit] 放弃并结算 → 结算页')
            return self.round_wait(wait=2)

        # 结算页 1:挑战失败/下一步
        if self.round_by_ocr_and_click(screen, '下一步', success_wait=3).is_success:
            return self.round_wait(wait=2)

        # 结算页 2:下一页
        if self.round_by_ocr_and_click(screen, '下一页', success_wait=3).is_success:
            return self.round_wait(wait=2)

        # 结算页 3:返回货币战争
        if self.round_by_ocr_and_click(screen, '返回货币战争', success_wait=3).is_success:
            return self.round_wait(wait=2)

        # 备战/对局中(无放弃提示)→ Esc 弹放弃提示
        if (self.round_by_find_area(screen, '货币战争-备战', '备战标识-购买经验').is_success       # 备战
                or self.round_by_ocr(screen, '备战阶段').is_success   # TODO(T#103) 待建 area
                or self.round_by_find_area(screen, '货币战争-备战', '按钮-出战').is_success):
            self.ctx.controller.btn_tap('esc')
            return self.round_wait(wait=2)

        # 事件 overlay(投资策略/环境 有「返回备战界面」)→ 点回备战,下轮走备战分支 Esc→放弃。
        # 修 bug:事件屏无「放弃并结算」/备战文本 → 全分支不命中 → retry 死循环(2026-08-04 实测卡 210s+)。
        if self.round_by_ocr_and_click(screen, '返回备战界面', success_wait=2).is_success:
            return self.round_wait(wait=2)
        # 其他事件 overlay(补给/遭遇/巨星/详情/可合成列表)→ Esc 关回备战
        if (self.round_by_ocr(screen, '补给阶段').is_success
                or self.round_by_ocr(screen, '遭遇其一').is_success
                or self.round_by_ocr(screen, '盛会之星').is_success
                or self.round_by_ocr(screen, '可合成列表').is_success
                or self.round_by_ocr(screen, '角色详情').is_success):
            self.ctx.controller.btn_tap('esc')
            return self.round_wait(wait=2)

        return self.round_retry(wait=1)
