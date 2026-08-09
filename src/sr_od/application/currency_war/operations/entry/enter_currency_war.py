# 未验证(货币战争自主推进期代码,需进对应画面按 od-dev-screen-onboarding 等 skill review 重审后才能信)

from typing import ClassVar

from one_dragon.base.geometry.rectangle import Rect
from one_dragon.base.operation.operation_edge import node_from
from one_dragon.base.operation.operation_node import operation_node
from one_dragon.base.operation.operation_round_result import OperationRoundResult
from one_dragon.utils.log_utils import log
from sr_od.context.sr_context import SrContext
from sr_od.interastral_peace_guide.guid_choose_tab import GuideChooseTab
from sr_od.interastral_peace_guide.open_guide import GuideOpen
from sr_od.operations.sr_operation import SrOperation


class EnterCurrencyWar(SrOperation):
    """从大世界进入「货币战争」大厅(入口流程 M1)。

    路径:打开指南(星际和平指南)→ 旷宇纷争 TAB → (货币战争分类默认选中)→ 前往参与
    → 关一次性弹窗(V4.4 赛季扩充说明 / 新内容解禁)→ 货币战争大厅。

    repo guide_data / screen_info 尚无货币战争,故 TAB 用现有「星际和平指南-TAB-旷宇纷争」area,
    其余用 OCR 点击(非 GuideTransport)。详见 .debug/temp/currency_war/design.md。
    """

    # 点空白关闭「点击空白处关闭」类弹窗的区域(避开中央内容)
    BLANK_CLICK: ClassVar[Rect] = Rect(1450, 920, 1560, 980)
    # 大厅 screen_info 画面名;到达判定经 round_by_find_area(替代全屏 ocr)
    LOBBY_SCREEN: ClassVar[str] = '货币战争-大厅'

    STATUS_AT_LOBBY: ClassVar[str] = '已在货币战争大厅'

    def __init__(self, ctx: SrContext):
        SrOperation.__init__(self, ctx, op_name='进入货币战争')

    @operation_node(name='打开指南', is_start_node=True)
    def open_guide(self) -> OperationRoundResult:
        op = GuideOpen(self.ctx)
        return self.round_by_op_result(op.execute())

    @node_from(from_name='打开指南')
    @operation_node(name='选择旷宇纷争TAB')
    def choose_tab(self) -> OperationRoundResult:
        # 复用 GuideChooseTab:检测当前 tab + find_and_click_area 真正点击(旷宇纷争在 repo guide_data 内)
        tab = self.ctx.guide_data.best_match_tab_by_name('旷宇纷争')
        if tab is None:
            return self.round_fail(status='指南数据无「旷宇纷争」TAB')
        op = GuideChooseTab(self.ctx, tab)
        return self.round_by_op_result(op.execute())

    @node_from(from_name='选择旷宇纷争TAB')
    @operation_node(name='前往参与')
    def enter(self) -> OperationRoundResult:
        screen = self.last_screenshot
        # success_wait 给点击落地 + 跳转加载留时间
        return self.round_by_ocr_and_click(screen, '前往参与', retry_wait=1, success_wait=2)

    @node_from(from_name='前往参与')
    @operation_node(name='关闭弹窗并等待大厅', node_max_retry_times=30)
    def wait_lobby(self) -> OperationRoundResult:
        screen = self.last_screenshot

        # 到达大厅:左菜单「创业指南」(大厅独有锚点;lobby screen_info area 判定,替代全屏 ocr)。
        # 不用「开始「货币战争」」——会与旷宇纷争页「货币战争」分类文本 LCS 误匹配。
        if self.round_by_find_area(screen, EnterCurrencyWar.LOBBY_SCREEN, '标识-创业指南').is_success:
            log.info('[cw-entry] 到达货币战争大厅')
            return self.round_success(EnterCurrencyWar.STATUS_AT_LOBBY)

        # 仍在指南页(「前往参与」还在 = 上个节点的 transport click 没落地,仍在加载)→ 重点击。
        # 否则停在指南页(「货币战争」分类 + 「前往参与」按钮都在)→ 下方 F 分支(NOT 前往参与)被跳过
        # → 无分支命中 → 死循环重试(2026-08-04 全流程跑 37x 重试失败根因)。
        if self.round_by_ocr(screen, '前往参与').is_success:
            return self.round_by_ocr_and_click(screen, '前往参与', success_wait=2)

        # 「点击空白处关闭」类弹窗(如新内容解禁)→ 点空白
        if self.round_by_ocr(screen, '点击空白处关闭').is_success:
            self.ctx.controller.click(EnterCurrencyWar.BLANK_CLICK.center)
            return self.round_retry(wait=1)

        # 公告类弹窗(如 V4.4 赛季扩充说明,无「点击空白处关闭」)→ ESC 关
        if (self.round_by_ocr(screen, '赛季扩充').is_success
                or self.round_by_ocr(screen, '新内容解禁').is_success
                or self.round_by_ocr(screen, '扩充内容概览').is_success):
            self.ctx.controller.esc()
            return self.round_retry(wait=1)

        # 「前往参与」把角色传送到朝露公馆入口附近(大世界旷野),需按 F(交互)进货币战争大厅。
        # 判定:画面有「货币战争」(入口交互提示)且不在指南页(无「前往参与」)→ 按 F。
        if (self.round_by_ocr(screen, '货币战争').is_success
                and not self.round_by_ocr(screen, '前往参与').is_success):
            log.info('[cw-entry] 朝露公馆入口(传送后)→ 按 F(交互)进货币战争大厅')
            self.ctx.controller.btn_tap(self.ctx.controller.game_config.key_interact)
            return self.round_retry(wait=2)

        # 加载中或未知态 → 继续等
        return self.round_retry(wait=1)
